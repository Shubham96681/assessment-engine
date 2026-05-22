"""
Rejection corpus — negative training memory for quality failures.

Stores rejected stems + flags so later generation avoids the same failure modes.
Persists to:
  - project-root rejection_corpus.jsonl (always, for training export)
  - Qdrant generation_history with record_type=rejected (semantic retrieval)
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.vector_store import qdrant_client
from app.generation.question_regenerator import collect_rejection_feedback
from app.rag.embeddings import embed_texts
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_JSONL = PROJECT_ROOT / "rejection_corpus.jsonl"
TRAINING_JSONL = PROJECT_ROOT / "training_rejection_corpus.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_flags(feedback: str) -> List[str]:
    if not feedback:
        return ["quality_below_threshold"]
    return [f.strip() for f in feedback.split(";") if f.strip()]


def _negative_instruction(flags: List[str], chapter: str) -> str:
    if not flags:
        return f"Do not repeat low-quality {chapter} question patterns from the rejection list."
    joined = ", ".join(flags[:8])
    return (
        f"Do NOT generate {chapter} questions with these defects: {joined}. "
        "Use different structure, length, and sub-part layout."
    )


def build_rejection_record(
    q: Dict[str, Any],
    *,
    user_id: str,
    document_id: Optional[str],
    chapter: str,
    slot_index: int = 0,
    slot_meta: Optional[Dict[str, Any]] = None,
    feedback: str = "",
    source: str = "quality_gate",
) -> Dict[str, Any]:
    """Normalize one rejected question into a corpus record."""
    meta = slot_meta or {}
    stem = (q.get("content") or q.get("question") or "").strip()
    flags = _parse_flags(feedback or collect_rejection_feedback(q))
    return {
        "id": str(uuid.uuid4()),
        "record_type": "rejected",
        "timestamp": _now_iso(),
        "source": source,
        "user_id": user_id,
        "document_id": document_id or "",
        "chapter": (chapter or "generic").strip().lower(),
        "slot": int(meta.get("slot") or slot_index + 1),
        "slot_band": meta.get("band", q.get("slot_band", "")),
        "archetype_id": meta.get("archetype_id") or q.get("archetype_id", ""),
        "question_type": q.get("question_type", ""),
        "ui_difficulty": q.get("difficulty", ""),
        "rejection_flags": flags,
        "rejection_feedback": feedback or "; ".join(flags),
        "stem_preview": stem[:400],
        "combined_score": q.get("combined_score", q.get("quality_score")),
        "negative_instruction": _negative_instruction(flags, chapter or "generic"),
    }


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _append_training_pair(record: Dict[str, Any]) -> None:
    """Instruction-style row for future fine-tuning / RLHF."""
    row = {
        "task": "avoid_rejected_question_pattern",
        "chapter": record.get("chapter"),
        "chapter_title": record.get("chapter", "").replace("_", " ").title(),
        "labels": record.get("rejection_flags", []),
        "instruction": record.get("negative_instruction"),
        "negative_example": record.get("stem_preview"),
        "metadata": {
            "slot": record.get("slot"),
            "slot_band": record.get("slot_band"),
            "archetype_id": record.get("archetype_id"),
            "source": record.get("source"),
            "timestamp": record.get("timestamp"),
        },
    }
    _append_jsonl(TRAINING_JSONL, row)


async def record_rejection(
    q: Dict[str, Any],
    *,
    user_id: str,
    document_id: Optional[str] = None,
    chapter: str = "generic",
    slot_index: int = 0,
    slot_meta: Optional[Dict[str, Any]] = None,
    feedback: str = "",
    source: str = "quality_gate",
) -> None:
    """Persist one rejected question to JSONL + Qdrant (when enabled)."""
    if not settings.ENABLE_REJECTION_CORPUS:
        return
    if not (q.get("content") or q.get("question")):
        return

    record = build_rejection_record(
        q,
        user_id=user_id,
        document_id=document_id,
        chapter=chapter,
        slot_index=slot_index,
        slot_meta=slot_meta,
        feedback=feedback,
        source=source,
    )
    try:
        _append_jsonl(CORPUS_JSONL, record)
        _append_training_pair(record)
    except OSError as e:
        logger.warning("Could not write rejection corpus file: %s", e)

    stem = record["stem_preview"]
    try:
        embeddings = await embed_texts([stem])
        if not embeddings:
            return
        embedding = embeddings[0]
        payload = {
            "record_type": "rejected",
            "user_id": user_id,
            "subject": "Mathematics",
            "document_id": document_id or "",
            "chapter": record["chapter"],
            "content_hash": _content_hash(stem),
            "question_preview": stem[:220],
            "rejection_flags": record["rejection_flags"],
            "rejection_feedback": record["rejection_feedback"],
            "negative_instruction": record["negative_instruction"],
            "slot": record["slot"],
            "slot_band": record["slot_band"],
            "archetype_id": record["archetype_id"],
            "question_type": record["question_type"],
            "ui_difficulty": record["ui_difficulty"],
            "corpus_id": record["id"],
            "timestamp": record["timestamp"],
        }
        point = PointStruct(id=record["id"], vector=embedding, payload=payload)
        await qdrant_client.upsert(
            collection_name=settings.QDRANT_COLLECTION_HISTORY,
            points=[point],
        )
    except Exception as e:
        logger.warning("Rejection corpus Qdrant upsert skipped: %s", e)


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode()).hexdigest()


async def load_rejection_corpus(
    user_id: str,
    *,
    document_id: Optional[str] = None,
    chapter: str = "",
    limit: int | None = None,
) -> Dict[str, Any]:
    """
    Load recent rejections for prompt injection.
    Prefers Qdrant; falls back to tail of JSONL file.
    """
    limit = limit or settings.REJECTION_CORPUS_LIMIT
    ch = (chapter or "").strip().lower()
    out: Dict[str, Any] = {
        "items": [],
        "flag_counts": {},
        "chapter": ch,
    }
    if not settings.ENABLE_REJECTION_CORPUS:
        return out

    items: List[Dict[str, Any]] = []
    try:
        must = [
            FieldCondition(key="record_type", match=MatchValue(value="rejected")),
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
        ]
        if document_id:
            must.append(
                FieldCondition(key="document_id", match=MatchValue(value=document_id))
            )
        if ch:
            must.append(FieldCondition(key="chapter", match=MatchValue(value=ch)))
        results, _ = await qdrant_client.scroll(
            collection_name=settings.QDRANT_COLLECTION_HISTORY,
            scroll_filter=Filter(must=must),
            limit=limit,
            with_payload=True,
        )
        for point in results or []:
            p = point.payload or {}
            items.append(
                {
                    "stem_preview": p.get("question_preview", ""),
                    "rejection_flags": p.get("rejection_flags") or [],
                    "rejection_feedback": p.get("rejection_feedback", ""),
                    "negative_instruction": p.get("negative_instruction", ""),
                    "slot": p.get("slot"),
                    "slot_band": p.get("slot_band"),
                    "archetype_id": p.get("archetype_id"),
                    "timestamp": p.get("timestamp"),
                }
            )
    except Exception as e:
        logger.warning("Rejection corpus Qdrant load failed: %s", e)

    if not items and CORPUS_JSONL.exists():
        try:
            lines = CORPUS_JSONL.read_text(encoding="utf-8").strip().splitlines()
            for line in reversed(lines[-limit * 3 :]):
                if not line.strip():
                    continue
                rec = json.loads(line)
                if ch and rec.get("chapter") != ch:
                    continue
                if document_id and rec.get("document_id") != document_id:
                    continue
                items.append(rec)
                if len(items) >= limit:
                    break
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Rejection corpus JSONL read failed: %s", e)

    items = items[:limit]
    counter: Counter[str] = Counter()
    for it in items:
        for f in it.get("rejection_flags") or []:
            counter[str(f)] += 1
    out["items"] = items
    out["flag_counts"] = dict(counter.most_common(12))
    return out


def rejection_avoidance_prompt(
    corpus: Dict[str, Any],
    *,
    locked_chapter: str = "",
    max_examples: int | None = None,
) -> str:
    """Prompt block: teach the model what NOT to generate."""
    items = corpus.get("items") or []
    if not items:
        return ""
    max_examples = max_examples or settings.REJECTION_CORPUS_PROMPT_MAX_EXAMPLES
    ch = locked_chapter or corpus.get("chapter") or "this chapter"
    lines = [
        "REJECTION CORPUS (mandatory — do NOT repeat these failure patterns):",
        f"- Chapter: {ch}. These stems FAILED quality gates; write differently.",
    ]
    counts = corpus.get("flag_counts") or {}
    if counts:
        freq = ", ".join(f"{k} ({v}×)" for k, v in list(counts.items())[:10])
        lines.append(f"- Banned defect patterns (frequency): {freq}")
    for it in items[:max_examples]:
        flags = it.get("rejection_flags") or []
        flag_str = ", ".join(flags[:6]) if flags else "quality_fail"
        preview = (it.get("stem_preview") or "")[:160]
        if preview:
            lines.append(f"- [{flag_str}] {preview}")
    lines.append(
        "- New stems: different numbers, labels, length band, and sub-part structure."
    )
    return "\n".join(lines) + "\n"


async def record_rejection_batch(
    questions: List[Dict[str, Any]],
    *,
    user_id: str,
    document_id: Optional[str],
    chapter: str,
    slot_meta_list: Optional[List[Dict[str, Any]]] = None,
    source: str = "quality_gate",
) -> int:
    """Record multiple rejections; returns count stored."""
    n = 0
    for i, q in enumerate(questions):
        meta = (slot_meta_list or [{}])[i] if slot_meta_list else {}
        await record_rejection(
            q,
            user_id=user_id,
            document_id=document_id,
            chapter=chapter,
            slot_index=i,
            slot_meta=meta,
            source=source,
        )
        n += 1
    return n
