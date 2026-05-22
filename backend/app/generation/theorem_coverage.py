"""
Curriculum-aware theorem coverage — TopicAgent plans required theorems; blueprint spreads them.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# importance: required | important | optional | bonus
# weight: contribution to weighted coverage (required theorems must be covered)
# cognitive_type: proof | computation | construction | reverse_reasoning | hots_fusion
IMPORTANCE_WEIGHTS = {
    "required": 1.0,
    "important": 0.85,
    "optional": 0.5,
    "bonus": 0.25,
}

THEOREM_META: Dict[str, Dict[str, Any]] = {
    "cyclic_opposite_angles": {
        "difficulty": "medium",
        "importance": "important",
        "weight": 0.85,
        "cognitive_type": "proof",
        "combines_with": ["parallelogram_diagonal_bisect"],
    },
    "parallelogram_diagonal_bisect": {
        "difficulty": "medium",
        "importance": "required",
        "weight": 1.0,
        "cognitive_type": "proof",
        "combines_with": ["cyclic_opposite_angles"],
    },
    "midpoint_theorem": {
        "difficulty": "medium",
        "importance": "important",
        "weight": 0.85,
        "cognitive_type": "proof",
        "combines_with": ["parallelogram_opposite_sides"],
    },
    "rhombus_diagonals": {
        "difficulty": "easy",
        "importance": "optional",
        "weight": 0.5,
        "cognitive_type": "proof",
        "combines_with": ["midpoint_theorem"],
    },
    "parallelogram_opposite_sides": {
        "difficulty": "easy",
        "importance": "optional",
        "weight": 0.5,
        "cognitive_type": "proof",
        "combines_with": [],
    },
    "trapezium_midsegment": {
        "difficulty": "medium",
        "importance": "bonus",
        "weight": 0.25,
        "cognitive_type": "computation",
        "combines_with": [],
    },
    "tangent_radius_perpendicular": {
        "difficulty": "easy",
        "importance": "optional",
        "weight": 0.5,
        "cognitive_type": "proof",
        "combines_with": ["tangent_lengths_equal"],
    },
    "tangent_lengths_equal": {
        "difficulty": "easy",
        "importance": "important",
        "weight": 0.85,
        "cognitive_type": "computation",
        "combines_with": ["secant_tangent_power", "angle_in_alternate_segment"],
    },
    "secant_tangent_power": {
        "difficulty": "hard",
        "importance": "required",
        "weight": 1.0,
        "cognitive_type": "hots_fusion",
        "combines_with": ["tangent_lengths_equal"],
    },
    "concentric_chord": {
        "difficulty": "hard",
        "importance": "important",
        "weight": 0.85,
        "cognitive_type": "computation",
        "combines_with": ["tangent_radius_perpendicular"],
    },
    "angle_in_alternate_segment": {
        "difficulty": "medium",
        "importance": "important",
        "weight": 0.85,
        "cognitive_type": "computation",
        "combines_with": ["tangent_radius_perpendicular"],
    },
    "discriminant_nature": {
        "difficulty": "easy",
        "importance": "required",
        "weight": 1.0,
        "cognitive_type": "computation",
        "combines_with": ["factorisation_method", "equal_roots_parameter"],
    },
    "equal_roots_parameter": {
        "difficulty": "medium",
        "importance": "important",
        "weight": 0.85,
        "cognitive_type": "computation",
        "combines_with": ["discriminant_nature"],
    },
    "factorisation_method": {
        "difficulty": "easy",
        "importance": "required",
        "weight": 1.0,
        "cognitive_type": "computation",
        "combines_with": ["discriminant_nature"],
    },
    "quadratic_formula": {
        "difficulty": "medium",
        "importance": "important",
        "weight": 0.85,
        "cognitive_type": "computation",
        "combines_with": ["discriminant_nature"],
    },
    "area_word_problem": {
        "difficulty": "hard",
        "importance": "required",
        "weight": 1.0,
        "cognitive_type": "hots_fusion",
        "combines_with": ["factorisation_method"],
    },
    "pythagoras": {
        "difficulty": "easy",
        "importance": "required",
        "weight": 1.0,
        "cognitive_type": "computation",
        "combines_with": ["similar_triangles"],
    },
    "similar_triangles": {
        "difficulty": "hard",
        "importance": "important",
        "weight": 0.85,
        "cognitive_type": "hots_fusion",
        "combines_with": ["pythagoras"],
    },
}

COGNITIVE_TYPES = (
    "proof",
    "computation",
    "construction",
    "reverse_reasoning",
    "hots_fusion",
)

_DIFF_TO_BAND = {"easy": "L1", "medium": "L2", "hard": "L4", "hots": "L5"}

# theorem_id → archetype_id in rd_archetypes
CHAPTER_THEOREM_CATALOG: Dict[str, List[Dict[str, str]]] = {
    "quadrilaterals": [
        {
            "id": "cyclic_opposite_angles",
            "label": "Opposite angles of a cyclic quadrilateral are supplementary",
            "archetype_id": "cyclic_angle",
        },
        {
            "id": "parallelogram_diagonal_bisect",
            "label": "Diagonals of a parallelogram bisect each other",
            "archetype_id": "diagonal_bisect",
        },
        {
            "id": "midpoint_theorem",
            "label": "Midpoint theorem / line parallel to one side",
            "archetype_id": "midpoint_theorem",
        },
        {
            "id": "rhombus_diagonals",
            "label": "Diagonals of a rhombus are perpendicular",
            "archetype_id": "rhombus_diagonal",
        },
        {
            "id": "parallelogram_opposite_sides",
            "label": "Opposite sides of a parallelogram are equal",
            "archetype_id": "parallelogram_opposite",
        },
        {
            "id": "trapezium_midsegment",
            "label": "Trapezium mid-segment parallel to parallel sides",
            "archetype_id": "trapezium_parallel",
        },
    ],
    "circles": [
        {
            "id": "tangent_radius_perpendicular",
            "label": "Tangent perpendicular to radius at point of contact",
            "archetype_id": "direct_theorem",
        },
        {
            "id": "tangent_lengths_equal",
            "label": "Tangents from external point are equal",
            "archetype_id": "length_find",
        },
        {
            "id": "secant_tangent_power",
            "label": "Secant–tangent power relation",
            "archetype_id": "secant_tangent",
        },
        {
            "id": "concentric_chord",
            "label": "Chord of larger circle tangent to inner circle",
            "archetype_id": "concentric",
        },
        {
            "id": "angle_in_alternate_segment",
            "label": "Angle between tangent and chord",
            "archetype_id": "angle_theorem",
        },
    ],
    "quadratic": [
        {
            "id": "discriminant_nature",
            "label": "Nature of roots via discriminant",
            "archetype_id": "nature_of_roots",
        },
        {
            "id": "equal_roots_parameter",
            "label": "Parameter for equal real roots",
            "archetype_id": "equal_roots_k",
        },
        {
            "id": "factorisation_method",
            "label": "Roots by factorisation",
            "archetype_id": "factorisation_roots",
        },
        {
            "id": "quadratic_formula",
            "label": "Roots using quadratic formula",
            "archetype_id": "formula_roots",
        },
        {
            "id": "area_word_problem",
            "label": "Area / dimension word problem → quadratic",
            "archetype_id": "word_problem_area",
        },
    ],
    "triangles": [
        {
            "id": "pythagoras",
            "label": "Pythagoras theorem applications",
            "archetype_id": "numerical_find",
        },
        {
            "id": "similar_triangles",
            "label": "Similar triangles ratio",
            "archetype_id": "proof_derive",
        },
    ],
}

_THEOREM_DETECT: List[tuple[str, str, str]] = [
    (r"cyclic|opposite\s+angles.*supplementary", "quadrilaterals", "cyclic_opposite_angles"),
    (r"diagonal.*bisect|bisect.*diagonal", "quadrilaterals", "parallelogram_diagonal_bisect"),
    (r"midpoint\s+theorem|parallel.*side", "quadrilaterals", "midpoint_theorem"),
    (r"rhombus.*diagonal|perpendicular\s+diagonal", "quadrilaterals", "rhombus_diagonals"),
    (r"tangent.*radius|radius.*tangent|perpendicular.*tangent", "circles", "tangent_radius_perpendicular"),
    (r"secant|tangent.*power|tg\s*=\s*", "circles", "secant_tangent_power"),
    (r"discriminant|nature\s+of\s+roots", "quadratic", "discriminant_nature"),
    (r"equal\s+roots|coincident\s+roots", "quadratic", "equal_roots_parameter"),
    (r"factoris", "quadratic", "factorisation_method"),
    (r"quadratic\s+formula", "quadratic", "quadratic_formula"),
    (r"area.*breadth|length.*breadth|word\s+problem", "quadratic", "area_word_problem"),
]


def catalog_for_chapter(chapter: str) -> List[Dict[str, str]]:
    return list(CHAPTER_THEOREM_CATALOG.get(chapter, CHAPTER_THEOREM_CATALOG.get("generic", [])))


def infer_required_theorems(
    chapter: str,
    blob: str = "",
    subtopics: Optional[List[str]] = None,
    *,
    max_theorems: int = 6,
) -> List[Dict[str, str]]:
    """
    Build required_theorems list for TopicAgent / blueprint.
    Merges chapter catalog defaults with PDF-detected signals.
    """
    catalog = {t["id"]: t for t in catalog_for_chapter(chapter)}
    if not catalog:
        return []

    found: List[str] = []
    text = (blob or "") + " " + " ".join(subtopics or [])
    low = text.lower()
    for pattern, ch, tid in _THEOREM_DETECT:
        if ch != chapter and chapter != "generic":
            continue
        if re.search(pattern, low, re.I) and tid not in found:
            found.append(tid)

    ordered: List[Dict[str, str]] = []
    for tid in found:
        if tid in catalog:
            ordered.append(catalog[tid])

    for t in catalog_for_chapter(chapter):
        if t["id"] not in {x["id"] for x in ordered}:
            ordered.append(t)

    return enrich_required_theorems(ordered[:max_theorems])


def enrich_required_theorems(theorems: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Attach difficulty, importance, weight, cognitive_type for synthesis."""
    out: List[Dict[str, str]] = []
    for t in theorems:
        tid = t.get("id", "")
        meta = THEOREM_META.get(tid, {})
        enriched = dict(t)
        imp = meta.get("importance", "important")
        enriched.setdefault("difficulty", meta.get("difficulty", "medium"))
        enriched.setdefault("importance", imp)
        enriched.setdefault(
            "weight", meta.get("weight", IMPORTANCE_WEIGHTS.get(imp, 0.85))
        )
        enriched.setdefault("cognitive_type", meta.get("cognitive_type", "computation"))
        enriched.setdefault("combines_with", meta.get("combines_with", []))
        out.append(enriched)
    # Required/important first; cap bonus theorems for human unevenness
    rank = {"required": 0, "important": 1, "optional": 2, "bonus": 3}
    out.sort(key=lambda x: (rank.get(x.get("importance", "important"), 2), -x.get("weight", 0)))
    return out


