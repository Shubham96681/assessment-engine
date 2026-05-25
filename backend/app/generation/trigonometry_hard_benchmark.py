"""
Hardest trigonometry benchmark — reference paper structure (20×6 marks, JEE-style).

Used when UI is 100% hard + chapter trigonometry: slot roles, marks (6 default),
(i)(ii)(iii) + prove–Hence + balanced OR, section-style topic spread.
Scaled for Class 10 board delivery (10 questions ≈ 60 marks) while keeping
reference depth — not verbatim Olympiad items from the sample PDF.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Reference metadata (20-question master paper)
REFERENCE_TOTAL_QUESTIONS = 20
REFERENCE_TOTAL_MARKS = 122
REFERENCE_DEFAULT_MARKS = 6
REFERENCE_TIME_HOURS = 3

# Board full-hard delivery defaults
FULL_HARD_DEFAULT_QUESTIONS = 10
FULL_HARD_DEFAULT_MARKS = 60
FULL_HARD_MARKS_PER_SLOT = 6
FULL_HARD_LAST_SLOT_MARKS = 8

# Difficulty tiers (prompt labels only)
TIER_HARD = "H"  # JEE Main / board stretch
TIER_VERY_HARD = "VH"  # JEE Advanced style prove+Hence chains
TIER_EXTREME = "E"  # fusion / multi-concept (board-capped wording)

# 10-slot plan mapped from reference sections A–F (compressed)
BENCHMARK_SLOTS_10: Tuple[Dict[str, Any], ...] = (
    {
        "slot": 1,
        "section": "A",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "identity_prove",
        "role": "Prove sin(A+B); Hence tan 3θ or compound-angle application",
        "stem_pattern": "(i) Prove sin(A+B)=… (ii) Hence prove/apply tan 3θ or triple-angle. (iii) Numeric Hence with given tan θ.",
        "marks": 6,
    },
    {
        "slot": 2,
        "section": "A",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "identity_prove",
        "role": "Sum-to-product / paired angles (a,b givens) → cos(A−B) and tan half-angle",
        "stem_pattern": "Given sin α+sin β and cos α+cos β; prove identities; Hence expression in a,b.",
        "marks": 6,
    },
    {
        "slot": 3,
        "section": "B",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "hots_trig",
        "role": "Trig equation — factorable or identity reduction (board level)",
        "stem_pattern": "Solve equation in [0,2π) or count solutions in interval; show key steps.",
        "marks": 6,
    },
    {
        "slot": 4,
        "section": "B",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "hots_trig",
        "role": "tan sum identity application — find sum of solutions in interval",
        "stem_pattern": "tan x + tan 2x + … = product form; sum of solutions in [0,π].",
        "marks": 6,
    },
    {
        "slot": 5,
        "section": "C",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "identity_prove",
        "role": "HOTS identity fusion — prove complex ratio; Hence evaluate at θ=π/24 etc.",
        "stem_pattern": "Prove LHS/RHS identity; Hence exact value at standard sub-multiple of π.",
        "marks": 6,
        "memory": "reuse",
    },
    {
        "slot": 6,
        "section": "C",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "ratio_find",
        "role": "Hidden condition — sin θ+cos θ or sec θ+cosec θ given; find tan θ",
        "stem_pattern": "Given combined ratio; (i) link via identity (ii) find tan θ in named quadrant.",
        "marks": 6,
    },
    {
        "slot": 7,
        "section": "D",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "quadrant_reduction",
        "role": "Reduction maze — negative/large radian or degree angle, all steps",
        "stem_pattern": "(i) Reduce to principal/acute (ii) quadrant (iii) Hence exact sin/cos/tan.",
        "marks": 6,
    },
    {
        "slot": 8,
        "section": "D",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "radian_degree",
        "role": "Degree–radian + exact surds after compound reduction (not duplicate of Q7)",
        "stem_pattern": "Express angle in radians; quadrant; Hence two exact ratios.",
        "marks": 6,
    },
    {
        "slot": 9,
        "section": "E",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "identity_prove",
        "role": "A+B+C=π style identity chain (board: tan sum or sin 2A sum)",
        "stem_pattern": "If A+B+C=π prove (i) tan identity (ii) sin 2A sum; Hence numeric evaluation.",
        "marks": 6,
    },
    {
        "slot": 10,
        "section": "F",
        "band": "L5",
        "tier": TIER_EXTREME,
        "archetype_id": "hots_trig",
        "role": "Balanced OR — both branches prove+find, 6–8 marks",
        "stem_pattern": "OR (i) prove identity + Hence exact value OR (ii) ratio set + sin 2θ evaluation.",
        "marks": 8,
        "memory": "reuse",
    },
)

BENCHMARK_PROMPT_RULES = """
TRIGONOMETRY BENCHMARK (reference: Advanced Trigonometry 20×6 marks / 122 total):
- Target depth: JEE Main–Advanced prove–Hence chains, scaled to Class 10–11 board wording.
- EVERY slot: marks 6 (last slot 8); stem has (i)(ii) and often (iii); 5+ answer steps.
- REQUIRED structures (rotate, do not clone reference PDF numbers):
  • Section A style: compound/multiple angle prove + Hence (sin(A+B), tan 3θ, paired angles).
  • Section B style: equation in an interval OR tan-sum identity with solution count.
  • Section C style: identity ratio prove + Hence evaluate at π/12, π/24, π/8 multiples only.
  • Section D style: reduction maze (negative/large radian) OR degree+radian + surds.
  • Section E style: conditional identities (A+B+C=π) with numeric Hence.
  • Section F style: balanced OR — both branches equal effort (prove+find each).
