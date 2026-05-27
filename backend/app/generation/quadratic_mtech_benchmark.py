"""
M.Tech-level quadratic benchmark — 100% hard UI on Class 10 syllabus.

L8–L9: existence/impossibility proofs, parameter families, construction,
recursive root transforms, boundary optimization without calculus.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

MTECH_MARKS_INTEGRATED = 6
MTECH_MARKS_MULTI = 8

BENCHMARK_PROMPT_RULES = """
M.TECH LEVEL (100% hard) — Quadratic Equations — ALL SLOTS L8–L9:
- Target 8–12 dependent reasoning steps; difficulty from hidden structure, not long arithmetic.
- BAN: bare factorisation, "find D", huge ugly numbers, procedural drills.
- REQUIRE: impossibility or iff proof, parameter family, construction, without-finding-roots,
  recurrence/power sums, multi-condition k or domain boundary, reverse-engineer or capstone.
- Hide the method: students must infer D=0, Vieta, endpoint signs, recurrence — never name it in stem.
- Marks: 6 (integrated) or 8 ((i)(ii)(iii)); model answers 8–12 steps.
- Class 10 syllabus only — no calculus, complex numbers, matrices.
- Stems: ASCII subscripts p_n only (not Unicode subscript letters).
"""

BENCHMARK_SLOTS_10: Tuple[Dict[str, Any], ...] = (
    {
        "slot": 1,
        "band": "L8",
        "archetype_id": "existence_proof",
        "role": "Prove no quadratic (or construct if possible) under contradictory Vieta/D constraints",
        "stem_format": "integrated_proof",
        "marks": 6,
    },
    {
        "slot": 2,
        "band": "L9",
        "archetype_id": "parameter_family",
        "role": "Family x² − 2kx + (k² − m) = 0 — equal roots, locus, integer conditions",
        "stem_format": "triple_part",
        "marks": 8,
    },
    {
        "slot": 3,
        "band": "L8",
        "archetype_id": "constructive_constraint",
        "role": "Construct ax²+bx+c with coefficient bounds + distinct roots + |α−β| bound",
        "stem_format": "integrated_construct",
        "marks": 6,
    },
    {
        "slot": 4,
        "band": "L9",
        "archetype_id": "recursive_roots",
        "role": "Derive p_n = s·p_{n-1} − t·p_{n-2}; hence numeric p_4; verify from roots",
        "stem_format": "hence_chain",
        "marks": 8,
    },
    {
        "slot": 5,
        "band": "L8",
        "archetype_id": "optimization_boundary",
        "role": "All k: real roots and both roots in closed interval — D plus endpoint signs",
        "stem_format": "integrated_optimize",
        "marks": 6,
    },
    {
        "slot": 6,
        "band": "L8",
        "archetype_id": "iff_impossibility",
        "role": "Prove no quadratic with listed integer/Vieta/D property exists",
        "stem_format": "integrated_proof",
        "marks": 6,
    },
    {
        "slot": 7,
        "band": "L9",
        "archetype_id": "parameter_family",
        "role": "Family x²−(k+2)x+2k=0 — equal roots, opposite signs, integer k",
        "stem_format": "triple_part",
        "marks": 8,
    },
    {
        "slot": 8,
        "band": "L8",
        "archetype_id": "reverse_engineer",
        "role": "Given D, sum, root ratio — recover monic quadratic",
        "stem_format": "integrated_construct",
        "marks": 6,
    },
    {
        "slot": 9,
        "band": "L9",
        "archetype_id": "without_roots",
        "role": "α²+β² then α³+β³ (or 1/α+1/β) without solving — Hence chain",
        "stem_format": "hence_chain",
        "marks": 8,
    },
    {
        "slot": 10,
        "band": "L9",
        "archetype_id": "multi_constraint_capstone",
        "role": "Given p_2 and p_3 for x²−sx+t — recover s, t and the equation",
        "stem_format": "triple_part",
        "marks": 8,
        "memory": "reuse",
    },
)


def benchmark_slots(question_count: int) -> List[Dict[str, Any]]:
    n = max(1, int(question_count or 10))
    out: List[Dict[str, Any]] = []
    for i in range(n):
        base = dict(BENCHMARK_SLOTS_10[i % len(BENCHMARK_SLOTS_10)])
        base["slot"] = i + 1
        base["band"] = base.get("band", "L8")
        base["one_line_ok"] = False
        base["full_hard"] = True
        base["mtech"] = True
        fmt = base.get("stem_format", "")
        base["marks"] = (
            MTECH_MARKS_MULTI
            if "triple" in fmt or "hence" in fmt
            else MTECH_MARKS_INTEGRATED
        )
        out.append(base)
    return out


def benchmark_prompt_block() -> str:
    return BENCHMARK_PROMPT_RULES.strip()


def benchmark_calibration_lines() -> Tuple[str, ...]:
    return (
        "M.TECH (100% hard): every slot L8–L9 — prove, construct, or optimize; not board drills.",
        "8+ reasoning steps; parameter families and impossibility proofs required.",
        "Marks 6–8 per item; 25–35 min thinking time per question at delivery.",
        "Syllabus lock: quadratics, Vieta, D, factorisation, formula only.",
    )


def suggested_paper_totals(question_count: int) -> Dict[str, int]:
    slots = benchmark_slots(question_count)
    marks = sum(int(s.get("marks") or 6) for s in slots)
    return {
        "total_questions": question_count,
        "total_marks": marks,
        "marks_per_slot_default": MTECH_MARKS_INTEGRATED,
    }
