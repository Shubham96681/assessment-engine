"""
Hardest trigonometry benchmark — 20 Hardest Trigonometry Questions (122 marks, 3 h).

Reference sections:
  A Q1–4  Compound & multiple angles
  B Q5–8  Equations & general solutions
  C Q9–12 Identities & algebraic manipulation
  D Q13–15 Inverse trigonometry
  E Q16–18 Triangle properties
  F Q19–20 Advanced reduction & optimization

Papers with n<20 sample slots across sections (see REF_MAP_5, REF_MAP_10).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

REFERENCE_TOTAL_QUESTIONS = 20
REFERENCE_TOTAL_MARKS = 122
REFERENCE_TIME_HOURS = 3
REFERENCE_PASS_MARKS = 45
REFERENCE_DISTINCTION_MARKS = 85

FULL_HARD_DEFAULT_QUESTIONS = 10
FULL_HARD_MARKS_PER_SLOT = 6
FULL_HARD_LAST_SLOT_MARKS = 8

# Reference paper: Q1–Q19 = 6 marks, Q20 = 8 marks
REFERENCE_MARKS_20: Tuple[int, ...] = (6,) * 19 + (8,)

# Scaled 10-slot paper (~62 marks): one item per section band + capstone
REF_MAP_10: Tuple[int, ...] = (1, 3, 5, 7, 9, 12, 14, 17, 19, 20)

# 5-slot paper: compound → equation → identity → inverse → optimization
REF_MAP_5: Tuple[int, ...] = (1, 5, 9, 13, 20)

TIER_HARD = "H"
TIER_VERY_HARD = "VH"
TIER_EXTREME = "E"

# ── 20 reference slots (invent NEW numbers each generation) ──────────────────
BENCHMARK_SLOTS_20: Tuple[Dict[str, Any], ...] = (
    {
        "slot": 1,
        "section": "A",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "identity_prove",
        "role": "Prove sin(A+B) for acute A,B; Hence tan 3θ; numeric tan 3θ and sin(π/4+3θ)",
        "stem_format": "prove_hence_iii",
        "marks": 6,
        "skill": "C-P",
    },
    {
        "slot": 2,
        "section": "A",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "identity_prove",
        "role": "Given sin α+sin β=a, cos α+cos β=b; prove cos(α−β) and tan((α+β)/2); Hence cos2α+cos2β+2cos(α+β)",
        "stem_format": "prove_hence_iii",
        "marks": 6,
        "skill": "I-P",
    },
    {
        "slot": 3,
        "section": "A",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "hots_trig",
        "role": "Prove sin θ/sin 7θ as polynomial in sin²θ; Hence roots of cubic in sin²(π/7), sin²(2π/7), sin²(3π/7)",
        "stem_format": "prove_hence_ii",
        "marks": 6,
        "skill": "M-A",
    },
    {
        "slot": 4,
        "section": "A",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "identity_prove",
        "role": "A+B+C=π: prove tan sum and sin 2A sum; Hence evaluate tan 20°+tan 40°+tan 60°+tan 80°",
        "stem_format": "prove_hence_iii",
        "marks": 6,
        "skill": "C-I",
        "memory": "reuse",
    },
    {
        "slot": 5,
        "section": "B",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "hots_trig",
        "role": "General solution: sin³x+sin³2x+sin³3x=(sinx+sin2x+sin3x)³; count in [0,2π]",
        "stem_format": "equation_solve",
        "marks": 6,
        "skill": "T-E",
    },
    {
        "slot": 6,
        "section": "B",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "hots_trig",
        "role": "Solve tan x+tan 2x+tan 3x=tan x tan 2x tan 3x; sum of solutions in [0,π]",
        "stem_format": "equation_solve",
        "marks": 6,
        "skill": "T-E",
    },
    {
        "slot": 7,
        "section": "B",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "hots_trig",
        "role": "General solution sin⁴x+cos⁴x=k; count solutions in [−2π,2π]",
        "stem_format": "equation_solve",
        "marks": 6,
        "skill": "T-E",
    },
    {
        "slot": 8,
        "section": "B",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "hots_trig",
        "role": "Solve (cos x+cos 3x+…)/(sin x+sin 3x+…)=tan 4x on [0,2π] with verification",
        "stem_format": "prove_hence_ii",
        "marks": 6,
        "skill": "T-E",
    },
    {
        "slot": 9,
        "section": "C",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "identity_prove",
        "role": "Prove complex trig fraction identity equals tan 2θ; evaluate at θ=π/24",
        "stem_format": "prove_hence_ii",
        "marks": 6,
        "skill": "I-P",
    },
    {
        "slot": 10,
        "section": "C",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "hots_trig",
        "role": "a=cos α+i sin α, a+b+c=0: prove cos/sin sums and cos 2α, cos 3α relations",
        "stem_format": "prove_hence_iii",
        "marks": 6,
        "skill": "I-P",
    },
    {
        "slot": 11,
        "section": "C",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "identity_prove",
        "role": "Prove product (1+cos(kπ/8)) four terms = 1/8",
        "stem_format": "prove_only",
        "marks": 6,
        "skill": "I-P",
    },
    {
        "slot": 12,
        "section": "C",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "hots_trig",
        "role": "sin⁻¹x+sin⁻¹y+sin⁻¹z=π: prove x/√(1−x²)+… = 2xyz",
        "stem_format": "prove_only",
        "marks": 6,
        "skill": "I-T",
    },
    {
        "slot": 13,
        "section": "D",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "hots_trig",
        "role": "Prove tan⁻¹(1/2)+tan⁻¹(1/5)+tan⁻¹(1/8)=π/4; Hence longer tan⁻¹ sum",
        "stem_format": "prove_hence_ii",
        "marks": 6,
        "skill": "I-T",
    },
    {
        "slot": 14,
        "section": "D",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "hots_trig",
        "role": "Solve sin⁻¹x+sin⁻¹(1−x)=cos⁻¹x for all real x",
        "stem_format": "equation_solve",
        "marks": 6,
        "skill": "I-T",
    },
    {
        "slot": 15,
        "section": "D",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "identity_prove",
        "role": "Prove sin⁻¹ identity; Hence cos⁻¹ sum",
        "stem_format": "prove_hence_ii",
        "marks": 6,
        "skill": "I-T",
    },
    {
        "slot": 16,
        "section": "E",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "identity_prove",
        "role": "Triangle: prove c²/(a²−b²)=sin(A+B)/sin(A−B); Hence cot A,cot B,cot C in A.P. when sides² in A.P.",
        "stem_format": "prove_hence_ii",
        "marks": 6,
        "skill": "T-P",
    },
    {
        "slot": 17,
        "section": "E",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "identity_prove",
        "role": "If cos A+cos B+cos C=k, prove triangle equilateral (given k=2/3 style)",
        "stem_format": "prove_only",
        "marks": 6,
        "skill": "T-P",
    },
    {
        "slot": 18,
        "section": "E",
        "band": "L5",
        "tier": TIER_HARD,
        "archetype_id": "hots_trig",
        "role": "Prove cos A+cos B+cos C=1+r/R; Hence maximum of cos sum",
        "stem_format": "prove_hence_ii",
        "marks": 6,
        "skill": "O-E",
    },
    {
        "slot": 19,
        "section": "F",
        "band": "L5",
        "tier": TIER_VERY_HARD,
        "archetype_id": "standard_angle",
        "role": "Evaluate sin²(π/8)+sin²(3π/8)+sin²(5π/8)+sin²(7π/8); Hence Σ sin²(kπ/(2n+1))",
        "stem_format": "prove_hence_ii",
        "marks": 6,
        "skill": "S-S",
    },
    {
        "slot": 20,
        "section": "F",
        "band": "L5",
        "tier": TIER_EXTREME,
        "archetype_id": "hots_trig",
        "role": "f(x)=sin⁶x+cos⁶x: prove form, max/min, period, solve f(x)=k and sum solutions in [0,2π]",
        "stem_format": "balanced_or",
        "marks": 8,
        "skill": "O-E",
        "memory": "reuse",
    },
)

BENCHMARK_PROMPT_RULES = """
20 HARDEST TRIGONOMETRY QUESTIONS (full-hard calibration — mandatory depth):
Reference: 20 questions, 122 marks, 3 hours (Sections A–F). Passing ~45; distinction ~85+.