- BAN: bare one-line Find cos X°; duplicate 180°+α pair; fusion graph copy of prior paper.
- BAN: minute angles; Olympiad-only roots-of-unity unless class ≥ 11 track says otherwise.
- Hence parts depend on prior sub-parts — award marks only if chain is valid.
- Exact surds only; calculators not permitted; show method in model answer.
"""


def benchmark_slots(question_count: int) -> List[Dict[str, Any]]:
    """Return slot metadata for full-hard trigonometry (reference-aligned)."""
    n = max(1, min(question_count, len(BENCHMARK_SLOTS_10)))
    out: List[Dict[str, Any]] = []
    for i in range(n):
        base = dict(BENCHMARK_SLOTS_10[i])
        base["slot"] = i + 1
        base["one_line_ok"] = False
        base["full_hard"] = True
        base["ui_difficulty"] = "hard"
        if i == 1:
            base.setdefault("memory", "teach")
        if i == n - 1 and "memory" not in base:
            base["memory"] = "reuse"
        out.append(base)
    if question_count > len(BENCHMARK_SLOTS_10):
        for i in range(len(BENCHMARK_SLOTS_10), question_count):
            tail = dict(BENCHMARK_SLOTS_10[i % len(BENCHMARK_SLOTS_10)])
            tail["slot"] = i + 1
            tail["one_line_ok"] = False
            tail["full_hard"] = True
            out.append(tail)
    return out


def target_marks_for_slot(slot: int, question_count: int) -> int:
    """Reference mark allocation: 6 per item; last slot 8 when paper has ≥8 questions."""
    if slot == question_count and question_count >= 8:
        return FULL_HARD_LAST_SLOT_MARKS
    return FULL_HARD_MARKS_PER_SLOT


def benchmark_prompt_block() -> str:
    return BENCHMARK_PROMPT_RULES.strip()


def benchmark_calibration_lines() -> Tuple[str, ...]:
    return (
        "FULL HARD benchmark: 6 marks/item (last slot 8 if count≥8); ~60 marks for 10 questions.",
        "Match reference sections: compound angles → equations → identities → reduction → OR.",
        "Each stem: (i)(ii)(iii) or balanced OR; VH/E depth; reject ≤2-step NCERT drills.",
        "Prove–Hence chains mandatory; numeric givens in every find part.",
    )


def suggested_paper_totals(question_count: int) -> Dict[str, int]:
    """Suggested delivery totals when full_hard trigonometry is active."""
    n = question_count or FULL_HARD_DEFAULT_QUESTIONS
    marks = sum(target_marks_for_slot(s, n) for s in range(1, n + 1))
    return {
        "total_questions": n,
        "total_marks": marks,
        "marks_per_slot_default": FULL_HARD_MARKS_PER_SLOT,
    }
