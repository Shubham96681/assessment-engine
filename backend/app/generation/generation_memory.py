"""
Temporal memory — avoid repeating theorem combos, archetypes, and cognitive patterns
across recent papers for the same user/document.
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.core.vector_store import qdrant_client, Filter, FieldCondition, MatchValue
from app.generation.theorem_coverage_score import (
    CHAPTER_THEOREM_COMBOS,
    detect_cognitive_type,
    detect_theorems_in_stem,
)
logger = logging.getLogger(__name__)


async def load_generation_memory(
    user_id: str,
    *,
    document_id: Optional[str] = None,
    subject: str = "Mathematics",
    limit: int | None = None,
) -> Dict[str, Any]:
    """Recent paper fingerprints from Qdrant generation_history."""
    limit = limit or settings.GENERATION_MEMORY_LIMIT
    memory: Dict[str, Any] = {
        "recent_theorems": [],
        "recent_combos": [],
        "recent_cognitive": [],
        "recent_archetypes": [],
        "theorem_counts": {},
        "combo_counts": {},
    }
    try:
        must = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="subject", match=MatchValue(value=subject or "Mathematics")),
        ]
        if document_id:
            must.append(
                FieldCondition(key="document_id", match=MatchValue(value=document_id))
            )
        results, _ = await qdrant_client.scroll(
            collection_name=settings.QDRANT_COLLECTION_HISTORY,
            scroll_filter=Filter(must=must),
            limit=limit,
            with_payload=True,
        )
        th_counter: Counter[str] = Counter()
        combo_counter: Counter[str] = Counter()
        cog_counter: Counter[str] = Counter()
        arch_counter: Counter[str] = Counter()
        recent_th: List[str] = []
        recent_combo: List[str] = []
        recent_cog: List[str] = []
        recent_arch: List[str] = []

        for point in results or []:
            p = point.payload or {}
            for tid in p.get("theorem_ids") or []:
                th_counter[tid] += 1
                if tid not in recent_th:
                    recent_th.append(tid)
            for cid in p.get("combo_ids") or []:
                combo_counter[cid] += 1
                if cid not in recent_combo:
                    recent_combo.append(cid)
            cog = p.get("cognitive_type")
            if cog:
                cog_counter[cog] += 1
                if cog not in recent_cog:
                    recent_cog.append(cog)
            arch = p.get("archetype_id")
            if arch:
                arch_counter[arch] += 1
                if arch not in recent_arch:
                    recent_arch.append(arch)

        memory["recent_theorems"] = recent_th[:20]
        memory["recent_combos"] = recent_combo[:12]
        memory["recent_cognitive"] = recent_cog[:8]
        memory["recent_archetypes"] = recent_arch[:12]
        memory["theorem_counts"] = dict(th_counter.most_common(15))
        memory["combo_counts"] = dict(combo_counter.most_common(10))
        memory["cognitive_counts"] = dict(cog_counter.most_common(6))
    except Exception as e:
        logger.warning("Could not load generation memory: %s", e)
    return memory


def memory_avoidance_prompt(
    memory: Dict[str, Any],
    *,
    locked_chapter: str = "",
) -> str:
    """Blueprint fragment: do not repeat recent patterns (same chapter only)."""
    if not any(
        memory.get(k)
        for k in ("recent_combos", "recent_theorems", "recent_cognitive")
    ):
        return ""
    from app.generation.prompt_purity import filter_memory_prompt_block

    lines = ["TEMPORAL MEMORY (vary from user's recent papers — same chapter only):"]
    if memory.get("recent_combos"):
        lines.append(
            f"- Avoid repeating combos: {', '.join(memory['recent_combos'][:6])}"
        )
    if memory.get("recent_theorems"):
        lines.append(
            f"- Use different emphasis than recent theorems: "
            f"{', '.join(memory['recent_theorems'][:8])}"
        )
    if memory.get("recent_cognitive"):
        lines.append(
            f"- Vary cognitive rhythm (recent was heavy on): "
            f"{', '.join(memory['recent_cognitive'][:4])}"
        )
    block = "\n".join(lines) + "\n"
    if locked_chapter:
        block = filter_memory_prompt_block(block, locked_chapter)
    return block


def reorder_theorems_avoid_memory(
    required_theorems: List[Dict[str, str]],
    memory: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Deprioritize theorems/combos that appeared heavily in recent papers."""
    if not required_theorems:
        return required_theorems
    th_counts = memory.get("theorem_counts") or {}
    combo_counts = memory.get("combo_counts") or {}
    recent_combos = set(memory.get("recent_combos") or [])

    def penalty(t: Dict[str, str]) -> float:
        p = th_counts.get(t.get("id", ""), 0) * 0.15
        tid = t.get("id", "")
        for combo in CHAPTER_THEOREM_COMBOS.get(
            memory.get("chapter", ""), []
        ):
            if combo["id"] in recent_combos and tid in (combo.get("requires") or []):
                p += combo_counts.get(combo["id"], 0) * 0.2 + 0.5
        return p

    ranked = sorted(required_theorems, key=penalty)
    return ranked


def paper_fingerprint(
    questions: List[Dict[str, Any]],
    *,
    chapter: str,
    required_theorems: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Extract combo/cognitive/theorem signature for one delivered paper."""
    all_th: Set[str] = set()
    cog_set: Set[str] = set()
    for q in questions:
        stem = q.get("content") or ""
        all_th |= detect_theorems_in_stem(stem, required_theorems)
        cog_set.add(
            q.get("detected_cognitive_type")
            or detect_cognitive_type(
                stem,
                next(
                    (t for t in required_theorems if t.get("id") in all_th),
                    None,
                ),
            )
        )

    satisfied: List[str] = []
    for combo in CHAPTER_THEOREM_COMBOS.get(chapter, []):
        req = set(combo.get("requires") or [])
        if req and req <= all_th:
            satisfied.append(combo["id"])

    return {
        "theorem_ids": sorted(all_th),
        "combo_ids": satisfied,
        "cognitive_types": sorted(cog_set),
        "chapter": chapter,
    }


async def record_paper_memory(
    questions: List[Dict[str, Any]],
    *,
    user_id: str,
    subject: str,
    class_level: str,
    document_id: Optional[str],
    chapter: str,
    required_theorems: List[Dict[str, str]],
) -> None:
    """Store per-question temporal fingerprints into generation_history."""
    from app.generation.dedup import DedupEngine

    if not settings.ENABLE_GENERATION_MEMORY:
        return
    fp = paper_fingerprint(questions, chapter=chapter, required_theorems=required_theorems)
    dedup = DedupEngine()
    for q in questions:
        emb = q.get("embedding")
        if not emb:
            continue
        q["theorem_ids"] = fp.get("theorem_ids", [])
        q["combo_ids"] = fp.get("combo_ids", [])
        q["cognitive_type"] = q.get("detected_cognitive_type") or (
            fp.get("cognitive_types", ["computation"])[0]
            if fp.get("cognitive_types")
            else "computation"
        )
        q["archetype_id"] = q.get("archetype_id") or q.get("planned_theorem_id")
    await dedup.record_questions_to_history(
        questions,
        user_id,
        subject,
        class_level,
        document_id=document_id,
    )
