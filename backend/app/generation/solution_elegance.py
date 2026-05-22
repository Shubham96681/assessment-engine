"""
Solution elegance — reward indirect insight and textbook voice; penalize brute-force chains.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


ELEGANCE_POSITIVE = (
    "hence",
    "therefore",
    "contradiction",
    "symmetry",
    "similar",
    "congruent",
    "without loss of generality",
    "observe that",
    "it follows",
    "RHS",
    "LHS",
    "⟂",
    "perpendicular",
    "ratio",
    "proportional",
)

BRUTE_MARKERS = (
    r"\btrial\s+and\s+error\b",
    r"\btrying\s+values\b",
    r"\bsubstitute\s+many\b",
    r"\blong\s+algebraic\s+expansion\b",
    r"\bstep\s*1:.*step\s*2:.*step\s*3:.*step\s*4:.*step\s*5:",
    r"\bcalculate\s+each\s+term\s+separately\s+for\s+all\b",
)

INDIRECT_MARKERS = (
    r"\bhence\b.*\bwithout\b",
    r"\busing\s+similarity\b",
    r"\bby\s+symmetry\b",
    r"\bcontradiction\b",
    r"\bone\s+line\s+of\s+symmetry\b",
    r"\bhidden\b",
    r"\bkey\s+observation\b",
)


def evaluate_solution_elegance(q: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score model answer elegance (0–1). Applies to computation and proof items.
    """
    answer = ""
    for key in ("correct_answer", "answer", "explanation"):
        v = q.get(key)
        if isinstance(v, str):
            answer += " " + v
    low = answer.lower().strip()
    flags: List[str] = []
    score = 0.72

    if len(low) < 40:
        return {
            "solution_elegance_ok": True,
            "solution_elegance_score": 0.75,
            "solution_elegance_flags": ["answer_too_short"],
        }

    pos_hits = sum(1 for m in ELEGANCE_POSITIVE if m.lower() in low)
    score += min(0.22, pos_hits * 0.04)

    for pat in BRUTE_MARKERS:
        if re.search(pat, low, re.I):
            flags.append("brute_force_style")
            score -= 0.2

    indirect = any(re.search(p, low, re.I) for p in INDIRECT_MARKERS)
    if indirect:
        score += 0.12
    elif pos_hits >= 3 and "step" in low:
        score += 0.06

    steps = len(re.findall(r"\bstep\s*\d+", low, re.I))
    if steps >= 6 and not indirect:
        flags.append("over_long_step_chain")
        score -= 0.15

    if re.search(r"\bprove\b", (q.get("content") or "").lower()):
        if "hence" not in low and "therefore" not in low:
            flags.append("proof_missing_hinge")
            score -= 0.12

    score = round(max(0.0, min(1.0, score)), 3)
    return {
        "solution_elegance_ok": score >= 0.58,
        "solution_elegance_score": score,
        "solution_elegance_flags": flags,
        "solution_indirect_insight": indirect,
    }


def should_reject_solution_elegance(
    q: Dict[str, Any],
    *,
    ui_difficulty: str = "medium",
    slot_band: str = "L3",
) -> bool:
    ui = (ui_difficulty or "").lower()
    if ui not in ("hard", "difficult"):
        return False
    if slot_band not in ("L4", "L5") and not q.get("sparse_hard"):
        return False
    report = evaluate_solution_elegance(q)
    q.update(report)
    return not report.get("solution_elegance_ok", True) and report.get(
        "solution_elegance_score", 1
    ) < 0.45
