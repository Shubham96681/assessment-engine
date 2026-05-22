"""
Extract primary topic, locked chapter, and subtopics from a document's indexed chunks.
Used by the topic agent and the Generate UI topic profile endpoint.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.vector_store import qdrant_client
from app.generation.chapter_concept_classifier import (
    resolve_locked_chapter,
    _score_text_for_chapters,
)
from app.generation.content_profile import parse_filename_hints
from app.generation.theorem_coverage import catalog_for_chapter, infer_required_theorems
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Headings / section labels common in NCERT / RD Sharma PDFs
_HEADING_RE = re.compile(
    r"(?im)^(?:"
    r"chapter\s+[\divxlcdm]+(?:\s*[:.\-–]\s*[^\n]{3,60})?"
    r"|exercise\s+[\d.]+(?:\s*[:.\-–]\s*[^\n]{3,50})?"
    r"|(?:\d+\.){1,2}\s+[A-Z][^\n]{4,55}"
    r"|theorem\s+[\d.]+[^\n]{0,40}"
    r"|summary\s+of\s+[^\n]{4,40}"
    r")"
)
_BULLET_TOPIC_RE = re.compile(
    r"(?i)\b(?:properties?|types?|theorems?|conditions?|applications?|"
    r"formulas?|identities?|methods?|constructions?)\s+of\s+([^\n.;]{4,45})"
)
_KEY_PHRASE_RE = re.compile(
    r"(?i)\b(?:prove|show\s+that|find|calculate|evaluate|solve|derive|"
    r"discriminant|tangent|parallelogram|rhombus|trapezium|"
    r"quadratic\s+equation|nature\s+of\s+roots|midpoint\s+theorem|"
    r"cyclic\s+quadrilateral|similar\s+triangles|arithmetic\s+progression)\b"
)


def _clean_label(text: str, max_len: int = 72) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    t = re.sub(r"[^\w\s\-–:().,²³√πθ]", "", t)
    return t[:max_len].strip(" .-")


def _primary_topic_from_filename(filename: str, locked_chapter: str) -> str:
    """Derive display topic when Qdrant has no chunks (filename is reliable for NCERT-style PDFs)."""
    hints = parse_filename_hints(filename or "")
    title = hints.get("chapter_title") or ""
    if title and len(title) > 3:
        return _clean_label(title, 80)
    stem = (filename or "").rsplit(".", 1)[0]
    stem = re.sub(r"[_]+", " ", stem).strip()
    if stem:
        return _clean_label(stem, 80)
    return _clean_label(locked_chapter.replace("_", " ").title(), 80)


async def scroll_document_text(
    document_id: str,
    *,
    limit: int = 120,
) -> List[Dict[str, Any]]:
    """Load chunk payloads for one document from Qdrant."""
    chunks: List[Dict[str, Any]] = []
    try:
        results, _ = await qdrant_client.scroll(
            collection_name=settings.QDRANT_COLLECTION_DOCUMENTS,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id", match=MatchValue(value=document_id)
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
        )
        for point in results or []:
            payload = point.payload or {}
            text = (payload.get("text") or "").strip()
            if not text:
                continue
            chunks.append(
                {
                    "text": text,
                    "page_num": payload.get("page_num"),
                    "qdrant_id": str(point.id),
                }
            )
    except Exception:
        return []
    return chunks


def _extract_headings_from_text(blob: str) -> List[str]:
    labels: List[str] = []
    for m in _HEADING_RE.finditer(blob):
        line = _clean_label(m.group(0))
        if len(line) >= 6 and line.lower() not in {x.lower() for x in labels}:
            labels.append(line)
    for m in _BULLET_TOPIC_RE.finditer(blob):
        line = _clean_label(f"Properties of {m.group(1)}")
        if len(line) >= 10:
            labels.append(line)
    return labels[:24]


def _extract_concept_phrases(blob: str, limit: int = 16) -> List[str]:
    counter: Counter[str] = Counter()
    for m in _KEY_PHRASE_RE.finditer(blob):
        phrase = m.group(0).lower()
        counter[phrase] += 1
    return [p.title() for p, _ in counter.most_common(limit)]


def build_topic_profile(
    *,
    document_id: str,
    filename: str = "",
    topic_focus: str = "",
    subject: str = "",
    class_level: str = "",
    chunks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Synchronous profile builder when chunks are already loaded.
    """
    blob = "\n".join((c.get("text") or "")[:800] for c in (chunks or [])[:80])
    locked_chapter, source, confidence = resolve_locked_chapter(
        filename=filename,
        topic_focus=topic_focus,
        context=blob,
    )

    headings = _extract_headings_from_text(blob)
    concept_phrases = _extract_concept_phrases(blob)

    chapter_scores = _score_text_for_chapters(blob)
    secondary_chapters = [
        ch
        for ch, sc in sorted(chapter_scores.items(), key=lambda x: -x[1])
        if ch != locked_chapter and sc >= 1.0
    ][:4]

    subtopics: List[str] = []
    seen: set[str] = set()

    def _add(label: str) -> None:
        key = label.lower()
        if key in seen or len(label) < 5:
            return
        seen.add(key)
        subtopics.append(label)

    if topic_focus:
        _add(_clean_label(topic_focus))
    for h in headings:
        _add(h)
    for p in concept_phrases:
        _add(p)

    primary_topic = topic_focus or _primary_topic_from_filename(filename, locked_chapter)
    if headings:
        primary_topic = _clean_label(headings[0], 80)
    elif not blob.strip():
        primary_topic = _primary_topic_from_filename(filename, locked_chapter)

    if not subtopics and locked_chapter not in ("generic", ""):
        for t in catalog_for_chapter(locked_chapter)[:8]:
            _add(t.get("label") or t.get("id", ""))

    required_theorems = infer_required_theorems(
        locked_chapter,
        blob,
        subtopics,
    )

    primary = _clean_label(primary_topic, 80)
    if not primary:
        primary = _primary_topic_from_filename(filename, locked_chapter)

    return {
        "document_id": document_id,
        "primary_topic": primary,
        "index_status": "indexed" if chunks else "no_chunks_in_vector_store",
        "locked_chapter": locked_chapter,
        "locked_chapter_source": source,
        "confidence": round(confidence, 3),
        "subject": subject or "Mathematics",
        "class_level": class_level or "",
        "subtopics": subtopics[:20],
        "secondary_chapters": secondary_chapters,
        "required_theorems": required_theorems,
        "chunk_count_used": len(chunks or []),
        "headings_found": len(headings),
    }


async def extract_document_topic_profile(
    document_id: str,
    *,
    filename: str = "",
    topic_focus: str = "",
    subject: str = "",
    class_level: str = "",
) -> Dict[str, Any]:
    chunks = await scroll_document_text(document_id)
    profile = build_topic_profile(
        document_id=document_id,
        filename=filename,
        topic_focus=topic_focus,
        subject=subject,
        class_level=class_level,
        chunks=chunks,
    )
    profile["sample_pages"] = sorted(
        {c["page_num"] for c in chunks if c.get("page_num") is not None}
    )[:12]
    return profile
