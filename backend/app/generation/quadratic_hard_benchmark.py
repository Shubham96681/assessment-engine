"""
Hardest quadratic benchmark — full-hard Class 10 / RD Sharma L5 / GATE-stretch.

Used when UI is ≥90% hard + chapter quadratic: every slot L5, fusion stems,
parameter traps, without-solving chains, word models + reject root, balanced OR.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

FULL_HARD_MARKS_PER_SLOT = 4
FULL_HARD_LAST_SLOT_MARKS = 5

BENCHMARK_PROMPT_RULES = """
QUADRATIC FULL HARD — ALL SLOTS L5 (hardest tier):
- BAN: bare "Solve x² − … by factorisation" with no second target; single-line "Find k for equal roots".
- BAN: discriminant-only one step; NCERT Example-1 drills; circle/tangent vocabulary.
- REQUIRE: 5–7 answer steps; hidden trap (parameter, without solving, or word reject).
- STEM VARIETY: rotate layouts — not every (i)(ii)(iii); max ~40% triple-part.
- Mix: without solving + α²+β², parameter interval, equal roots + verify, speed/area word, OR capstone.
- Marks: 4 per slot (slot 10 → 5 if count≥10).
"""

BENCHMARK_SLOTS_10: Tuple[Dict[str, Any], ...] = (
    {
        "slot": 1,
        "band": "L5",
        "archetype_id": "nature_of_roots",
        "role": "Discriminant + nature + factorise; verify αβ = c/a",
        "stem_format": "prove_hence_ii",
        "marks": 4,
    },
    {
        "slot": 2,
        "band": "L5",
        "archetype_id": "factorisation_roots",
        "role": "Messy middle-term split; sum/product from coefficients",
        "stem_format": "direct_find",
        "marks": 4,
    },
    {
        "slot": 3,
        "band": "L5",
        "archetype_id": "equal_roots_k",
        "role": "Sparse — equal roots parameter k; verify repeated root",
        "stem_format": "sparse_single",
        "marks": 4,
        "sparse_hard": True,
    },
    {
        "slot": 4,
        "band": "L5",
        "archetype_id": "word_problem_area",
        "role": "Area or dimension word model → quadratic → valid root only",
        "stem_format": "word_model",
        "marks": 4,
    },
    {
        "slot": 5,
        "band": "L5",
        "archetype_id": "formula_roots",
        "role": "Balanced OR — formula with surds OR roots differ by d",
        "stem_format": "balanced_or",
        "marks": 4,
        "memory": "reuse",
    },
    {
        "slot": 6,
        "band": "L5",
        "archetype_id": "nature_of_roots",
        "role": "Without solving — nature + α² + β² from coefficients",
        "stem_format": "without_solving",
        "marks": 4,
    },
    {
        "slot": 7,
        "band": "L5",
        "archetype_id": "factorisation_roots",
        "role": "Form quadratic from given roots (surds or rationals)",
        "stem_format": "form_equation",
        "marks": 4,
    },
    {
        "slot": 8,
        "band": "L5",
        "archetype_id": "word_problem_area",
        "role": "Speed–time or stream word problem → quadratic",
        "stem_format": "word_model",
        "marks": 4,
    },
    {
        "slot": 9,
        "band": "L5",
        "archetype_id": "equal_roots_k",
        "role": "Parameter p — no real roots; least integer p",
        "stem_format": "parameter_interval",
        "marks": 4,
    },
    {
        "slot": 10,
        "band": "L5",
        "archetype_id": "hots_quad",
        "role": "Capstone OR — fusion branches, separate numeric givens",
        "stem_format": "balanced_or",
        "marks": 5,
        "memory": "reuse",
    },
)


def benchmark_slots(question_count: int) -> List[Dict[str, Any]]:
    """Expand or trim L5 slot plan for delivery count."""
    n = max(1, int(question_count or 10))
    out: List[Dict[str, Any]] = []
    for i in range(n):
        base = dict(BENCHMARK_SLOTS_10[i % len(BENCHMARK_SLOTS_10)])
        base["slot"] = i + 1
        base["band"] = "L5"
        base["one_line_ok"] = False
        base["full_hard"] = True
        if i == n - 1 and n >= 8:
            base["marks"] = FULL_HARD_LAST_SLOT_MARKS
        else:
            base["marks"] = base.get("marks", FULL_HARD_MARKS_PER_SLOT)
        out.append(base)
    return out


def target_marks_for_slot(slot: int, question_count: int) -> int:
    if slot == question_count and question_count >= 8:
        return FULL_HARD_LAST_SLOT_MARKS
    return FULL_HARD_MARKS_PER_SLOT


def benchmark_prompt_block() -> str:
    return BENCHMARK_PROMPT_RULES.strip()


def benchmark_calibration_lines() -> Tuple[str, ...]:
    return (
        "QUADRATIC FULL HARD: every slot L5 — parameter, without solving, word+reject, OR.",
        "Reject ≤2-step factorisation drills and thin 'Find k' stems.",
        "4 marks/item (last slot 5 if count≥8); 5–7 steps per model answer.",
        "Rotate stem_format per slot; max ~40% (i)(ii)(iii) papers.",
    )


def suggested_paper_totals(question_count: int) -> Dict[str, int]:
    n = question_count or 10
    marks = sum(target_marks_for_slot(s, n) for s in range(1, n + 1))
    return {
        "total_questions": n,
        "total_marks": marks,
        "marks_per_slot_default": FULL_HARD_MARKS_PER_SLOT,
    }
