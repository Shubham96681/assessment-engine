"""
Semantic completeness — stem must be self-contained and solvable from text alone.
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Set, Tuple

from app.generation.idiomatic_geometry_patterns import detect_awkward_idiom
from app.generation.common_tangent_values import (
    is_common_external_tangent_stem,
    stem_has_required_external_tangent_givens,
    stem_has_valid_external_tangent_givens,
)
from app.generation.geometry_graph_validator import (
    validate_geometry_graph,
    apply_minimum_context,
)


def _extract_point_labels(text: str) -> Set[str]:
    labels: Set[str] = set()
    if not text:
        return labels
    for m in re.finditer(
        r"\b(?:angle|triangle|quadrilateral)\s+([A-Z])([A-Z])([A-Z]?)\b",
        text,
        re.I,
    ):
        for g in m.groups():
            if g:
                labels.add(g.upper())
    for m in re.finditer(r"\b([A-Z])([A-Z])\b", text):
        labels.add(m.group(1).upper())
        labels.add(m.group(2).upper())
    for m in re.finditer(
        r"\b(?:centre|center|point|at)\s+([A-Z])\b|"
        r"\b([A-Z])\s*=\s*\d|"
        r"\bfrom\s+([A-Z])\b|"
        r"\btangents?\s+([A-Z])([A-Z])\b",
        text,
        re.I,
    ):
        for g in m.groups():
            if g and len(g) == 1 and g.isalpha():
                labels.add(g.upper())
    return labels


def _figure_labels(q: Dict[str, Any]) -> Set[str]:
    labels: Set[str] = set()
    spec = q.get("figure_spec") or {}
    for el in spec.get("elements") or []:
        if isinstance(el, dict):
            lab = el.get("label") or el.get("from") or el.get("to")
            if isinstance(lab, str) and len(lab) == 1 and lab.isalpha():
                labels.add(lab.upper())
    for k in (spec.get("labels") or {}).keys():
        if len(k) == 1:
            labels.add(k.upper())
    return labels


def _is_conceptual_one_liner(stem: str) -> bool:
    low = stem.lower().strip()
    if len(stem.split()) > 20:
        return False
    return bool(
        re.match(r"^can\s+.+\?$", low)
        or re.match(r"^is\s+.+\?$", low)
        or "can a tangent" in low
    )


def _has_numeric_givens(stem: str) -> bool:
    return bool(re.search(r"\d+\s*(?:cm|m|°|degrees?)?|\d+°", stem, re.I))


def _angle_find_complete(stem: str) -> bool:
    """Find angle X requires named angle + at least one numeric angle or sufficient givens."""
    low = stem.lower()
    if not re.search(r"\bfind\s+(?:the\s+)?angle\b", low):
        return True
    if not re.search(r"angle\s+[A-Z]{2,4}\b", stem, re.I):
        return False
    if _has_numeric_givens(stem):
        return True
    if re.search(r"angle\s+[A-Z]{2,4}\s*=\s*\d", stem, re.I):
        return True
    if re.search(r"right angle|90\s*°", low):
        return True
    return False


def _has_clear_objective(stem: str) -> bool:
    low = stem.lower()
    return bool(
        re.search(
            r"\b(find|prove|show that|calculate|determine|hence|can\s|which|name)\b",
            low,
        )
    )


def _or_sections_balanced(stem: str) -> Tuple[bool, str]:
    if " or " not in stem.lower():
        return True, ""
    parts = re.split(r"\s+or\s+", stem, flags=re.I)
    if len(parts) != 2:
        return True, ""
    a, b = parts[0].lower(), parts[1].lower()
    a_find = "find" in a
    b_find = "find" in b
    a_prove = "prove" in a
    b_prove = "prove" in b
    if (a_find and b_prove) or (a_prove and b_find):
        return False, "or_mixed_archetype"
    if a_find and b_find and not (_has_numeric_givens(parts[0]) and _has_numeric_givens(parts[1])):
        if not (_has_numeric_givens(parts[0]) or _has_numeric_givens(parts[1])):
            return False, "or_missing_givens"
    return True, ""


def text_figure_independence_score(q: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Question should be solvable from stem text; figure is supportive only.
    """
    stem = (q.get("content") or "").strip()
    flags: List[str] = []
    score = 1.0
    if q.get("question_type") != "FigureBased":
        return score, flags

    stem_points = _extract_point_labels(stem)
    fig_points = _figure_labels(q)
    if stem_points and fig_points:
        missing_in_fig = stem_points - fig_points
        if len(missing_in_fig) > 2:
            flags.append("figure_not_supporting_text")
            score -= 0.12

    if len(stem.split()) < 10 and not _is_conceptual_one_liner(stem):
        flags.append("stem_requires_figure")
        score -= 0.15

    if re.search(r"\bin the figure\b|\bsee the diagram\b", stem, re.I):
        flags.append("figure_dependent_wording")
        score -= 0.2

    return max(0.0, score), flags


