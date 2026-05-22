"""
Solution-graph difficulty — score from answer structure, not stem length.
"""
from __future__ import annotations

import re
from typing import Dict, Any


THEOREM_MARKERS = (
    "perpendicular",
    "tangent",
    "pythagoras",
    "congruence",
    "rhs",
    "sss",
    "similar",
    "similarity",
    "cyclic",
    "quadrilateral",
    "angle sum",
    "equal tangents",
    "secant",
    "concentric",
    "auxiliary",
    "opposite angles",
    "supplementary",
)

FUSION_MARKERS = (
    "quadrilateral",
    "cyclic",
    "similar",
    "congruence",
    "angle at",
    "hence angle",
    "step 2",
    "step 3",
    "step 4",
)

HIDDEN_STEP_MARKERS = (
    "step 1",
    "step 2",
    "step 3",
    "hence",
    "therefore",
    "thus",
    "we get",
    "it follows",
)

BRANCH_MARKERS = (" or ", "\nor\n", "(i)", "(ii)", "(iii)", "alternatively")


def score_solution_difficulty(q: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns metrics + solution_difficulty (0–1) and inferred band L1–L5.
    """
    answer = ""
    for key in ("correct_answer", "answer", "explanation"):
        val = q.get(key)
        if isinstance(val, str) and val.strip():
            answer += " " + val.strip()
    lower = answer.lower()

    theorem_count = sum(1 for m in THEOREM_MARKERS if m in lower)
    fusion_count = sum(1 for m in FUSION_MARKERS if m in lower)
    hidden_steps = len(re.findall(r"\bstep\s*\d+", lower)) + lower.count("hence")
    dependency_depth = min(
        5,
        theorem_count
        + (1 if "prove" in lower else 0)
        + (1 if fusion_count >= 2 else 0)
        + (1 if hidden_steps >= 3 else 0),
    )
    algebraic = len(re.findall(r"[=^²√]|\b\d+\s*cm\b", answer))
    has_branch = any(m in lower for m in BRANCH_MARKERS)
    proof_chain = hidden_steps >= 3 or (theorem_count >= 2 and "hence" in lower)

    raw = (
        theorem_count * 0.14
        + fusion_count * 0.1
        + min(hidden_steps, 8) * 0.09
        + dependency_depth * 0.14
        + min(algebraic, 5) * 0.04
        + (0.12 if has_branch else 0)
        + (0.1 if proof_chain else 0)
    )
    solution_difficulty = max(0.0, min(1.0, raw))

    if solution_difficulty < 0.22:
        band = "L1"
    elif solution_difficulty < 0.38:
        band = "L2"
    elif solution_difficulty < 0.52:
        band = "L3"
    elif solution_difficulty < 0.68:
        band = "L4"
    else:
        band = "L5"

    return {
        "solution_difficulty": round(solution_difficulty, 3),
        "solution_band": band,
        "theorem_count": theorem_count,
        "hidden_steps": hidden_steps,
        "dependency_depth": dependency_depth,
        "algebraic_resolution": algebraic,
        "has_branch": has_branch,
        "fusion_count": fusion_count,
        "proof_chain": proof_chain,
    }
