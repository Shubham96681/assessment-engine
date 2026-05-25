"""
Strict topic gate — reject questions whose concepts belong to another chapter.

Prevents Circles / Quadratic leakage when user selected Quadrilaterals (etc.).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.generation.chapter_concept_classifier import (
    classify_stem_chapter,
    resolve_locked_chapter,
    stem_matches_locked_chapter,
)

# Tokens that must NOT appear when locked chapter is set (case-insensitive word boundary)
CHAPTER_FORBIDDEN: Dict[str, Set[str]] = {
    "quadrilaterals": {
        "circle",
        "tangent",
        "tangents",
        "secant",
        "secants",
        "radius",
        "radii",
        "concentric",
        "point of contact",
        "external point",
        "cyclic angle",  # circle cyclic unless explicit quad cyclic
    },
    "quadratic": {
        "tangent",
        "secant",
        "radius",
        "concentric",
        "parallelogram",
        "rhombus",
        "trapezium",
        "midpoint theorem",
    },
    "circles": {
        "parallelogram",
        "rhombus",
        "trapezium",
        "discriminant",
        "quadratic equation",
        "nature of roots",
    },
    "triangles": {
        "tangent",
        "secant",
        "discriminant",
        "parallelogram",
    },
    "trigonometry": {
        "circle",
        "secant",
        "concentric",
        "parallelogram",
        "discriminant",
        "quadratic equation",
        "∫",
        "integral",
        " dx",
        "d/dx",
        "differentiate",
        "integration by parts",
    },
}

# At least one should appear for non-generic chapters (soft — paired with classifier)
CHAPTER_ALLOWED_HINTS: Dict[str, Set[str]] = {
    "quadrilaterals": {
        "parallelogram",
        "quadrilateral",
        "rhombus",
        "trapezium",
        "trapezoid",
        "rectangle",
        "square",
        "kite",
        "diagonal",
        "diagonals",
        "midpoint",
        "opposite sides",
        "opposite angles",
        "cyclic",
    },
    "quadratic": {
        "quadratic",
        "x²",
        "x^2",
        "discriminant",
        "roots",
        "factorisation",
        "factorization",
        "breadth",
        "area is",
        "polynomial",
    },
    "circles": {
        "circle",
        "tangent",
        "radius",
        "chord",
        "secant",
        "centre",
        "center",
    },
}


def _contains_forbidden(stem: str, forbidden: Set[str]) -> List[str]:
    low = stem.lower()
    hits = []
    for term in forbidden:
        if " " in term:
            if term in low:
                hits.append(term)
        elif re.search(rf"\b{re.escape(term)}\b", low):
            hits.append(term)
    return hits


def _alignment_label(score: float) -> str:
    if score >= 0.85:
        return "fully_aligned"
    if score >= 0.70:
        return "acceptable"
    if score >= 0.40:
        return "partial_drift"
    return "wrong_chapter"


def compute_topic_alignment_score(
    stem: str,
    *,
    locked_chapter: str,
) -> tuple[float, List[str], str, float]:
    """
    Graded alignment in [0, 1] — not binary valid/invalid.
    Returns (score, flags, detected_chapter, classifier_confidence).
    """
    flags: List[str] = []
    score = 1.0
    detected, conf, _ = classify_stem_chapter(stem)

    forbidden = CHAPTER_FORBIDDEN.get(locked_chapter, set())
    hits = _contains_forbidden(stem, forbidden)
    if hits:
        flags.append(f"forbidden_concepts:{','.join(hits[:5])}")
        score -= min(0.55, 0.18 * len(hits))

    match, reason = stem_matches_locked_chapter(stem, locked_chapter)
    if match:
        score += 0.08
    elif reason:
        flags.append(reason)
        score -= 0.32

    hints = CHAPTER_ALLOWED_HINTS.get(locked_chapter, set())
    if any(re.search(rf"\b{re.escape(h)}\b", stem, re.I) for h in hints):
        score += 0.06

    if conf >= 0.35 and detected == locked_chapter:
        score += 0.10 * conf
    elif conf >= 0.45 and detected not in (locked_chapter, "generic"):
        flags.append(f"classifier_drift:{detected}_conf_{conf:.2f}")
        score -= 0.25 + 0.35 * conf

    if locked_chapter == "quadrilaterals" and re.search(
        r"\bform\s+the\s+quadratic|\bx\s*metres?\).*area|\barea\s+is\s+\d+\s*m",
        stem,
        re.I,
    ):
        flags.append("quadratic_word_problem_in_quadrilaterals")
        score -= 0.45

    if locked_chapter == "quadratic" and re.search(
        r"\bprove.*parallelogram|\bdiagonals?\s+of\s+.*rhombus",
        stem,
        re.I,
    ):
        flags.append("geometry_proof_in_quadratic")
        score -= 0.45

    score = max(0.0, min(1.0, round(score, 3)))
    return score, flags, detected, conf


def evaluate_topic_gate(
    q: Dict[str, Any],
    *,
    locked_chapter: str,
    locked_source: str = "",
) -> Dict[str, Any]:
    stem = (q.get("content") or "").strip()

    if not stem or locked_chapter in ("generic", ""):
        return {
            "topic_gate_ok": True,
            "topic_gate_flags": [],
            "topic_alignment_score": 1.0,
            "topic_gate_score": 1.0,
            "topic_alignment_label": "fully_aligned",
            "locked_chapter": locked_chapter,
            "detected_stem_chapter": "generic",
        }

    score, flags, detected, conf = compute_topic_alignment_score(
        stem, locked_chapter=locked_chapter
    )
    reject_at = settings.TOPIC_ALIGNMENT_REJECT_THRESHOLD
    ok = score >= reject_at

    return {
        "topic_gate_ok": ok,
        "topic_gate_flags": flags,
        "topic_alignment_score": score,
        "topic_gate_score": score,
        "topic_alignment_label": _alignment_label(score),
        "locked_chapter": locked_chapter,
        "detected_stem_chapter": detected,
        "classifier_confidence": round(conf, 3),
    }


def should_reject_topic_drift(
    q: Dict[str, Any],
    *,
    locked_chapter: str,
    min_score: float | None = None,
) -> bool:
    report = evaluate_topic_gate(q, locked_chapter=locked_chapter)
    q.update(report)
    threshold = (
        min_score
        if min_score is not None
        else settings.TOPIC_ALIGNMENT_REJECT_THRESHOLD
    )
    return report.get("topic_alignment_score", 0) < threshold


def filter_questions_by_topic(
    questions: List[Dict[str, Any]],
    *,
    locked_chapter: str,
    lenient_fallback: bool = True,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (accepted, rejected)."""
    if not questions or locked_chapter in ("generic", ""):
        return questions, []

    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for q in questions:
        if should_reject_topic_drift(q, locked_chapter=locked_chapter):
            q["rejected_by"] = "strict_topic_gate"
            rejected.append(q)
        else:
            accepted.append(q)

    if not accepted and questions and lenient_fallback:
        import logging

        logging.getLogger(__name__).warning(
            "Topic gate rejected all %d items (locked=%s) — lenient fallback keeps best by alignment score",
            len(questions),
            locked_chapter,
        )
        for q in questions:
            if "topic_alignment_score" not in q:
                evaluate_topic_gate(q, locked_chapter=locked_chapter)
        ranked = sorted(
            questions,
            key=lambda x: x.get("topic_alignment_score", 0),
            reverse=True,
        )
        for q in ranked:
            q["topic_gate_lenient"] = True
        return ranked, rejected

    return accepted, rejected


def blueprint_archetype_pool_only(locked_chapter: str) -> str:
    """Instruction fragment: archetypes must come from this chapter only."""
    return (
        f"\nLOCKED CHAPTER (mandatory): {locked_chapter}\n"
        f"- Archetype pool is ONLY {locked_chapter} patterns.\n"
        f"- FORBIDDEN in every stem: {', '.join(sorted(CHAPTER_FORBIDDEN.get(locked_chapter, set()))[:12])}.\n"
    )