def validate_completeness(q: Dict[str, Any]) -> Dict[str, Any]:
    stem = (q.get("content") or "").strip()
    flags: List[str] = []
    score = 1.0

    if not stem:
        return {
            "completeness_score": 0.0,
            "completeness_flags": ["empty_stem"],
            "semantically_complete": False,
        }

    awkward = detect_awkward_idiom(stem)
    if awkward:
        flags.extend(awkward)
        penalty = 0.15 * len(awkward)
        if "awkward_perpendicular_wording" in awkward:
            penalty += 0.35
        if "tautological_perp_at_contact" in awkward:
            penalty += 0.45
        if "incomplete_angle_target" in awkward or "vague_angle_find" in awkward:
            penalty += 0.4
        score -= min(0.55, penalty)

    if not _has_clear_objective(stem):
        flags.append("no_clear_objective")
        score -= 0.35

    if not _angle_find_complete(stem):
        flags.append("angle_find_under_specified")
        score -= 0.4

    if is_common_external_tangent_stem(stem):
        if not stem_has_required_external_tangent_givens(stem):
            flags.append("common_external_tangent_missing_givens")
            score -= 0.55
        elif not stem_has_valid_external_tangent_givens(stem):
            flags.append("common_external_tangent_impossible_geometry")
            score -= 0.6

    if re.search(r"\bfind\b", stem, re.I) and not _has_numeric_givens(stem):
        if not _is_conceptual_one_liner(stem) and "prove" not in stem.lower():
            if "which" not in stem.lower():
                flags.append("find_without_numeric_givens")
                score -= 0.22

    n_words = len(stem.split())
    if n_words < 10 and not _is_conceptual_one_liner(stem):
        flags.append("over_compressed")
        score -= 0.25
    elif n_words < 14 and re.search(r"\bfind\b", stem, re.I) and not _has_numeric_givens(stem):
        flags.append("thin_find_stem")
        score -= 0.15

    or_ok, or_flag = _or_sections_balanced(stem)
    if not or_ok:
        flags.append(or_flag)
        score -= 0.12

    tf_score, tf_flags = text_figure_independence_score(q)
    flags.extend(tf_flags)
    score = min(score, tf_score)

    geo = validate_geometry_graph(stem, q)
    flags.extend(geo.get("geometry_flags") or [])
    score = min(score, geo.get("geometry_integrity_score", 1.0))
    if "prove_equality_missing_tangent_setup" in flags:
        score -= 0.15
    if "angle_center_mismatch:use_AOB_not_POQ" in flags:
        score -= 0.2

    stem_points = _extract_point_labels(stem)
    if stem_points and q.get("question_type") == "FigureBased":
        fig_pts = _figure_labels(q)
        orphan = stem_points - fig_pts
        common = {"O", "P", "Q", "T", "A", "B", "M", "R"}
        orphan = {p for p in orphan if p in common or len(stem_points) <= 6}
        if orphan and len(orphan) > 1:
            flags.append(f"points_not_in_figure:{','.join(sorted(orphan))}")
            score -= 0.1

    completeness = max(0.0, min(1.0, score))
    return {
        "completeness_score": round(completeness, 3),
        "completeness_flags": flags,
        "semantically_complete": completeness >= 0.58,
    }


def should_reject_incomplete(q: Dict[str, Any]) -> bool:
    if "completeness_score" not in q:
        q.update(validate_completeness(q))
    flags = q.get("completeness_flags") or []
    if "awkward_perpendicular_wording" in flags and not q.get("idiom_fixed"):
        return True
    if "tautological_perp_at_contact" in flags and not q.get("idiom_fixed"):
        return True
    if "angle_find_under_specified" in flags:
        return True
    if "prove_equality_missing_tangent_setup" in flags and not q.get("geometry_repaired"):
        return True
    if "angle_center_mismatch:use_AOB_not_POQ" in flags:
        return True
    if (
        "common_external_tangent_missing_givens" in flags
        or "common_external_tangent_impossible_geometry" in flags
    ) and not q.get("paper_repaired"):
        return True
    if not q.get("semantically_complete", True):
        return True
    return q.get("completeness_score", 1) < 0.52


def ensure_minimum_context(q: Dict[str, Any]) -> Dict[str, Any]:
    """Expand stem if graph validator would flag missing setup."""
    stem = (q.get("content") or "").strip()
    new_stem, changed = apply_minimum_context(stem, q)
    if changed:
        q["content"] = new_stem
        q["geometry_repaired"] = True
        q.update(validate_completeness(q))
    return q
