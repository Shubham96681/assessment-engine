"""
RD Sharma / RS Aggarwal — archetypes, chapter fingerprints, human sequencing, blueprint.
"""
from __future__ import annotations

import random
from typing import List, Dict, Any, Optional

from app.generation.textbook_constants import (
    TEXTBOOK_DIFFICULTY_MIX_5,
    TEXTBOOK_DIFFICULTY_MIX_8,
    HARD_DIFFICULTY_MIX_5,
    HARD_DIFFICULTY_MIX_8,
)
from app.generation.chapter_prompt_isolation import (
    build_chapter_hard_prompt_stack,
    filter_archetypes_to_chapter,
    figure_complexity_for_chapter,
    figure_type_hint_for_chapter,
    real_difficulty_mix_note,
    scan_text_for_chapter_contamination,
    sequence_slots_for_chapter,
)
from app.generation.reasoning_signature import pick_diverse_archetype_ids
from app.generation.author_styles import AuthorStyle, RD_SHARMA, author_style_prompt_block
from app.generation.author_imperfections import (
    get_chapter_imperfection_profile,
    get_imperfection_profile,
    build_exercise_memory_plan,
    imperfection_prompt_block,
)

# Circles-only templates (used when chapter fingerprint = circles)
CIRCLE_ARCHETYPES: List[Dict[str, str]] = [
    {
        "id": "length_find",
        "name": "Tangent length",
        "stem_hint": "Numeric givens only. Find length. Never name Pythagoras.",
        "example": "PQ is a tangent at P to a circle with centre O. OP = 5 cm, OQ = 12 cm. Find PQ.",
    },
    {
        "id": "angle_theorem",
        "name": "Angle between tangents",
        "stem_hint": "Angle ATB or AOB — link tangents and centre.",
        "example": "Tangents TA, TB from T. If angle ATB = 60°, find angle AOB.",
    },
    {
        "id": "hidden_theorem",
        "name": "Hidden theorem",
        "stem_hint": "Trap invisible. Givens + Find only.",
        "example": "PA, PB tangents from P. OA = 5 cm, OP = 13 cm. Find AP.",
    },
    {
        "id": "concentric",
        "name": "Concentric circles",
        "stem_hint": "Two radii; chord of larger touching smaller.",
        "example": "Concentric circles, radii 7 cm and 4 cm. Find chord of larger touching smaller.",
    },
    {
        "id": "secant_tangent",
        "name": "Secant + tangent",
        "stem_hint": "Name secant vs tangent — one line possible.",
        "example": "Line cuts circle at C, D; another touches at E only. Which is secant?",
    },
    {
        "id": "converse_identify",
        "name": "Pure conceptual",
        "stem_hint": "One-line allowed: Can a tangent…? Justify.",
        "example": "Can a tangent be drawn through a point inside the circle?",
    },
    {
        "id": "direct_theorem",
        "name": "Proof-only",
        "stem_hint": "Prove / Show that — low frequency.",
        "example": "Prove that tangents from an external point are equal.",
    },
    {
        "id": "chord_tangent",
        "name": "Chord–tangent",
        "stem_hint": "Chord + tangent in one item.",
        "example": "Chord AB, tangent at T. OM ⟂ AB, radius 7 cm. Find AM.",
    },
    {
        "id": "common_tangent",
        "name": "Common tangents",
        "stem_hint": "Two circles; external tangent length.",
        "example": "Circles centres O, O', radii 5 cm, 3 cm. Find common external tangent length.",
    },
    {
        "id": "hots_mixed",
        "name": "HOTS mixed",
        "stem_hint": "Prove then Hence find; OR — uneven marks.",
        "example": "Prove TA = TB. Hence find TA if OT = 13 cm, radius = 5 cm.",
    },
    {
        "id": "tangent_similarity",
        "name": "Tangent + similarity",
        "stem_hint": "Hidden similar triangles; no theorem names in stem.",
        "example": "Tangents TP, TQ from T. A secant through T meets the circle at R, S. Prove TR.TS = TP^2.",
    },
    {
        "id": "cyclic_angle",
        "name": "Cyclic / angle chase",
        "stem_hint": "Quadrilateral OATB or cyclic hints; multi-angle chase.",
        "example": "Tangents TA, TB. If angle ATB = 50°, find angle AOB and angle ABT.",
    },
]