def apply_organic_noise_to_slots(
    items: List[Any],
    *,
    noise: float | None = None,
    seed: int | None = None,
) -> List[Any]:
    """
    Slight shuffle so papers are not robotically balanced (controlled_organic_noise).
    """
    import random

    from app.core.config import settings

    p = noise if noise is not None else settings.CONTROLLED_ORGANIC_NOISE
    if p <= 0 or len(items) < 3:
        return items
    rng = random.Random(seed)
    out = list(items)
    for i in range(len(out) - 1):
        if rng.random() < p:
            j = min(i + rng.randint(1, 2), len(out) - 1)
            out[i], out[j] = out[j], out[i]
    return out


def difficulty_to_band(difficulty: str, ui_difficulty: str = "medium") -> str:
    d = (difficulty or "medium").lower()
    ui = (ui_difficulty or "medium").lower()
    if ui in ("hard", "difficult") and d in ("hard", "hots"):
        return "L5" if d == "hots" else "L4"
    return _DIFF_TO_BAND.get(d, "L2")


def get_theorem_slot_bands(
    question_count: int,
    required_theorems: List[Dict[str, str]],
    *,
    ui_difficulty: str = "medium",
    fallback_bands: Optional[List[str]] = None,
) -> List[str]:
    """
    Map each paper slot to L-band from planned theorem difficulty (easy → hard spread).
    """
    if not required_theorems:
        return fallback_bands or []

    fallback_bands = fallback_bands or []
    # Sort theorems easy → hard, round-robin across slots
    ranked = sorted(
        required_theorems,
        key=lambda t: {"easy": 0, "medium": 1, "hard": 2, "hots": 3}.get(
            (t.get("difficulty") or "medium").lower(), 1
        ),
    )
    bands: List[str] = []
    for i in range(question_count):
        th = ranked[i % len(ranked)]
        bands.append(difficulty_to_band(th.get("difficulty", "medium"), ui_difficulty))
    # Last slot HOTS when hard UI and enough questions
    if ui_difficulty in ("hard", "difficult") and question_count >= 5:
        bands[-1] = "L5"
    return apply_organic_noise_to_slots(bands)