SECTION PROGRESSION (invent NEW numbers/labels — do not copy reference stems verbatim):
  A (Q1–4): Compound/multiple angles — geometric sin(A+B), parameter (a,b), sin nθ ratio, A+B+C=π.
  B (Q5–8): Equations — cubed sine sums, tan product chains, sin⁴+cos⁴, grouped cos/sin ratio = tan 4x.
  C (Q9–12): Identity fusion — fraction prove+evaluate, complex a+b+c=0, cos product at π/8, inverse sum identity.
  D (Q13–15): Inverse trig — tan⁻¹ telescoping, sin⁻¹ equation, sin⁻¹/cos⁻¹ prove chains.
  E (Q16–18): Triangle properties — sine rule manipulation, equilateral condition, R and r relation.
  F (Q19–20): sin² sums at π/8 family; capstone f(x)=sin⁶x+cos⁶x with max/min/period/solve (8 marks).

Q19 GOLD STANDARD (Section F — mandatory pattern for series slots; invent new angles):
  "Evaluate exactly: sin²(π/8)+sin²(3π/8)+sin²(5π/8)+sin²(7π/8).
   Hence find the exact value of Σ_{k=1}^{n} sin²(kπ/(2n+1))."
  Answer: complementary/supplementary pairing → sin² θ identity → sum = 3/2 for n=4;
  general sum = (2n+1)/4. NOT a one-line Find sin X° item.

