"""
Filter retrieved chunks by locked chapter — drop obvious cross-chapter contamination.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.generation.strict_topic_gate import CHAPTER_FORBIDDEN

# Chunks should contain at least one hint for locked chapter
CHAPTER_CHUNK_HINTS: Dict[str, List[str]] = {
    "quadrilaterals": [
        "parallelogram",
        "quadrilateral",
        "rhombus",
        "trapezium",
        "diagonal",
        "midpoint",
        "rectangle",
    ],
    "quadratic": [
        "quadratic",
        "discriminant",
        "roots",
        "x2",
        "x²",
        "factorisation",
        "polynomial",
    ],
    "circles": ["circle", "tangent", "radius", "chord", "secant"],
    "trigonometry": [
        "sin",
        "cos",
        "tan",
        "radian",
        "identity",
        "trigonometric",
        "cot",
        "sec",
        "cosec",
    ],
    "triangles": [
        "triangle",
        "congruent",
        "similar",
        "pythagoras",
        "angle",
        "side",
    ],
}


def score_chunk_for_chapter(text: str, locked_chapter: str) -> float:
    if not text or locked_chapter in ("generic", ""):
        return 1.0
    low = text.lower()
    score = 0.5
    for hint in CHAPTER_CHUNK_HINTS.get(locked_chapter, []):
        if hint in low:
            score += 0.15
    forbidden = CHAPTER_FORBIDDEN.get(locked_chapter, set())
    for term in forbidden:
        if " " in term:
            if term in low:
                score -= 0.35
        elif re.search(rf"\b{re.escape(term)}\b", low):
            score -= 0.25
    return max(0.0, min(1.0, score))


def filter_chunks_by_chapter(
    chunks: List[Dict[str, Any]],
    locked_chapter: str,
    *,
    min_score: float = 0.35,
    min_keep: int = 2,
) -> List[Dict[str, Any]]:
    if not chunks or locked_chapter in ("generic", ""):
        return chunks
    scored = []
    for c in chunks:
        text = c.get("text") or ""
        s = score_chunk_for_chapter(text, locked_chapter)
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    kept = [c for s, c in scored if s >= min_score]
    if len(kept) < min_keep:
        kept = [c for _, c in scored[: max(min_keep, len(scored))]]
    return kept
