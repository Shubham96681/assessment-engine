"""
Chapter concept classifier — lock generation to the selected PDF chapter.

Resolves authoritative chapter from filename / topic_focus / CONTEXT, and
classifies each question stem to detect drift (e.g. quadratic area → quadratic,
cyclic quad → quadrilaterals, tangents → circles).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Strong concept → chapter (checked before loose keywords)
_CONCEPT_PATTERNS: List[Tuple[str, str, float]] = [
    # (regex or keyword blob, chapter_key, weight)
    (r"\bquadratic\s+equation|\bdiscriminant\b|nature\s+of\s+roots|x\^2|x²|equal\s+roots", "quadratic", 3.0),
    (r"\bform\s+the\s+quadratic|\b2x²|\bax²\s*\+\s*bx", "quadratic", 2.5),
    (r"\barea\s+is\s+\d+.*\b(?:breadth|length|width)|length\s+is\s+(?:twice|2\s*times).*breadth", "quadratic", 2.0),
    (r"\btangent|\bsecant|\bconcentric\s+circle|\bradius\b|\bpoint\s+of\s+contact", "circles", 3.0),
    (r"\bexternal\s+point.*tangent|tangents?\s+[A-Z][A-Z].*circle", "circles", 2.5),
    (r"\bparallelogram|\brhombus|\btrapezium|\btrapezoid|\bmidpoint\s+theorem", "quadrilaterals", 3.0),
    (r"\bcyclic\s+quadrilateral|opposite\s+angles.*supplementary|diagonals?\s+of\s+.*parallelogram", "quadrilaterals", 2.5),
    (r"\bdiagonal.*bisect|prove.*parallelogram", "quadrilaterals", 2.0),
    (r"\bsimilar\s+triangles|\bcongruence|\bpythagoras", "triangles", 2.0),
    (r"\barithmetic\s+progression|\bcommon\s+difference|\bnth\s+term", "arithmetic", 2.0),
    (r"\btrigonometric\s+identity|\bsin\s*\(|angle\s+of\s+elevation", "trigonometry", 2.0),
]

_FILENAME_CHAPTER: List[Tuple[str, str]] = [
    ("quadratic", "quadratic"),
    ("quadrilateral", "quadrilaterals"),
    ("circle", "circles"),
    ("triangle", "triangles"),
    ("polynomial", "polynomials"),
    ("coordinate", "coordinate"),
    ("trigonometry", "trigonometry"),
    ("statistics", "statistics"),
    ("probability", "probability"),
]


def _score_text_for_chapters(text: str) -> Dict[str, float]:
    low = (text or "").lower()
    scores: Dict[str, float] = {}
    for pattern, chapter, weight in _CONCEPT_PATTERNS:
        if re.search(pattern, low, re.I):
            scores[chapter] = scores.get(chapter, 0) + weight
    return scores


def resolve_locked_chapter(
    *,
    filename: str = "",
    topic_focus: str = "",
    context: str = "",
) -> Tuple[str, str, float]:
    """
    Authoritative chapter for this generation run.
    Returns (chapter_key, source, confidence).
    Priority: explicit topic_focus > filename > CONTEXT headline scoring.
    """
    blob_focus = (topic_focus or "").lower()
    for key, chapter in _FILENAME_CHAPTER:
        if key in blob_focus:
            return chapter, "topic_focus", 0.95

    low_fn = (filename or "").lower()
    for key, chapter in _FILENAME_CHAPTER:
        if key in low_fn:
            return chapter, "filename", 0.92

    ctx_scores = _score_text_for_chapters(context[:3000])
    if ctx_scores:
        best = max(ctx_scores, key=ctx_scores.get)
        total = sum(ctx_scores.values()) or 1
        conf = ctx_scores[best] / total
        if conf >= 0.35:
            return best, "context", min(0.9, conf + 0.3)

    from app.generation.rd_archetypes import detect_chapter_key

    ch = detect_chapter_key(topic_focus, filename, context)
    return ch, "detect_chapter_key", 0.5


def classify_stem_chapter(stem: str) -> Tuple[str, float, Dict[str, float]]:
    """Infer chapter from question stem only."""
    scores = _score_text_for_chapters(stem)
    if not scores:
        return "generic", 0.0, scores
    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    return best, scores[best] / total, scores


def stem_matches_locked_chapter(stem: str, locked_chapter: str) -> Tuple[bool, str]:
    """
    True if stem fits locked chapter; else returns False + reason.
    """
    if locked_chapter in ("generic", ""):
        return True, ""
    detected, conf, _ = classify_stem_chapter(stem)
    if detected == "generic" or conf < 0.25:
        return True, ""
    if detected == locked_chapter:
        return True, ""
    return False, f"stem_chapter_mismatch:{detected}_vs_{locked_chapter}"


def context_supports_chapter(context: str, locked_chapter: str, min_score: float = 1.0) -> bool:
    scores = _score_text_for_chapters(context[:4000])
    if locked_chapter not in scores:
        return locked_chapter == "generic"
    return scores.get(locked_chapter, 0) >= min_score
