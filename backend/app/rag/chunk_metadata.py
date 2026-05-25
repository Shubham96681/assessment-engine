"""
Label ingested chunks with chapter / section metadata for scoped retrieval.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.generation.chapter_concept_classifier import resolve_locked_chapter
from app.generation.rd_archetypes import detect_chapter_key


def label_chunk_payload(
    chunk: Dict[str, Any],
    *,
    filename: str = "",
    subject: str = "",
) -> Dict[str, Any]:
    """Attach locked_chapter, section hints, and retrieval keywords to a chunk payload."""
    text = chunk.get("text") or ""
    locked, source, confidence = resolve_locked_chapter(
        filename=filename,
        context=text[:1200],
    )
    if locked == "generic":
        locked = detect_chapter_key("", filename, text[:800])

    keywords: List[str] = []
    for pat in (
        r"EXERCISE\s+[\d.]+",
        r"Example\s+\d+",
        r"Theorem\s+[\d.]+",
        r"tangent|secant|chord|radius|circle",
        r"quadratic|discriminant|roots",
        r"parallelogram|rhombus|trapezium",
        r"sin|cos|tan|identity|radian",
        r"similar\s+triangles|congruence|pythagoras",
    ):
        if re.search(pat, text, re.I):
            keywords.append(pat.split("|")[0].lower())

    out = dict(chunk)
    out["locked_chapter"] = locked
    out["chapter_source"] = source
    out["chapter_confidence"] = round(confidence, 3)
    out["retrieval_keywords"] = list(dict.fromkeys(keywords))[:12]
    out["section_type"] = chunk.get("section_type") or "paragraph"
    out["section_label"] = chunk.get("section_label") or ""
    out["exercise_id"] = chunk.get("exercise_id") or ""
    if subject:
        out["subject"] = subject
    return out


def boost_chunk_for_query(chunk: Dict[str, Any], query: str, locked_chapter: str) -> float:
    """Lexical boost 0..1 for reranking after dense+BM25 fusion."""
    text = (chunk.get("text") or "").lower()
    q = (query or "").lower()
    score = 0.0
    if locked_chapter and chunk.get("locked_chapter") == locked_chapter:
        score += 0.35
    for kw in chunk.get("retrieval_keywords") or []:
        if kw in q or kw in text:
            score += 0.08
    st = chunk.get("section_type") or ""
    if st in ("example", "exercise", "exercise_item") and any(
        w in q for w in ("exercise", "example", "find", "prove")
    ):
        score += 0.12
    q_tokens = set(re.findall(r"[a-z0-9]{3,}", q))
    if q_tokens:
        hits = sum(1 for t in q_tokens if t in text)
        score += min(0.35, hits * 0.04)
    return min(1.0, score)