# Parallelogram / quadrilateral chapter (NOT circles)
QUADRILATERAL_ARCHETYPES: List[Dict[str, str]] = [
    {
        "id": "parallelogram_opposite",
        "name": "Opposite sides / angles",
        "stem_hint": "Prove or find using opposite sides equal, opposite angles equal.",
        "example": "In parallelogram ABCD, if angle A = 72°, find angle C and angle B.",
    },
    {
        "id": "diagonal_bisect",
        "name": "Diagonals bisect",
        "stem_hint": "Diagonals intersect at O; use AO = OC, BO = OD.",
        "example": "Diagonals AC and BD of parallelogram PQRS meet at O. If AO = 7 cm, find AC.",
    },
    {
        "id": "midpoint_theorem",
        "name": "Midpoint / mid-segment",
        "stem_hint": "Midpoint joins sides; parallel to third side, half length.",
        "example": "In triangle ABC, D and E are midpoints of AB and AC. If BC = 14 cm, find DE.",
    },
    {
        "id": "rhombus_diagonal",
        "name": "Rhombus diagonals",
        "stem_hint": "Rhombus: diagonals perpendicular, bisect vertex angles.",
        "example": "Rhombus ABCD has diagonals AC = 16 cm, BD = 12 cm. Find side AB.",
    },
    {
        "id": "trapezium_parallel",
        "name": "Trapezium",
        "stem_hint": "One pair parallel; find unknown side or angle.",
        "example": "Trapezium ABCD has AB parallel DC, AB = 8 cm, DC = 14 cm, height 6 cm. Find area.",
    },
    {
        "id": "quad_proof",
        "name": "Prove parallelogram",
        "stem_hint": "Show quadrilateral is parallelogram from given conditions.",
        "example": "In quadrilateral ABCD, AB = CD and AB is parallel to CD. Prove ABCD is a parallelogram.",
    },
    {
        "id": "area_quad",
        "name": "Area",
        "stem_hint": "Area via base × height or diagonal formula.",
        "example": "Parallelogram ABCD has base AB = 12 cm and perpendicular distance 7 cm. Find area.",
    },
    {
        "id": "hots_quad",
        "name": "HOTS quadrilateral",
        "stem_hint": "OR: prove property then Hence find length/angle.",
        "example": "Prove diagonals of rectangle are equal. Hence find diagonal if sides are 9 cm and 40 cm.",
    },
]

QUADRATIC_ARCHETYPES: List[Dict[str, str]] = [
    {
        "id": "nature_of_roots",
        "name": "Nature of roots",
        "requires_figure_reasoning": False,
        "stem_hint": "Discriminant; real / equal / no real roots.",
        "example": "Find the nature of roots of 2x² − 5x + 3 = 0.",
    },
    {
        "id": "equal_roots_k",
        "name": "Parameter k",
        "requires_figure_reasoning": True,
        "stem_hint": "Find k for equal roots; table of coefficients ok.",
        "example": "Find k if 3x² + kx + 12 = 0 has equal roots.",
    },
    {
        "id": "word_problem_area",
        "name": "Area word problem",
        "requires_figure_reasoning": True,
        "stem_hint": "Rectangle / grove; form quadratic from area.",
        "example": "Length is twice breadth; area 800 m². Find sides.",
    },
    {
        "id": "factorisation_roots",
        "name": "Factorisation",
        "requires_figure_reasoning": False,
        "stem_hint": "Find roots by factorisation.",
        "example": "Solve x² − 7x + 10 = 0 by factorisation.",
    },
    {
        "id": "formula_roots",
        "name": "Quadratic formula",
        "requires_figure_reasoning": False,
        "stem_hint": "Use formula when factorisation is messy.",
        "example": "Solve 3x² − 4x + 2 = 0 and comment on nature of roots.",
    },
    {
        "id": "hots_quad",
        "name": "HOTS quadratic",
        "requires_figure_reasoning": True,
        "stem_hint": "OR: word problem or sum of squares of integers.",
        "example": "OR solve area problem OR consecutive integers with sum of squares 365.",
    },
]