DIFFICULTY MIX (reference): ~60% Hard (JEE Main), ~40% Very Hard (JEE Advanced).
COGNITIVE DEMANDS: multi-step proof (4+ steps), Hence chains, factorization, pattern in series, optimization.

STEM RULES:
  • Most slots 6 marks; capstone slot 8 marks with (i)(ii)(iii)(iv) or balanced OR.
  • (i)(ii)(iii) on fusion slots; max ~40% of paper with triple parts — vary prove-only and sparse stems.
  • 5+ answer steps minimum; 6–10 on equation/general-solution slots.
  • Exact values with square roots allowed; ban bare Find cos N° one-liners.
  • BAN word "surd" in stems if user prefers — use "exact form" or "simplest radical form".
  • Self-contained stems; theorems named only in model answers.

BANS: minute angles; copying π/7, π/11, 20°+40°+60°+80° every paper; circle/secant vocabulary.
"""


def _reference_index(paper_slot: int, question_count: int) -> int:
    """0-based index into BENCHMARK_SLOTS_20."""
    if question_count >= 20:
        return min(paper_slot - 1, len(BENCHMARK_SLOTS_20) - 1)
    if question_count == 10:
        return REF_MAP_10[paper_slot - 1] - 1
    if question_count == 5:
        return REF_MAP_5[paper_slot - 1] - 1
    # Spread across 20 for other counts
    return min(
        (paper_slot - 1) * len(BENCHMARK_SLOTS_20) // max(1, question_count),
        len(BENCHMARK_SLOTS_20) - 1,
    )


def benchmark_slots(question_count: int) -> List[Dict[str, Any]]:
    n = max(1, question_count)
    out: List[Dict[str, Any]] = []
    for i in range(n):
        ref_idx = _reference_index(i + 1, n)
        base = dict(BENCHMARK_SLOTS_20[ref_idx])
        base["slot"] = i + 1
        base["ref_slot"] = ref_idx + 1
        base["one_line_ok"] = False
        base["full_hard"] = True
        base["ui_difficulty"] = "hard"
        if n == 20:
            base["marks"] = REFERENCE_MARKS_20[i]
        elif i == n - 1 and n >= 5:
            base["marks"] = FULL_HARD_LAST_SLOT_MARKS
        else:
            base["marks"] = FULL_HARD_MARKS_PER_SLOT
        if i == 1:
            base.setdefault("memory", "teach")
        if i == n - 1:
            base["memory"] = "reuse"
        out.append(base)
    return out


def target_marks_for_slot(slot: int, question_count: int) -> int:
    slots = benchmark_slots(question_count)
    idx = slot - 1
    if 0 <= idx < len(slots):
        return int(slots[idx].get("marks") or FULL_HARD_MARKS_PER_SLOT)
    return FULL_HARD_MARKS_PER_SLOT


def benchmark_prompt_block() -> str:
    return BENCHMARK_PROMPT_RULES.strip()


def benchmark_calibration_lines() -> Tuple[str, ...]:
    return (
        "EXTREME TRIG: calibrate to 20 Hardest Trigonometry Questions (122 marks, 3 h, Sections A–F).",
        "60% JEE Main depth (prove+Hence, compound angles); 40% JEE Advanced (general solution, inverse, optimization).",
        "Reject flat NCERT drill: bare Find cos N°, one-step recall, identical (i)(ii)(iii) on every slot.",
        "Require: equation/general-solution slot, inverse slot, triangle slot, sin²-sum or f(x) capstone.",
    )


def suggested_paper_totals(question_count: int) -> Dict[str, Any]:
    n = question_count or FULL_HARD_DEFAULT_QUESTIONS
    marks = sum(target_marks_for_slot(s, n) for s in range(1, n + 1))
    return {
        "total_questions": n,
        "total_marks": marks,
        "marks_per_slot_default": FULL_HARD_MARKS_PER_SLOT,
        "reference_total_questions": REFERENCE_TOTAL_QUESTIONS,
        "reference_total_marks": REFERENCE_TOTAL_MARKS,
        "reference_time_hours": REFERENCE_TIME_HOURS,
        "sections": ["A", "B", "C", "D", "E", "F"],
    }


# Back-compat alias for tests importing old name
FULL_HARD_MARKS_SCHEDULE_10: Tuple[int, ...] = tuple(
    target_marks_for_slot(i, 10) for i in range(1, 11)
)
BENCHMARK_SLOTS_10: Tuple[Dict[str, Any], ...] = tuple(benchmark_slots(10))