def build_theorem_coverage_prompt(
    required_theorems: List[Dict[str, str]],
    question_count: int,
) -> str:
    if not required_theorems:
        return ""
    lines = [
        "THEOREM COVERAGE PLAN (curriculum-aware — spread across paper):",
        f"- Chapter theorems to cover (max {max(1, int(question_count * 0.4))} repeats per theorem):",
    ]
    for t in required_theorems:
        diff = t.get("difficulty", "medium")
        imp = t.get("importance", "important")
        cog = t.get("cognitive_type", "computation")
        lines.append(
            f"  • {t.get('id')} [{imp}, {diff}, {cog}]: {t.get('label', '')}"
        )
    lines.append(
        "- Assign slots so distinct theorems appear before repeating the same archetype."
    )
    lines.append(
        "- Match slot difficulty to theorem tier (easy→L1/L2, hard→L4/L5)."
    )
    lines.append(
        "- Cognitive mix: spread proof, computation, and HOTS fusion — not all same type."
    )
    lines.append(
        "- Slight uneven spacing is OK (human textbook rhythm); do not force perfect balance."
    )
    return "\n".join(lines) + "\n"


def pick_archetypes_with_theorem_coverage(
    n: int,
    chapter: str,
    required_theorems: List[Dict[str, str]],
    *,
    ui_difficulty: str = "medium",
    seed: int | None = None,
) -> List[Dict[str, str]]:
    """Round-robin archetypes from required theorems, then fill from weighted pool."""
    import random

    from app.generation.rd_archetypes import ARCHETYPE_BY_ID, pick_weighted_archetypes

    if not required_theorems:
        return pick_weighted_archetypes(n, chapter, seed=seed, ui_difficulty=ui_difficulty)

    rng = random.Random(seed)
    theorem_arches = [
        ARCHETYPE_BY_ID[t["archetype_id"]]
        for t in required_theorems
        if t.get("archetype_id") in ARCHETYPE_BY_ID
    ]
    if not theorem_arches:
        return pick_weighted_archetypes(n, chapter, seed=seed, ui_difficulty=ui_difficulty)

    chosen: List[Dict[str, str]] = []
    idx = 0
    while len(chosen) < n:
        th = required_theorems[idx % len(required_theorems)]
        arch = ARCHETYPE_BY_ID.get(th.get("archetype_id", ""))
        if arch:
            entry = dict(arch)
            entry["theorem_id"] = th["id"]
            entry["theorem_difficulty"] = th.get("difficulty", "medium")
            chosen.append(entry)
        idx += 1
    if len(chosen) < n:
        chosen.extend(
            pick_weighted_archetypes(
                n - len(chosen), chapter, seed=rng.randint(0, 99999), ui_difficulty=ui_difficulty
            )
        )
    from app.generation.chapter_prompt_isolation import filter_archetypes_to_chapter

    chosen = filter_archetypes_to_chapter(chosen, chapter)
    while len(chosen) < n:
        chosen.extend(
            filter_archetypes_to_chapter(
                pick_weighted_archetypes(
                    n - len(chosen), chapter, seed=rng.randint(0, 99999), ui_difficulty=ui_difficulty
                ),
                chapter,
            )
        )
    chosen = apply_organic_noise_to_slots(chosen, seed=seed)
    return chosen[:n]