GENERIC_ARCHETYPES: List[Dict[str, str]] = [
    {
        "id": "concept_apply",
        "name": "Concept application",
        "stem_hint": "Apply one definition or law from the chapter.",
        "example": "Using the relation from the chapter, find the unknown.",
    },
    {
        "id": "numerical_find",
        "name": "Numerical find",
        "stem_hint": "Givens + find; multi-step.",
        "example": "Given values from the text, calculate the required quantity.",
    },
    {
        "id": "proof_derive",
        "name": "Prove / show",
        "stem_hint": "Prove or show that — brief stem, structured answer.",
        "example": "Show that the expression simplifies as stated in the chapter.",
    },
    {
        "id": "word_problem",
        "name": "Word problem",
        "stem_hint": "Real-life setup from chapter style.",
        "example": "A problem modeled like the examples in the chapter.",
    },
    {
        "id": "multi_step",
        "name": "Multi-step chain",
        "stem_hint": "Two ideas from CONTEXT combined.",
        "example": "First establish a relation, hence find the value.",
    },
    {
        "id": "hots_fusion",
        "name": "HOTS fusion",
        "stem_hint": "OR or (i)(ii); uneven marks.",
        "example": "Part (i) establish result; part (ii) Hence find numerical value.",
    },
]

ARCHETYPES: List[Dict[str, str]] = CIRCLE_ARCHETYPES

# Hard UI: bias away from one-step drills
CHAPTER_PATTERNS_HARD: Dict[str, List[tuple[str, float]]] = {
    "quadratic": [
        ("word_problem_area", 0.22),
        ("nature_of_roots", 0.20),
        ("equal_roots_k", 0.18),
        ("hots_quad", 0.16),
        ("factorisation_roots", 0.12),
        ("formula_roots", 0.12),
    ],
    "generic": [
        ("numerical_find", 0.22),
        ("concept_apply", 0.20),
        ("word_problem", 0.18),
        ("multi_step", 0.16),
        ("proof_derive", 0.12),
        ("hots_fusion", 0.12),
    ],
    "quadrilaterals": [
        ("diagonal_bisect", 0.20),
        ("parallelogram_opposite", 0.18),
        ("midpoint_theorem", 0.16),
        ("hots_quad", 0.14),
        ("rhombus_diagonal", 0.12),
        ("area_quad", 0.10),
        ("quad_proof", 0.06),
        ("trapezium_parallel", 0.04),
    ],
    "circles": [
        ("hidden_theorem", 0.18),
        ("concentric", 0.17),
        ("hots_mixed", 0.16),
        ("chord_tangent", 0.14),
        ("cyclic_angle", 0.12),
        ("tangent_similarity", 0.10),
        ("length_find", 0.07),
        ("common_tangent", 0.05),
        ("angle_theorem", 0.04),
        ("direct_theorem", 0.03),
        ("secant_tangent", 0.02),
        ("converse_identify", 0.02),
    ],
}

# Chapter statistical fingerprints (weight = relative frequency)
CHAPTER_PATTERNS: Dict[str, List[tuple[str, float]]] = {
    "quadratic": [
        ("factorisation_roots", 0.22),
        ("nature_of_roots", 0.20),
        ("word_problem_area", 0.18),
        ("equal_roots_k", 0.15),
        ("formula_roots", 0.12),
        ("hots_quad", 0.13),
    ],
    "generic": [
        ("numerical_find", 0.25),
        ("concept_apply", 0.22),
        ("word_problem", 0.20),
        ("multi_step", 0.18),
        ("proof_derive", 0.08),
        ("hots_fusion", 0.07),
    ],
    "quadrilaterals": [
        ("parallelogram_opposite", 0.22),
        ("diagonal_bisect", 0.20),
        ("midpoint_theorem", 0.18),
        ("area_quad", 0.14),
        ("quad_proof", 0.10),
        ("rhombus_diagonal", 0.08),
        ("trapezium_parallel", 0.08),
    ],
    "circles": [
        ("length_find", 0.28),
        ("angle_theorem", 0.20),
        ("hidden_theorem", 0.18),
        ("concentric", 0.12),
        ("secant_tangent", 0.10),
        ("converse_identify", 0.07),
        ("direct_theorem", 0.03),
        ("chord_tangent", 0.08),
        ("common_tangent", 0.06),
        ("hots_mixed", 0.08),
    ],
    "generic": [
        ("numerical_find", 0.25),
        ("concept_apply", 0.22),
        ("word_problem", 0.20),
        ("multi_step", 0.18),
        ("proof_derive", 0.08),
        ("hots_fusion", 0.07),
    ],
}

