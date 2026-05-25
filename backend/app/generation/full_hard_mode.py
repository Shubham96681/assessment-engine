"""
Full-hard paper mode — when UI difficulty slider is ~100% hard.

Board_hard still allows L3 warm-ups; full_hard enforces examiner-grade depth on
every slot: hidden theorems, multi-step proofs, no direct NCERT one-liners.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

# Slot bands when hard ≥ threshold and easy+medium negligible
FULL_HARD_THRESHOLD = 90
FULL_HARD_MAX_EASY_MEDIUM = 10

CIRCLES_FULL_HARD_SEQUENCE_SLOTS: List[Dict[str, Any]] = [
    {
        "slot": 1,
        "band": "L5",
        "role": "L5 concentric chord — hidden perpendicular+bisect before Pythagoras; establishes R, r for chain",
        "one_line_ok": False,
        "memory": "teach",
        "depends_on": [],
        "forbid_archetypes": ("length_find", "angle_theorem", "direct_theorem"),
    },
    {
        "slot": 2,
        "band": "L5",
        "role": "Depends Q1 — Hence-only tangent–secant (NO repeat Q1 chord find; NO (i) chord part)",
        "one_line_ok": False,
        "memory": "teach",
        "depends_on": [1],
        "forbid_archetypes": ("angle_theorem", "converse_identify"),
    },
    {
        "slot": 3,
        "band": "L5",
        "role": "Proof chain 5+ steps — congruence/RHS then Hence numeric (sparse stem OK)",
        "one_line_ok": False,
        "sparse_hard": True,
    },
    {
        "slot": 4,
        "band": "L5",
        "role": "Concentric + chord + tangent fusion OR similarity + secant (case reasoning)",
        "one_line_ok": False,
    },
    {
        "slot": 5,
        "band": "L5",
        "role": "HOTS — depends Q1+Q2 — radius trap + Hence secant on same narrative",
        "one_line_ok": False,
        "memory": "reuse",
        "depends_on": [1, 2],
    },
]

CIRCLES_FULL_HARD_RULES = """
FULL HARD (100% hard UI) — Circles — EXAMINER STANDARD (ALL SLOTS L5):
- 100% hard slider means EVERY question is L5 — multi-theorem, hidden first step, proof or Hence chain.
- BAN L3/L4-style one-step finds, direct formula drills, or single-theorem recall in any slot.
- BAN Q1/Q2: direct Pythagoras after radius ⟂ tangent only; bare r² + a² = c²; OP/OQ find PQ only.
- BAN: standard NCERT one-shot proofs without Hence/find branch.
- BAN: angle at centre = 180° − given only; "Name secant/tangent"; "Can a tangent…?"
- REQUIRE each stem: indirect givens OR disguised setup OR non-obvious first deduction.
- REQUIRE model answers: minimum 5 labeled steps (Given → Step 1 → … → Hence) on EVERY item.
- REQUIRE ≥3 distinct theorem families per item; ≥4 inference links; at least ONE proof+Hence fusion.
- Q5 must fuse prior-slot configuration (dependency graph) — not an isolated drill.
- NUMERIC FEASIBILITY: secant chord PQ = (WT²/WP)−WP must satisfy PQ ≤ 2R; pick WP ≥ min feasible.
- BAN Q2(i) that only repeats Q1 chord with no new structure — Q2 must start with Hence tangent–secant only.
- Q1 concentric radii: pick R and r so R² − r² is a perfect square (e.g. 17&8→chord 30, 13&5→24) — not messy surds like 18&8.
- Q3 converse proof: state givens (line meets circle only at S; OS ⟂ line) — figure must show S and tangent line.
- Prefer multi-concept fusion (area ratio, converse proof, angle between common tangent and MN) over third tangent-secant drill.
- PDF stems: write sin inverse (5/13) not sin^{-1} — no LaTeX braces in question text.
"""

GENERIC_FULL_HARD_RULES = """
FULL HARD (100% hard UI) — ALL SLOTS L5:
- Every item is maximum board-hard depth (L5): hidden trap, multi-step chain, Hence branches.
- BAN warm-up L3/L4 items, one-step recall, and bare theorem naming in stems.
- Model answers: 5+ steps; cite prior questions when the paper dependency graph requires it.
"""

def _trigonometry_full_hard_rules() -> str:
    from app.generation.trigonometry_hard_benchmark import benchmark_prompt_block

    return (
        """
