"""
Chapter-specific prompt isolation — hard rules, numeric blocks, figures, sequences.

Universal hard-mode text was geometry-only and overwrote quadratic chapter locks.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set

from app.generation.strict_topic_gate import CHAPTER_FORBIDDEN

# ── Hard-mode prompt blocks (replace global geometry-only HARD_PAPER_RULES) ─────

CIRCLES_HARD_RULES = """
HARD MODE — Circles (mandatory when UI difficulty is hard):
STEM REPHRASING (raise difficulty — do not copy NCERT one-liners):
- Combine two ideas in one stem: e.g. concentric chord find + external tangent–secant on the same figure.
- Use (i)(ii) or (i)(ii)(iii) on L4/L5 instead of a single "Find AB".
- State indirect givens first (distances OP, OQ, radii) before the ask — trap stays invisible.
- FigureBased slots: full figure_spec required; stem may say "In the figure" but never "Use the diagram".
- BAN bare drills: "Find PQ" with only OP and OQ; "Prove tangent at T" without numeric follow-up on L4+.
- NOT an easy exercise set — minimum reasoning depth per slot band below.
- BAN as Q1/Q2: single-step Pythagoras after radius ⟂ tangent only.
- BAN: "Name the secant and tangent" unless slot explicitly allows ONE cooldown (max 1 per paper).
- MAX ONE paper item with reasoning graph: tangent_pair → quadrilateral → central/between angle.
- Tangent-pair angle finds: central angle at O between contact points (TOU), NOT angle TOW with W at centre.
- REQUIRE for L4/L5 slots: 3+ inference steps in model answer (Given → Step 1 → Step 2 → Hence).
- Q5 HOTS: disguised reuse, OR with proof branch, or multi-concept angle chase.
- Numeric: TA² = TC·TD, OT² − r² = TA², angle APB + angle AOB = 180° when radii ⟂ tangents.
- PROOF wording: "Prove that OT ⟂ tangent TR at T" or Theorem 10.1 idiom — NEVER "perpendicular from O to tangent at T passes through T".
- Multi-step concentric + secant: student must FIND chord length first — do NOT give √-form chord length in the stem before tangent–secant work.
- figure_spec: show_right_angle at point of contact; mark centre-to-contact radius dashed.
- PAPER DEPENDENCY (hard): Q1 establishes concentric chord; Q2 MUST reference Q1 with (i) chord (ii) Hence tangent–secant; Q5 fuses Q1–Q2 — not five isolated drills.
- FULL HARD (100%): every slot L5 — 5+ answer steps, ≥3 theorem families; reject L4/one-step items.
"""

QUADRATIC_HARD_RULES = """
HARD MODE — Quadratic Equations only (mandatory when UI difficulty is hard):
- Q1: non-trivial factorisation or coefficient trap (not mental one-step).
- Q2: discriminant D = b² − 4ac and nature of roots (real distinct / equal / no real).
- Q3: parameter k for equal roots or for a stated root condition.
- Q4: word problem (area, speed, consecutive integers) → form ax² + bx + c = 0.
- Q5 HOTS: OR branch (word problem OR sum-of-squares OR parameter fusion) — not geometry.
- BAN in every stem: circle, tangent, secant, radius, chord, concentric, angle AOB, centre O.
- L4/L5 answers: 3+ steps (form equation → discriminant or factor → roots → verify).
- Numeric: D must match stated nature; area (length)×(breadth) = given; speed times consistent.
"""

QUADRILATERALS_HARD_RULES = """
HARD MODE — Quadrilaterals only:
- Spread: parallelogram properties, diagonals, midpoint theorem, rhombus, area, proof+Hence.
- BAN: tangent, secant, radius, concentric circles, quadratic discriminant.
- L4/L5: 3+ proof or find steps; OR with same archetype and separate givens.
"""

TRIANGLES_HARD_RULES = """
HARD MODE — Triangles / similarity only:
- Spread: similarity ratio, congruence (RHS/SAS), Pythagoras, area ratio, proof+Hence.
- BAN: circle, secant, concentric, tangent at point of contact, discriminant, quadratic equation.
- L4/L5: 3+ steps; OR only with same archetype and separate numeric givens.
"""

TRIGONOMETRY_HARD_RULES = """
HARD MODE — Trigonometry only:
- Spread: radian/degree conversion, identities, quadrant signs, standard angles, proofs.
- BAN: circle geometry, secant, concentric, parallelogram, quadratic, tangent at contact point.
- L4/L5: 3+ steps in answers; stems vary — not every item labeled (i)(ii)(iii).
- Use per-slot stem_format: single prove, direct find, (i)(ii) only, OR, or full triple where assigned.
"""

GENERIC_HARD_RULES = """
HARD MODE — chapter from CONTEXT only:
- Match uploaded chapter structures; no circle templates unless CONTEXT is Circles.
- L4/L5: 3+ reasoning steps in model answers.
"""

CHAPTER_HARD_RULES: Dict[str, str] = {
    "circles": CIRCLES_HARD_RULES,
    "quadratic": QUADRATIC_HARD_RULES,
    "quadrilaterals": QUADRILATERALS_HARD_RULES,
    "triangles": TRIANGLES_HARD_RULES,
    "trigonometry": TRIGONOMETRY_HARD_RULES,
    "polynomials": GENERIC_HARD_RULES,
    "generic": GENERIC_HARD_RULES,
}

CIRCLES_REASONING_DIVERSITY = """
REASONING GRAPH DIVERSITY — Circles:
- Max ONE item: external tangents → quadrilateral angle sum → central angle.
- Spread: concentric chord, chord ⟂ radius proof, secant–tangent power, similarity, cyclic chase.
- L4/L5: 3+ dependent theorem steps — not a single quadrilateral angle sum.
- SEMANTIC UNIQUENESS: no two items may share the same theorem-equivalence graph (relabelled points forbidden).
"""

QUADRATIC_REASONING_DIVERSITY = """
REASONING DIVERSITY — Quadratic Equations:
- Max ONE area–rectangle / grove word problem per paper.
- Spread: factorisation, discriminant, equal-roots k, quadratic formula, speed–time, sum of squares.
- Do NOT repeat the same equation template with relabelled numbers only.
- L4/L5: operation chain must differ from Q1–Q2 (e.g. parameter k after factorisation paper).
"""

QUADRILATERALS_REASONING_DIVERSITY = """
REASONING DIVERSITY — Quadrilaterals:
- Spread diagonal, midpoint, opposite sides, rhombus, trapezium area — not circle graphs.
"""

GENERIC_REASONING_DIVERSITY = """
REASONING DIVERSITY:
- No two items with the same cognitive chain and only relabelled points.
"""

TRIANGLES_REASONING_DIVERSITY = """
REASONING DIVERSITY — Triangles:
- Spread similarity, congruence, Pythagoras, area ratio — not circle or quadratic graphs.
"""

TRIGONOMETRY_REASONING_DIVERSITY = """
REASONING DIVERSITY — Trigonometry:
- Spread identities, quadrant reduction, standard values, proofs — not circle templates.
- Max TWO period/reduction-only items per paper (standard_angle + quadrant_reduction).
- Do not repeat the same reduction template with relabelled angles only.
"""

TRIGONOMETRY_NUMERIC_RULES = """
NUMERIC CONSISTENCY — Trigonometry:
- Exact surd values only for standard angles (multiples of 15° after reduction).
- Quadrant signs: QII cos,tan negative; QIII all negative except tan,cot.
- OR options: comparable difficulty — both multi-step, not trivial reduction beside proof.
"""

TRIGONOMETRY_IDIOMATIC = """
TRIGONOMETRY PHRASING:
- Example: "If sin θ = 8/17 and θ lies in quadrant II, find the remaining ratios."
- Example: "Prove that cos(π − x) = −cos x using cos(A − B)."
- BAN minute angles (162°30′) with exact surd sin/cos requests.
"""

CHAPTER_REASONING_DIVERSITY: Dict[str, str] = {
    "circles": CIRCLES_REASONING_DIVERSITY,
    "quadratic": QUADRATIC_REASONING_DIVERSITY,
    "quadrilaterals": QUADRILATERALS_REASONING_DIVERSITY,
    "triangles": TRIANGLES_REASONING_DIVERSITY,
    "trigonometry": TRIGONOMETRY_REASONING_DIVERSITY,
    "generic": GENERIC_REASONING_DIVERSITY,
}

CIRCLES_NUMERIC_RULES = """
NUMERIC CONSISTENCY — Circles:
- Tangent–secant: TA² = TC × TD.
- Tangent length: TA² = OT² − radius².
- Secant feasibility: chord PQ = (WT²/WP) − WP must satisfy PQ ≤ 2R; require WP ≥ (−2R + √(4R²+4·WT²))/2.
- Tangent pair + centre: angle APB + angle AOB = 180° when radii ⟂ tangents at A, B.
- Concentric chord: AB = 2√(R² − r²) with R > r.
"""

QUADRATIC_NUMERIC_RULES = """
NUMERIC CONSISTENCY — Quadratics:
- Discriminant D = b² − 4ac must match equal / distinct / no real roots claim.
- Area models: (length)×(breadth) equals given area; reject negative dimensions.
- Speed–time: 1/v_out − 1/v_in = Δt/distance when times differ.
- Sum of squares: n² + (n+k)² = S must have consistent integer n when required.
"""

QUADRILATERALS_NUMERIC_RULES = """
NUMERIC CONSISTENCY — Quadrilaterals:
- Parallelogram: opposite sides equal; diagonals bisect.
- Rhombus: diagonals perpendicular; side from half-diagonals via Pythagoras.
"""

CHAPTER_NUMERIC_RULES: Dict[str, str] = {
    "circles": CIRCLES_NUMERIC_RULES,
    "quadratic": QUADRATIC_NUMERIC_RULES,
    "quadrilaterals": QUADRILATERALS_NUMERIC_RULES,
    "trigonometry": TRIGONOMETRY_NUMERIC_RULES,
    "generic": "",
}

QUADRATIC_IDIOMATIC = """
ALGEBRA / WORD-PROBLEM PHRASING (Quadratic Equations):
- Example: "Find the nature of roots of 2x² − 5x + 3 = 0."
- Example: "Length is twice breadth; area 800 m². Form the quadratic and find x."
- BAN circle/tangent vocabulary entirely.
"""

CIRCLES_IDIOMATIC = """
IDIOMATIC GEOMETRY (Circles):
- Tangent ⟂ radius: 'Prove that OT is perpendicular to tangent TR at T.'
- Angle find: name full angle (PTQ, AOB) AND give a numeric given.
"""

CHAPTER_IDIOMATIC: Dict[str, str] = {
    "circles": CIRCLES_IDIOMATIC,
    "quadratic": QUADRATIC_IDIOMATIC,
    "quadrilaterals": "Use standard quadrilateral theorem wording from NCERT/RD Sharma.",
    "trigonometry": TRIGONOMETRY_IDIOMATIC,
    "generic": "",
}

QUADRATIC_FIGURE_COMPLEXITY = [
    "rectangle area model: labelled length and breadth",
    "table: equation | discriminant | nature of roots",
    "segment diagram A–B for speed–distance",
    "algebra layout ax² + bx + c = 0 (no circle)",
    "HOTS: two-part word setup or OR branches",
]

CIRCLES_FIGURE_COMPLEXITY = [
    "simple: centre + one tangent",
    "add second radius or external point",
    "angle marking ATB or AOB",
    "secant + tangent or interior point",
    "dense: concentric + chord + right angle",
]

CHAPTER_FIGURE_COMPLEXITY: Dict[str, List[str]] = {
    "circles": CIRCLES_FIGURE_COMPLEXITY,
    "quadratic": QUADRATIC_FIGURE_COMPLEXITY,
    "quadrilaterals": [
        "parallelogram ABCD with diagonals",
        "rhombus with perpendicular diagonals",
        "trapezium with parallel sides marked",
        "midpoint on sides of triangle",
        "HOTS: prove then Hence find",
    ],
    "generic": ["labeled diagram from chapter CONTEXT"],
}

QUADRATIC_HARD_SEQUENCE_SLOTS = [
    {"slot": 1, "band": "L5", "role": "Discriminant + nature + verify relations", "one_line_ok": False, "memory": "teach"},
    {"slot": 2, "band": "L5", "role": "Messy factorisation or middle-term split", "one_line_ok": False, "memory": "teach"},
    {"slot": 3, "band": "L5", "role": "Sparse — equal roots parameter; verify double root", "one_line_ok": False, "sparse_hard": True},
    {"slot": 4, "band": "L5", "role": "Area or speed word problem → reject invalid root", "one_line_ok": False},
    {"slot": 5, "band": "L5", "role": "HOTS OR fusion — disguised reuse", "one_line_ok": False, "memory": "reuse"},
]

from app.generation.full_hard_mode import (
    CIRCLES_FULL_HARD_SEQUENCE_SLOTS,
    TRIGONOMETRY_FULL_HARD_SEQUENCE_SLOTS,
)

CHAPTER_HARD_SEQUENCE_SLOTS: Dict[str, List[Dict[str, Any]]] = {
    "quadratic": QUADRATIC_HARD_SEQUENCE_SLOTS,
}

CHAPTER_FULL_HARD_SEQUENCE_SLOTS: Dict[str, List[Dict[str, Any]]] = {
    "circles": CIRCLES_FULL_HARD_SEQUENCE_SLOTS,
    "trigonometry": TRIGONOMETRY_FULL_HARD_SEQUENCE_SLOTS,
}

CHAPTER_REAL_DIFFICULTY_NOTE: Dict[str, str] = {
    "circles": (
        "- HARD UI: Q1–Q2 medium+ with DISTINCT reasoning graphs; Q3 sparse proof; "
        "Q4 multi-concept; Q5 HOTS fusion. Max ONE tangent-pair→quadrilateral→central angle item."
    ),
    "quadratic": (
        "- HARD UI: ALL slots L5 — parameter, without solving, word+reject, OR; "
        "BAN bare factorise/discriminant drills. NO circle/tangent items."
    ),
    "quadrilaterals": (
        "- HARD UI: mix proofs and finds; diagonals / midpoint / area; no circle templates."
    ),
    "trigonometry": (
        "- Board mix: conversion, identity proofs, ratio finds, one short standard value, "
        "HOTS prove+apply; max 2 reduction drills; balanced OR on last item."
    ),
    "generic": "- ~2 easy, ~2 medium, ~1 sparse hard, ~1 challenge — from CONTEXT chapter only.",
}

# Extra forbidden tokens for blueprint / archetype scanning (before generation)
CHAPTER_BLUEPRINT_FORBIDDEN: Dict[str, Set[str]] = {
    "quadratic": CHAPTER_FORBIDDEN.get("quadratic", set())
    | {"circle", "tangent", "secant", "radius", "chord", "concentric", "aob", "centre", "center"},
}


def normalize_chapter(chapter: str) -> str:
    c = (chapter or "generic").strip().lower()
    return c if c in CHAPTER_HARD_RULES else "generic"


def hard_mode_prompt_block(chapter: str = "generic") -> str:
    return CHAPTER_HARD_RULES.get(normalize_chapter(chapter), GENERIC_HARD_RULES).strip()


def reasoning_diversity_prompt_block(
    chapter: str = "generic",
    question_count: int = 10,
    *,
    paper_template_id: Optional[str] = None,
    ui_difficulty: str = "hard",
    full_hard: bool = False,
) -> str:
    ch = normalize_chapter(chapter)
    base = CHAPTER_REASONING_DIVERSITY.get(ch, GENERIC_REASONING_DIVERSITY).strip()
    from app.generation.theorem_variety_engine import theorem_variety_prompt_block

    extra = theorem_variety_prompt_block(
        ch,
        question_count,
        paper_template_id=paper_template_id,
        ui_difficulty=ui_difficulty,
        full_hard=full_hard,
    )
    return f"{base}\n{extra}".strip() if extra else base


def numeric_prompt_block(chapter: str = "generic") -> str:
    return CHAPTER_NUMERIC_RULES.get(normalize_chapter(chapter), "").strip()


def idiomatic_prompt_block(chapter: str = "generic") -> str:
    return CHAPTER_IDIOMATIC.get(normalize_chapter(chapter), "").strip()


def figure_complexity_for_chapter(chapter: str, index: int) -> str:
    hints = CHAPTER_FIGURE_COMPLEXITY.get(
        normalize_chapter(chapter), CHAPTER_FIGURE_COMPLEXITY["generic"]
    )
    return hints[index] if index < len(hints) else hints[-1]


def sequence_slots_for_chapter(
    chapter: str,
    ui_difficulty: str,
    *,
    full_hard: bool = False,
    question_count: int = 10,
    elevated_hard: bool = False,
) -> List[Dict[str, Any]]:
    from app.generation.rd_archetypes import HARD_SEQUENCE_SLOTS, HUMAN_SEQUENCE_SLOTS

    ui = (ui_difficulty or "medium").lower()
    ch = normalize_chapter(chapter)
    if ui in ("hard", "difficult"):
        if full_hard and ch == "trigonometry":
            from app.generation.trigonometry_hard_benchmark import benchmark_slots

            return benchmark_slots(question_count)
        if (full_hard or elevated_hard) and ch == "quadratic":
            from app.generation.quadratic_hard_benchmark import benchmark_slots

            return benchmark_slots(question_count)
        if full_hard and ch in CHAPTER_FULL_HARD_SEQUENCE_SLOTS:
            return CHAPTER_FULL_HARD_SEQUENCE_SLOTS[ch]
        if ch in CHAPTER_HARD_SEQUENCE_SLOTS:
            return CHAPTER_HARD_SEQUENCE_SLOTS[ch]
        from app.generation.chapter_rule_packs import CHAPTER_RULES, get_chapter_rule_pack
        from app.generation.chapter_prompt_config import sequence_slots_from_rule_pack

        if ch in CHAPTER_RULES:
            derived = sequence_slots_from_rule_pack(
                get_chapter_rule_pack(ch), full_hard=full_hard
            )
            if derived:
                return derived
        return HARD_SEQUENCE_SLOTS
    return HUMAN_SEQUENCE_SLOTS


def real_difficulty_mix_note(
    chapter: str,
    ui_difficulty: str,
    *,
    full_hard: bool = False,
) -> str:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return "- ~2 easy, ~2 medium, ~1 sparse hard (minimal stem), ~1 challenge."
    if full_hard:
        from app.generation.full_hard_mode import full_hard_calibration_lines

        ch = normalize_chapter(chapter)
        return "\n".join(f"- {ln}" for ln in full_hard_calibration_lines(ch))
    return CHAPTER_REAL_DIFFICULTY_NOTE.get(
        normalize_chapter(chapter),
        CHAPTER_REAL_DIFFICULTY_NOTE["generic"],
    )


def build_chapter_hard_prompt_stack(
    chapter: str,
    ui_difficulty: str,
    *,
    full_hard: bool = False,
) -> str:
    """Single stack: chapter hard + reasoning + numeric — no geometry bleed."""
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return ""
    ch = normalize_chapter(chapter)
    from app.generation.cognitive_graph_validator import cognitive_graph_prompt_block
    from app.generation.full_hard_mode import full_hard_prompt_block

    parts = [
        full_hard_prompt_block(ch) if full_hard else "",
        hard_mode_prompt_block(ch),
        reasoning_diversity_prompt_block(ch),
        cognitive_graph_prompt_block(ch),
        numeric_prompt_block(ch),
        idiomatic_prompt_block(ch),
    ]
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def filter_archetypes_to_chapter(
    archetypes: List[Dict[str, Any]],
    chapter: str,
) -> List[Dict[str, Any]]:
    from app.generation.archetype_registry import filter_archetype_dicts

    return filter_archetype_dicts(archetypes, chapter)


def scan_text_for_chapter_contamination(text: str, chapter: str) -> List[str]:
    """Pre-generation scan of blueprint / archetype lines."""
    forbidden = CHAPTER_BLUEPRINT_FORBIDDEN.get(normalize_chapter(chapter), set())
    if not forbidden or not text:
        return []
    low = text.lower()
    hits = []
    for term in sorted(forbidden):
        if re.search(rf"\b{re.escape(term)}\b", low):
            hits.append(term)
    return hits


def figure_type_hint_for_chapter(chapter: str) -> str:
    ch = normalize_chapter(chapter)
    if ch == "quadratic":
        return (
            "FigureBased for quadratics: use labeled_diagram (rectangle/segment layout), "
            "table, line_graph, or flowchart — NEVER circle/tangent diagrams."
        )
    if ch == "circles":
        return "FigureBased: labeled_diagram with circle, points A–Z, radii dashed, tangents solid."
    return "FigureBased: match chapter CONTEXT visual style."