# Human uneven rhythm — includes sparse hard spike + exercise-memory teach/reuse slots
HUMAN_SEQUENCE_SLOTS = [
    {"slot": 1, "band": "L1", "role": "Direct warm-up", "one_line_ok": False, "memory": "teach"},
    {"slot": 2, "band": "L2", "role": "Variation — pattern anchor", "one_line_ok": False, "memory": "teach"},
    {"slot": 3, "band": "L5", "role": "Sparse hard — minimal stem, deep answer", "one_line_ok": False, "sparse_hard": True},
    {"slot": 4, "band": "L2", "role": "Easier conceptual", "one_line_ok": True},
    {"slot": 5, "band": "L5", "role": "HOTS — disguised reuse of Q2 pattern", "one_line_ok": False, "memory": "reuse"},
]

# Hard UI paper — medium floor, no easy drill cluster
HARD_SEQUENCE_SLOTS = [
    {
        "slot": 1,
        "band": "L3",
        "role": "Medium — hidden length, concentric, or chord (NOT tangent-pair central angle)",
        "one_line_ok": False,
        "memory": "teach",
        "forbid_archetypes": ("angle_theorem",),
    },
    {
        "slot": 2,
        "band": "L4",
        "role": "Theorem chain — chord–tangent, similarity, or cyclic (NOT duplicate tangent-pair angle)",
        "one_line_ok": False,
        "memory": "teach",
        "forbid_archetypes": ("angle_theorem",),
    },
    {"slot": 3, "band": "L5", "role": "Sparse hard proof — 6+ steps, congruence or chord ⟂ radius", "one_line_ok": False, "sparse_hard": True},
    {"slot": 4, "band": "L3", "role": "Multi-concept — concentric, secant+tangent, or similarity", "one_line_ok": False},
    {"slot": 5, "band": "L5", "role": "HOTS — disguised reuse, OR proof+find (fusion, not bare equal tangents)", "one_line_ok": False, "memory": "reuse"},
    {"slot": 6, "band": "L3", "role": "Mixed", "one_line_ok": False},
    {"slot": 7, "band": "L1", "role": "Direct find", "one_line_ok": False},
    {"slot": 8, "band": "L5", "role": "Challenge", "one_line_ok": False, "memory": "reuse"},
]

# Figure element count progression (psychological)
FIGURE_COMPLEXITY = [
    "simple: centre + one tangent",
    "add second radius or external point",
    "angle marking ATB or AOB",
    "secant + tangent or interior point",
    "dense: concentric + chord + right angle",
]

ARCHETYPE_BY_ID = {
    a["id"]: a
    for a in (
        CIRCLE_ARCHETYPES
        + QUADRILATERAL_ARCHETYPES
        + QUADRATIC_ARCHETYPES
        + GENERIC_ARCHETYPES
    )
}


def _chapter_archetype_pool(chapter: str) -> List[Dict[str, str]]:
    if chapter == "quadratic":
        return QUADRATIC_ARCHETYPES
    if chapter == "quadrilaterals":
        return QUADRILATERAL_ARCHETYPES
    if chapter == "circles":
        return CIRCLE_ARCHETYPES
    if chapter == "generic":
        return GENERIC_ARCHETYPES
    # Never leak Circles archetypes into other chapters
    return GENERIC_ARCHETYPES


# Order: specific chapters before generic; avoid mapping quad PDF → circles via "chord"
_CHAPTER_DETECT_ORDER: List[tuple[str, tuple[str, ...]]] = [
    ("quadratic", ("quadratic", "quadratic equation", "discriminant", "nature of roots", "x^2", "x²")),
    ("quadrilaterals", (
        "quadrilateral", "parallelogram", "rhombus", "trapezium", "trapezoid",
        "rectangle", "square", "midpoint theorem", "mid-point theorem",
    )),
    ("triangles", ("triangle", "similar triangles", "congruence", "pythagoras theorem")),
    ("circles", ("circle", "tangent", "circles", "secant", "concentric", "cyclic")),
    ("polynomials", ("polynomial", "zeroes of", "zeros of", "division algorithm")),
    ("coordinate", ("coordinate", "distance formula", "section formula", "slope")),
    ("trigonometry", ("trigonometry", "sin", "cos", "tan", "identity", "angle of elevation")),
    ("probability", ("probability", "dice", "cards", "random", "event")),
    ("arithmetic", ("arithmetic progression", "ap", "common difference", "nth term", "sum of n terms")),
    ("statistics", ("mean", "median", "mode", "frequency", "histogram")),
]


