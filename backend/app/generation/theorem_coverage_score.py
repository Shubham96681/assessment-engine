"""
Theorem coverage scoring — measure and enforce pedagogical completeness before delivery.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.generation.theorem_coverage import IMPORTANCE_WEIGHTS

# Named multi-theorem reasoning patterns (dependency-aware coverage)
CHAPTER_THEOREM_COMBOS: Dict[str, List[Dict[str, Any]]] = {
    "circles": [
        {
            "id": "tangent_secant_power_chain",
            "requires": ["tangent_lengths_equal", "secant_tangent_power"],
            "label": "Tangent lengths + secant–tangent power",
        },
        {
            "id": "tangent_radius_angle_fusion",
            "requires": ["tangent_radius_perpendicular", "angle_in_alternate_segment"],
            "label": "Radius ⟂ tangent + alternate-segment angle",
        },
        {
            "id": "concentric_tangent_chain",
            "requires": ["concentric_chord", "tangent_radius_perpendicular"],
            "label": "Concentric chord + radius at contact",
        },
    ],
    "quadrilaterals": [
        {
            "id": "cyclic_parallelogram_fusion",
            "requires": ["cyclic_opposite_angles", "parallelogram_diagonal_bisect"],
            "label": "Cyclic quad + parallelogram diagonal property",
        },
        {
            "id": "midpoint_rhombus_chain",
            "requires": ["midpoint_theorem", "rhombus_diagonals"],
            "label": "Midpoint theorem + rhombus diagonals",
        },
    ],
    "quadratic": [
        {
            "id": "discriminant_then_roots",
            "requires": ["discriminant_nature", "factorisation_method"],
            "label": "Nature of roots then factorisation",
        },
        {
            "id": "parameter_equal_roots",
            "requires": ["equal_roots_parameter", "discriminant_nature"],
            "label": "Equal roots via k and discriminant",
        },
    ],
}

# Per-theorem stem detectors (beyond archetype id)
THEOREM_STEM_PATTERNS: Dict[str, List[str]] = {
    "cyclic_opposite_angles": [r"cyclic", r"opposite\s+angles.*supplementary", r"supplementary.*opposite"],
    "parallelogram_diagonal_bisect": [r"diagonal.*bisect", r"bisect.*diagonal", r"parallelogram.*diagonal"],
    "midpoint_theorem": [r"midpoint\s+theorem", r"parallel.*(?:side|base)", r"joining\s+midpoints"],
    "rhombus_diagonals": [r"rhombus", r"perpendicular\s+diagonals"],
    "parallelogram_opposite_sides": [r"opposite\s+sides.*equal", r"parallelogram.*opposite"],
    "trapezium_midsegment": [r"trapezium", r"trapezoid", r"mid.?segment"],
    "tangent_radius_perpendicular": [r"tangent.*perpendicular|radius.*perpendicular|perpendicular.*tangent"],
    "tangent_lengths_equal": [r"tangents?\s+.*equal|equal\s+tangents?", r"TP\s*=\s*TA"],
    "secant_tangent_power": [r"secant", r"tangent.*power|power\s+of\s+a\s+point|TG\s*=\s*"],
    "concentric_chord": [r"concentric", r"chord.*touches?\s+the\s+smaller"],
    "angle_in_alternate_segment": [r"alternate\s+segment", r"angle\s+between\s+tangent\s+and\s+chord"],
    "discriminant_nature": [r"discriminant", r"nature\s+of\s+(?:the\s+)?roots"],
    "equal_roots_parameter": [r"equal\s+roots|coincident\s+roots|two\s+equal\s+real\s+roots"],
    "factorisation_method": [r"factoris", r"by\s+factor"],
    "quadratic_formula": [r"quadratic\s+formula", r"\-b\s*±\s*√"],
    "area_word_problem": [r"area\s+is\s+\d+", r"breadth|width.*length", r"rectangular\s+field|grove|hall"],
    "pythagoras": [r"pythagoras|hypotenuse"],
    "similar_triangles": [r"similar\s+triangles|similarity"],
}

# Stem → cognitive operation (coverage-by-cognitive-type)
COGNITIVE_STEM_PATTERNS: Dict[str, List[str]] = {
    "proof": [r"\bprove\b", r"\bshow\s+that\b", r"\bhence\s+prove\b", r"\bdeduce\b"],
    "computation": [
        r"\bfind\b",
        r"\bcalculate\b",
        r"\bevaluate\b",
        r"\bsolve\b",
        r"\bdetermine\s+the\s+(?:value|length|angle)",
    ],
    "construction": [r"\bconstruct\b", r"\bdraw\b", r"\blocate\s+the\s+point\b"],
    "reverse_reasoning": [
        r"\bwhich\s+theorem\b",
        r"\bidentify\s+the\s+property\b",
        r"\bstate\s+the\s+theorem\b",
        r"\bname\s+the\b",
    ],
    "hots_fusion": [
        r"\bor\b.*\bprove\b",
        r"\bhence\b.*\bfind\b",
        r"\bif\s+.*\bthen\s+prove\b",
        r"\band\s+hence\b",
    ],
}


def detect_cognitive_type(stem: str, theorem: Optional[Dict[str, str]] = None) -> str:
    """Infer cognitive operation from stem; fall back to theorem default."""
    low = (stem or "").lower()
    for ctype in ("hots_fusion", "proof", "construction", "reverse_reasoning", "computation"):
        for pat in COGNITIVE_STEM_PATTERNS.get(ctype, []):
            if re.search(pat, low, re.I):
                return ctype
    if theorem:
        return theorem.get("cognitive_type", "computation")
    return "computation"


def theorem_weight(theorem: Dict[str, str]) -> float:
    imp = theorem.get("importance", "important")
    return float(
        theorem.get("weight") or IMPORTANCE_WEIGHTS.get(imp, 0.85)
    )


def missing_theorems_weighted(
    required_theorems: List[Dict[str, str]],
    covered: Set[str],
) -> List[str]:
    """Missing theorems sorted by weight (required first)."""
    missing = [
        t for t in required_theorems if t.get("id") and t["id"] not in covered
    ]
    return sorted(missing, key=lambda t: -theorem_weight(t))


def detect_theorems_in_stem(
    stem: str,
    required_theorems: List[Dict[str, str]],
) -> Set[str]:
    """Return theorem ids detected in a question stem."""
    low = (stem or "").lower()
    found: Set[str] = set()
    for t in required_theorems:
        tid = t.get("id", "")
        if not tid:
            continue
        for pat in THEOREM_STEM_PATTERNS.get(tid, []):
            if re.search(pat, low, re.I):
                found.add(tid)
                break
        # Fallback: label keywords
        if tid not in found and t.get("label"):
            words = [w for w in t["label"].lower().split() if len(w) > 5][:3]
            if words and sum(1 for w in words if w in low) >= 2:
                found.add(tid)
    return found


def detect_combos_in_paper(
    questions: List[Dict[str, Any]],
    chapter: str,
    *,
    required_theorems: Optional[List[Dict[str, str]]] = None,
) -> Tuple[List[str], List[str]]:
    """
    Dependency-aware: which named theorem combinations appear (same stem or across paper).
    Returns (combos_satisfied, combos_partial).
    """
    combos = CHAPTER_THEOREM_COMBOS.get(chapter, [])
    if not combos or not questions:
        return [], []

    paper_theorems: Set[str] = set()
    per_stem: List[Set[str]] = []
    for q in questions:
        stem = q.get("content") or ""
        detected = detect_theorems_in_stem(stem, required_theorems or [])
        q["detected_theorems"] = list(detected)
        per_stem.append(detected)
        paper_theorems |= detected

    satisfied: List[str] = []
    partial: List[str] = []
    for combo in combos:
        req = set(combo.get("requires") or [])
        if not req:
            continue
        if req <= paper_theorems:
            satisfied.append(combo["id"])
        elif req & paper_theorems:
            partial.append(combo["id"])
        # Same-question fusion
        for detected in per_stem:
            if req <= detected:
                if combo["id"] not in satisfied:
                    satisfied.append(combo["id"])
                break

    return satisfied, partial


def score_theorem_coverage(
    questions: List[Dict[str, Any]],
    required_theorems: List[Dict[str, str]],
    *,
    chapter: str = "generic",
) -> Dict[str, Any]:
    """
    coverage_score = |covered planned theorems| / |planned|
    combo_score = |satisfied combos| / |available combos for chapter|
    """
    planned_ids = [t["id"] for t in required_theorems if t.get("id")]
    if not planned_ids:
        return {
            "coverage_score": 1.0,
            "weighted_coverage_score": 1.0,
            "required_theorem_ratio": 1.0,
            "cognitive_diversity_score": 1.0,
            "combo_score": 1.0,
            "planned_count": 0,
            "covered_count": 0,
            "covered_theorems": [],
            "missing_theorems": [],
            "missing_theorems_weighted": [],
            "theorem_combos_satisfied": [],
            "theorem_combos_partial": [],
            "per_question": [],
            "meets_minimum": True,
        }

    covered: Set[str] = set()
    per_q: List[Dict[str, Any]] = []
    cognitive_seen: Set[str] = set()
    theorem_by_id = {t["id"]: t for t in required_theorems if t.get("id")}

    for q in questions:
        stem = q.get("content") or ""
        detected = detect_theorems_in_stem(stem, required_theorems)
        covered |= detected
        primary_th = next(iter(detected), None)
        th_meta = theorem_by_id.get(primary_th or "", {})
        cog = detect_cognitive_type(stem, th_meta)
        cognitive_seen.add(cog)
        q["detected_cognitive_type"] = cog
        per_q.append(
            {
                "order_index": q.get("order_index"),
                "detected": sorted(detected),
                "planned_theorem": q.get("planned_theorem_id"),
                "cognitive_type": cog,
            }
        )

    missing_ids = [tid for tid in planned_ids if tid not in covered]
    missing_weighted = [
        t["id"] for t in missing_theorems_weighted(required_theorems, covered)
    ]
    coverage_score = round(len(covered & set(planned_ids)) / len(planned_ids), 3)

    total_w = sum(theorem_weight(t) for t in required_theorems) or 1.0
    covered_w = sum(
        theorem_weight(t) for t in required_theorems if t.get("id") in covered
    )
    weighted_coverage_score = round(covered_w / total_w, 3)

    # Required-tier must be mostly satisfied
    required_ids = [
        t["id"]
        for t in required_theorems
        if t.get("importance") == "required" and t.get("id")
    ]
    required_covered = sum(1 for rid in required_ids if rid in covered)
    required_ratio = (
        round(required_covered / len(required_ids), 3) if required_ids else 1.0
    )

    planned_cognitive = {
        t.get("cognitive_type", "computation")
        for t in required_theorems
        if t.get("cognitive_type")
    }
    cognitive_diversity_score = (
        round(len(cognitive_seen & planned_cognitive) / len(planned_cognitive), 3)
        if planned_cognitive
        else 1.0
    )

    combos_avail = CHAPTER_THEOREM_COMBOS.get(chapter, [])
    satisfied, partial = detect_combos_in_paper(questions, chapter, required_theorems=required_theorems)
    combo_score = (
        round(len(satisfied) / len(combos_avail), 3) if combos_avail else 1.0
    )

    min_cov = settings.MINIMUM_THEOREM_COVERAGE_SCORE
    min_w = settings.MINIMUM_WEIGHTED_COVERAGE_SCORE
    min_cog = settings.MINIMUM_COGNITIVE_DIVERSITY_SCORE
    meets = (
        weighted_coverage_score >= min_w
        and required_ratio >= 0.6
        and cognitive_diversity_score >= min_cog
    ) or coverage_score >= min_cov

    return {
        "coverage_score": coverage_score,
        "weighted_coverage_score": weighted_coverage_score,
        "required_theorem_ratio": required_ratio,
        "cognitive_diversity_score": cognitive_diversity_score,
        "cognitive_types_seen": sorted(cognitive_seen),
        "cognitive_types_planned": sorted(planned_cognitive),
        "combo_score": combo_score,
        "planned_count": len(planned_ids),
        "covered_count": len(covered & set(planned_ids)),
        "covered_theorems": sorted(covered & set(planned_ids)),
        "missing_theorems": missing_ids,
        "missing_theorems_weighted": missing_weighted,
        "theorem_combos_satisfied": satisfied,
        "theorem_combos_partial": partial,
        "per_question": per_q,
        "meets_minimum": meets,
        "minimum_required": min_cov,
        "minimum_weighted": min_w,
    }


def boost_coverage_from_pool(
    final: List[Dict[str, Any]],
    pool: List[Dict[str, Any]],
    required_theorems: List[Dict[str, str]],
    missing: List[str],
    *,
    target_count: int,
) -> List[Dict[str, Any]]:
    """
    Swap in pool questions that cover missing theorems (graceful enrichment).
    """
    if not missing or not pool:
        return final

    result = list(final)
    used_hashes = {q.get("content_hash") for q in result}
    # Boost high-weight missing theorems first
    ordered_missing = missing
    if required_theorems:
        covered_so_far: Set[str] = set()
        for q in result:
            covered_so_far |= detect_theorems_in_stem(
                q.get("content") or "", required_theorems
            )
        ordered_missing = [
            t["id"]
            for t in missing_theorems_weighted(required_theorems, covered_so_far)
        ]

    for tid in ordered_missing:
        for candidate in sorted(
            pool,
            key=lambda q: q.get("topic_alignment_score", q.get("quality_score", 0)),
            reverse=True,
        ):
            if candidate.get("content_hash") in used_hashes:
                continue
            stem = candidate.get("content") or ""
            if tid in detect_theorems_in_stem(stem, required_theorems):
                # Replace weakest slot that does not cover this theorem
                replace_idx = 0
                worst_score = 999.0
                for i, q in enumerate(result):
                    det = detect_theorems_in_stem(q.get("content") or "", required_theorems)
                    if tid in det:
                        continue
                    sc = q.get("topic_alignment_score", q.get("quality_score", 0))
                    if sc < worst_score:
                        worst_score = sc
                        replace_idx = i
                result[replace_idx] = candidate
                used_hashes.add(candidate.get("content_hash"))
                break

    from app.generation.theorem_coverage import apply_organic_noise_to_slots

    return apply_organic_noise_to_slots(result[:target_count])


def enforce_coverage_before_delivery(
    final: List[Dict[str, Any]],
    pool: List[Dict[str, Any]],
    required_theorems: List[Dict[str, str]],
    *,
    chapter: str,
    target_count: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Score coverage; optionally boost from pool; return final + report."""
    report = score_theorem_coverage(final, required_theorems, chapter=chapter)
    if (
        settings.THEOREM_COVERAGE_ENFORCE
        and required_theorems
        and not report["meets_minimum"]
        and pool
    ):
        boosted = boost_coverage_from_pool(
            final,
            pool,
            required_theorems,
            report["missing_theorems"],
            target_count=target_count,
        )
        report_after = score_theorem_coverage(
            boosted, required_theorems, chapter=chapter
        )
        report_after["boosted"] = True
        report_after["pre_boost_score"] = report["coverage_score"]
        return boosted, report_after
    return final, report
