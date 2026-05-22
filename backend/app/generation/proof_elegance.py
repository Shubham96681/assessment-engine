"""
Proof elegance — flag AI-structured proofs; prefer contradiction / RHS textbook voice.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


AI_PROOF_MARKERS = (
    r"\bon\s*>\s*om\b",
    r"\bn\s+inside\s+the\s+circle\b",
    r"\blies\s+inside\s+the\s+circle\b",
    r"\btherefore\s+on\s*>\s*",
    r"\bstep\s*1:\s*draw\b.*\bstep\s*2:\s*draw\b",
)

TEXTBOOK_PROOF_MARKERS = (
    "contradiction",
    "assume",
    "perpendicular",
    "rhs",
    "congruent",
    "hence",
    "therefore",
    "bisects",
)


def evaluate_proof_elegance(q: Dict[str, Any]) -> Dict[str, Any]:
    stem = (q.get("content") or "").lower()
    answer = ""
    for key in ("correct_answer", "answer"):
        v = q.get(key)
        if isinstance(v, str):
            answer += " " + v
    low = answer.lower()
    flags: List[str] = []
    score = 1.0

    if "prove" not in stem and "show that" not in stem:
        return {"proof_elegance_ok": True, "proof_elegance_score": 1.0, "proof_elegance_flags": []}

    for pat in AI_PROOF_MARKERS:
        if re.search(pat, low, re.I):
            flags.append("proof_ai_inequality_chain")
            score -= 0.35

    if re.search(r"\bperpendicular\b", stem) and "chord" in stem:
        has_contradiction = "contradiction" in low or "assume" in low
        has_standard = any(m in low for m in ("rhs", "congruent", "radius", "tangent"))
        if not has_contradiction and not has_standard:
            if re.search(r"\bon\s*>\s*om|inside\s+the\s+circle", low, re.I):
                flags.append("chord_perp_proof_non_textbook")
                score -= 0.3

    textbook_hits = sum(1 for m in TEXTBOOK_PROOF_MARKERS if m in low)
    if len(answer) > 80 and textbook_hits < 2:
        flags.append("proof_lacks_textbook_structure")
        score -= 0.2

    return {
        "proof_elegance_ok": score >= 0.62,
        "proof_elegance_score": round(max(0.0, min(1.0, score)), 3),
        "proof_elegance_flags": flags,
    }


def should_reject_proof_elegance(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
) -> bool:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return False
    if slot_band not in ("L4", "L5") and not q.get("sparse_hard"):
        return False
    report = evaluate_proof_elegance(q)
    q.update(report)
    flags = report.get("proof_elegance_flags") or []
    critical = ("proof_ai_inequality_chain", "chord_perp_proof_non_textbook")
    return any(c in flags for c in critical) and not report.get("proof_elegance_ok", True)