def detect_chapter_key(topic_focus: str = "", filename: str = "", context: str = "") -> str:
    blob = f"{topic_focus} {filename} {context[:1200]}".lower()
    for chapter, keys in _CHAPTER_DETECT_ORDER:
        if any(k in blob for k in keys):
            return chapter
    return "generic"


def chapter_content_alignment_note(
    chapter: str,
    filename: str = "",
    *,
    subject: str = "",
    class_level: str = "",
    topic_focus: str = "",
    context: str = "",
    instructions: str = "",
) -> str:
    """Force RAG/Cursor to match SELECTED DOCUMENT — delegates to content_profile."""
    from app.generation.content_profile import build_chapter_alignment, build_content_profile

    profile = build_content_profile(
        topic_focus=topic_focus,
        filename=filename,
        context=context,
        subject=subject,
        class_level=class_level,
        instructions=instructions,
    )
    profile.chapter_key = chapter or profile.chapter_key
    return build_chapter_alignment(profile)


def pick_weighted_archetypes(
    n: int,
    chapter: str = "generic",
    seed: int | None = None,
    *,
    ui_difficulty: str = "medium",
) -> List[Dict[str, str]]:
    ui = (ui_difficulty or "medium").lower()
    pool_ids_set = {a["id"] for a in _chapter_archetype_pool(chapter)}
    if ui in ("hard", "difficult"):
        raw = CHAPTER_PATTERNS_HARD.get(chapter, CHAPTER_PATTERNS_HARD.get("generic", []))
    else:
        raw = CHAPTER_PATTERNS.get(chapter, CHAPTER_PATTERNS.get("generic", []))
    weights = [(aid, p) for aid, p in raw if aid in pool_ids_set]
    if not weights:
        weights = [(a["id"], 1.0) for a in _chapter_archetype_pool(chapter)]
    rng = random.Random(seed)
    if ui in ("hard", "difficult"):
        chosen_ids = pick_diverse_archetype_ids(n, chapter, rng, ui_difficulty=ui)
    else:
        ids = [w[0] for w in weights]
        probs = [w[1] for w in weights]
        chosen_ids = []
        pool_ids, pool_probs = list(ids), list(probs)
        for _ in range(n):
            if not pool_ids:
                pool_ids, pool_probs = list(ids), list(probs)
            pick = rng.choices(pool_ids, weights=pool_probs, k=1)[0]
            chosen_ids.append(pick)
            if pick in pool_ids:
                idx = pool_ids.index(pick)
                pool_ids.pop(idx)
                pool_probs.pop(idx)
    return [ARCHETYPE_BY_ID[i] for i in chosen_ids if i in ARCHETYPE_BY_ID]


def get_slot_bands(question_count: int, ui_difficulty: str = "medium") -> List[str]:
    ui = (ui_difficulty or "medium").lower()
    if ui in ("hard", "difficult"):
        mix = HARD_DIFFICULTY_MIX_5 if question_count <= 5 else HARD_DIFFICULTY_MIX_8
    else:
        mix = TEXTBOOK_DIFFICULTY_MIX_5 if question_count <= 5 else TEXTBOOK_DIFFICULTY_MIX_8
    return [mix[i % len(mix)]["band"] for i in range(question_count)]