FULL HARD (100% hard UI) — Trigonometry — ALL SLOTS L5 (benchmark-aligned):
- Reference paper: 20 questions × 6 marks (122 total, 3 h); deliver 10×6 (+8 on last) for board runs.
- EVERY item: (i)(ii)(iii) or balanced OR; 5+ answer steps; marks 6 (slot 10 → 8 if count≥8).
- BAN: bare "Find cos 255° exactly" / one-line recall; L3/L4 warm-up; duplicate reduction pair.
- REQUIRE: section spread — compound prove+Hence → equation/identity → reduction → OR fusion.
- REQUIRE: Q2 teaches identity chain → Q5 disguised reuse (new givens, same inference).
- Model answers: Given → Step 1 → Step 2 → Step 3 → Hence; theorems only in answers.
"""
        + "\n"
        + benchmark_prompt_block()
    )


TRIGONOMETRY_FULL_HARD_RULES = _trigonometry_full_hard_rules()

TRIGONOMETRY_FULL_HARD_SEQUENCE_SLOTS: List[Dict[str, Any]] = [
    {"slot": 1, "band": "L5", "role": "Degree–radian + quadrant + exact surds (compound angle)", "one_line_ok": False, "memory": "teach"},
    {"slot": 2, "band": "L5", "role": "Prove compound-angle identity (sin/cos/tan addition)", "one_line_ok": False, "memory": "teach"},
    {"slot": 3, "band": "L5", "role": "Sparse — all ratios from one function in QII/QIII", "one_line_ok": False, "sparse_hard": True},
    {"slot": 4, "band": "L5", "role": "Second identity proof — different formula than Q2", "one_line_ok": False},
    {"slot": 5, "band": "L5", "role": "HOTS prove + apply OR hidden-condition ratio fusion", "one_line_ok": False, "memory": "reuse", "depends_on": [2]},
    {"slot": 6, "band": "L5", "role": "Reciprocal ratios in another quadrant — multi-step", "one_line_ok": False},
    {"slot": 7, "band": "L5", "role": "Prove identity then find exact value (Hence chain)", "one_line_ok": False},
    {"slot": 8, "band": "L5", "role": "Large negative/large radian reduction — all steps", "one_line_ok": False},
    {"slot": 9, "band": "L5", "role": "Degree reduction with reciprocal ratio", "one_line_ok": False},
    {"slot": 10, "band": "L5", "role": "HOTS balanced OR — both branches prove+find, same difficulty", "one_line_ok": False, "memory": "reuse"},
]

CHAPTER_FULL_HARD_RULES: Dict[str, str] = {
    "circles": CIRCLES_FULL_HARD_RULES,
    "trigonometry": TRIGONOMETRY_FULL_HARD_RULES,
    "quadratic": GENERIC_FULL_HARD_RULES
    + "\n- Quadratic L5: parameter fusion, discriminant traps, word model + Hence verify.",
    "generic": GENERIC_FULL_HARD_RULES,
}

CHAPTER_FULL_HARD_SEQUENCE_SLOTS: Dict[str, List[Dict[str, Any]]] = {
    "circles": CIRCLES_FULL_HARD_SEQUENCE_SLOTS,
    "trigonometry": TRIGONOMETRY_FULL_HARD_SEQUENCE_SLOTS,
}


def _dist_values(
    difficulty_distribution: Optional[Union[Any, Dict[str, int]]],
) -> tuple[int, int, int]:
    if difficulty_distribution is None:
        return 0, 50, 20
    if isinstance(difficulty_distribution, dict):
        return (
            int(difficulty_distribution.get("easy", 0) or 0),
            int(difficulty_distribution.get("medium", 0) or 0),
            int(difficulty_distribution.get("hard", 0) or 0),
        )
    return (
        int(getattr(difficulty_distribution, "easy", 0) or 0),
        int(getattr(difficulty_distribution, "medium", 0) or 0),
        int(getattr(difficulty_distribution, "hard", 0) or 0),
    )


def is_full_hard_paper(
    difficulty_distribution: Optional[Union[Any, Dict[str, int]]] = None,
) -> bool:
    """True when UI is effectively 100% hard (no easy/medium slack)."""
    easy, medium, hard = _dist_values(difficulty_distribution)
    return hard >= FULL_HARD_THRESHOLD and (easy + medium) <= FULL_HARD_MAX_EASY_MEDIUM


def full_hard_prompt_block(chapter: str) -> str:
    from app.generation.chapter_prompt_isolation import normalize_chapter

    return CHAPTER_FULL_HARD_RULES.get(normalize_chapter(chapter), "").strip()


def full_hard_calibration_lines(chapter: str) -> tuple[str, ...]:
    ch = (chapter or "generic").strip().lower()
    if ch == "circles":
        return (
            "FULL HARD (100%): ALL five slots are L5 — hardest board tier, not L4 warm-up.",
            "Each item: hidden first step + ≥3 theorem families + 5+ answer steps + Hence.",
            "Reject any question that could be solved in ≤2 standard NCERT moves.",
            "Paper dependency chain active — Q2/Q5 must reference earlier deductions.",
        )
    if ch == "trigonometry":
        from app.generation.trigonometry_hard_benchmark import benchmark_calibration_lines

        return benchmark_calibration_lines()
    return (
        "FULL HARD (100%): every slot L5; 5+ reasoning steps; ban one-step and L4 drills.",
        "Require indirect givens, multi-concept fusion, and Hence chains.",
    )


def full_hard_minimum_slot_band() -> str:
    """Minimum blueprint band when UI is 100% hard."""
    return "L5"
