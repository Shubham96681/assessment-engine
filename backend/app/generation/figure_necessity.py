"""
Figure necessity — FigureBased only when reasoning truly needs a visual model.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from app.generation.rd_archetypes import ARCHETYPE_BY_ID

# Archetype ids that legitimately need a figure (diagram / table / graph)
_ARCHETYPE_REQUIRES_FIGURE: Dict[str, bool] = {
    # Quadratic
    "word_problem_area": True,
    "hots_quad": True,  # often OR word + diagram
    "equal_roots_k": True,  # table of coefficients ok
    "nature_of_roots": False,
    "factorisation_roots": False,
    "formula_roots": False,
    # Circles (when used)
    "length_find": True,
    "angle_theorem": True,
    "hidden_theorem": True,
    "concentric": True,
    "chord_tangent": True,
    "secant_tangent": True,
    "tangent_similarity": True,
    "cyclic_angle": True,
    "common_tangent": True,
    "hots_mixed": True,
    "direct_theorem": True,
    "converse_identify": False,
    # Generic
    "word_problem": True,
    "numerical_find": False,
    "concept_apply": False,
    "proof_derive": False,
    "multi_step": False,
    "hots_fusion": True,
}


def archetype_requires_figure_reasoning(archetype_id: str) -> bool:
    if not archetype_id:
        return False
    if archetype_id in _ARCHETYPE_REQUIRES_FIGURE:
        return _ARCHETYPE_REQUIRES_FIGURE[archetype_id]
    arch = ARCHETYPE_BY_ID.get(archetype_id) or {}
    return bool(arch.get("requires_figure_reasoning", False))


def _stem_demands_visual_model(stem: str) -> bool:
    low = stem.lower()
    if re.search(
        r"\b(?:plot|graph|table|diagram|rectangle|triangle|field|grove|plot\s+pqrs|"
        r"breadth|length|segment|road|highway|cities)\b",
        low,
    ):
        return re.search(r"\b[a-z]\s*=\s*\d|\d+\s*(?:km|m|m²)\b", stem, re.I) is not None
    return False


def validate_figure_necessity(q: Dict[str, Any]) -> Dict[str, Any]:
    """
    decorative_figure when FigureBased but algebra-only stem.
    """
    flags: List[str] = []
    score = 1.0
    qtype = q.get("question_type") or ""
    if qtype != "FigureBased":
        return {
            "figure_necessity_score": 1.0,
            "figure_necessity_flags": [],
            "figure_is_necessary": True,
        }

    stem = (q.get("content") or "").strip()
    arch_id = (
        q.get("archetype_id")
        or q.get("planned_theorem_id")
        or q.get("detected_archetype")
        or ""
    )
    needs_figure = archetype_requires_figure_reasoning(arch_id) or _stem_demands_visual_model(
        stem
    )

    from app.generation.stem_dependency_validator import _has_explicit_polynomial

    algebra_only = _has_explicit_polynomial(stem) and not _stem_demands_visual_model(stem)
    if algebra_only and not needs_figure:
        flags.append("decorative_figure")
        score = 0.25

    if len(stem.split()) < 12 and not _stem_demands_visual_model(stem):
        flags.append("thin_figure_stem")
        score -= 0.2

    if re.search(r"by factorisation|discriminant of|nature of roots of", stem, re.I):
        if not _stem_demands_visual_model(stem):
            flags.append("algebra_should_be_short_answer")
            score = min(score, 0.3)

    fn_score = max(0.0, min(1.0, score))
    return {
        "figure_necessity_score": round(fn_score, 3),
        "figure_necessity_flags": flags,
        "figure_is_necessary": fn_score >= 0.55,
        "suggested_type": "ShortAnswer" if "decorative_figure" in flags else qtype,
    }


def should_reject_decorative_figure(q: Dict[str, Any]) -> bool:
    if "figure_necessity_score" not in q:
        q.update(validate_figure_necessity(q))
    flags = q.get("figure_necessity_flags") or []
    if "decorative_figure" in flags or "algebra_should_be_short_answer" in flags:
        return True
    return not q.get("figure_is_necessary", True) and q.get("question_type") == "FigureBased"