def build_paper_blueprint(
    question_count: int,
    dominant_ui_difficulty: str = "hard",
    *,
    chapter: str = "generic",
    author: Optional[AuthorStyle] = None,
    topic_focus: str = "",
    filename: str = "",
    context: str = "",
    locked_chapter: str = "",
    required_theorems: Optional[List[Dict[str, str]]] = None,
    use_curriculum_archetypes: bool = False,
) -> str:
    """
    DEPRECATED — use PromptCompiler.compile_full_prompt() + SemanticGenerationPlan.

    Returns a minimal chapter-only stub (no global geometry author DNA).
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(
        "build_paper_blueprint is deprecated; use PromptCompiler + ChapterRulePack"
    )
    if locked_chapter:
        chapter = locked_chapter
    elif chapter == "generic":
        chapter = detect_chapter_key(topic_focus, filename, context)
        from app.generation.chapter_concept_classifier import resolve_locked_chapter

        ch2, _, _ = resolve_locked_chapter(
            filename=filename, topic_focus=topic_focus, context=context
        )
        if ch2 != "generic":
            chapter = ch2
    from app.generation.chapter_rule_packs import get_chapter_rule_pack
    from app.generation.chapter_prompt_isolation import (
        build_chapter_hard_prompt_stack,
        real_difficulty_mix_note,
        figure_type_hint_for_chapter,
    )

    pack = get_chapter_rule_pack(chapter)
    ui = (dominant_ui_difficulty or "medium").lower()
    lines = [
        f"EXERCISE BLUEPRINT — {pack.display_title} (ids 1..N):",
        pack.preferred_types_block(),
        pack.semantic_completeness_rules(),
    ]
    if ui in ("hard", "difficult"):
        hm = build_chapter_hard_prompt_stack(chapter, ui)
        if hm:
            lines.extend(["", hm])
    lines.extend(
        [
            "",
            real_difficulty_mix_note(chapter, ui),
            figure_type_hint_for_chapter(chapter),
            "",
            "Use PromptCompiler for full generation — this stub is chapter-scoped only.",
        ]
    )
    return "\n".join(lines)


def get_slot_metadata(
    question_count: int,
    author: AuthorStyle,
    ui_difficulty: str = "medium",
    *,
    locked_chapter: str = "",
) -> List[Dict[str, Any]]:
    """Per-question slot flags for curation pipeline."""
    ui = (ui_difficulty or "medium").lower()
    chapter = (locked_chapter or "").strip().lower()
    if not chapter:
        from app.generation.topic_isolation import get_current_topic_state

        chapter = (get_current_topic_state() or {}).get("locked_chapter", "generic")
    profile = get_chapter_imperfection_profile(chapter, author)
    memory = build_exercise_memory_plan(question_count, locked_chapter=chapter)
    teach_idx = memory[0]["teach_index"] if memory else -1
    reuse_idx = memory[0]["reuse_index"] if memory else -1
    sequence_slots = sequence_slots_for_chapter(chapter, ui)
    bands = get_slot_bands(question_count, ui_difficulty=ui)

    meta: List[Dict[str, Any]] = []
    for i in range(question_count):
        seq = sequence_slots[i % len(sequence_slots)]
        slot_num = i + 1
        meta.append(
            {
                "slot": slot_num,
                "band": bands[i] if i < len(bands) else seq.get("band", "L3"),
                "role": seq.get("role", ""),
                "ui_difficulty": ui,
                "sparse_hard": slot_num == profile.sparse_hard_slot or seq.get("sparse_hard"),
                "imperfect_compression": (i % 4 == 1) and profile.imperfect_compression_rate > 0,
                "exercise_memory_teach": i == teach_idx,
                "exercise_memory_reuse": i == reuse_idx,
                "one_line_ok": seq.get("one_line_ok", False),
                "forbid_archetypes": seq.get("forbid_archetypes", ()),
                "figure_complexity": figure_complexity_for_chapter(chapter, i),
                "locked_chapter": chapter,
                "visual_hints": profile.visual.figure_spec_hints,
            }
        )
    return meta


def archetype_prompt_block(chapter: str = "generic") -> str:
    weights = CHAPTER_PATTERNS.get(chapter, CHAPTER_PATTERNS["generic"])
    rows = ["| Pattern | Frequency |", "|---------|-----------|"]
    for aid, w in sorted(weights, key=lambda x: -x[1])[:6]:
        name = ARCHETYPE_BY_ID.get(aid, {}).get("name", aid)
        rows.append(f"| {name} | {'high' if w >= 0.15 else 'medium' if w >= 0.08 else 'low'} |")
    return "\n".join(rows)
