"""
Rule-based hardness scoring — reject mis-labelled L5 / hard items.

Complements stem heuristics (hard_mode_calibration) and solution-graph bands.
ML layer can be added later; rules run on every question today.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.generation.cognitive_graph_validator import stem_hiddenness_score
from app.generation.solution_difficulty import score_solution_difficulty


def count_logical_steps(answer: str) -> int:
    """Count explicit deductions in model answer."""
    if not answer:
        return 0
    low = answer.lower()
    labeled = len(re.findall(r"\bstep\s*\d+", low))
    hence = low.count("hence") + low.count("therefore") + low.count("thus")
    equations = len(re.findall(r"(?:^|\n)\s*(?:step\s*\d+:|given:)", low, re.I))
    return max(labeled, hence, equations)


def requires_hidden_construction(stem: str, answer: str) -> bool:
    low = f"{stem} {answer}".lower()
    markers = (
        "hence",
        "auxiliary",
        "contradiction",
        "without naming",
        "do not name",
        "hidden",
        "disguised",
        "from question",
        "using the result",
        "it follows that",
        "suppose",
    )
    if any(m in low for m in markers):
        return True
    if re.search(r"\(i\).*\(ii\)", stem, re.I | re.S):
        return True
    if "concentric" in low and re.search(r"\bprove\b", low):
        return True
    return False


def has_reverse_reasoning(answer: str) -> bool:
    low = (answer or "").lower()
    return bool(
        re.search(r"contradiction|suppose.*perpendicular|cannot lie", low)
        or re.search(r"if.*then.*hence", low)
    )


def theorem_visibility_score(stem: str, archetype: str) -> float:
    """1.0 = theorem obvious in stem; 0.0 = path hidden."""
    hidden = stem_hiddenness_score(stem, archetype)
    return round(1.0 - hidden, 3)


def score_hardness(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
) -> Dict[str, Any]:
    stem = q.get("content") or ""
    answer = ""
    for key in ("correct_answer", "answer", "explanation"):
        v = q.get(key)
        if isinstance(v, str):
            answer += " " + v
    arch = (q.get("archetype_id") or "").strip()
    sol = score_solution_difficulty(q)
    steps = count_logical_steps(answer)
    hidden = requires_hidden_construction(stem, answer)
    reverse = has_reverse_reasoning(answer)
    visibility = theorem_visibility_score(stem, arch)
    band = sol.get("solution_band") or "L3"

    flags: List[str] = []
    ui = (ui_difficulty or "medium").lower()
    hard_slot = slot_band in ("L4", "L5") or ui in ("hard", "difficult")

    stem_low = stem.lower()
    shallow_angle = bool(
        re.search(r"tangents?\s+[A-Z]{2}", stem, re.I)
        and re.search(r"find\s+angle\s+[A-Z]O[A-Z]", stem, re.I)
        and not re.search(r"\(i\)|\(ii\)|hence|alternate|chord", stem_low)
    )

    if hard_slot and steps < 3:
        flags.append(f"insufficient_steps:{steps}<3")
    if hard_slot and not hidden and steps < 4:
        flags.append("no_hidden_construction")
    if hard_slot and visibility > 0.70:
        flags.append(f"theorem_too_visible:{visibility:.2f}>0.70")
    if hard_slot and band in ("L1", "L2", "L3"):
        flags.append(f"solution_band_too_low:{band}")
    if hard_slot and shallow_angle:
        flags.append("shallow_tangent_pair_angle_sum")

    reject = hard_slot and (
        steps < 3
        or shallow_angle
        or (visibility > 0.70 and steps < 4)
        or (not hidden and steps < 4 and band in ("L1", "L2", "L3"))
    )

    return {
        "logical_steps": steps,
        "hidden_construction": hidden,
        "reverse_reasoning": reverse,
        "theorem_visibility": visibility,
        "solution_band": band,
        "hardness_flags": flags,
        "hardness_reject": reject,
    }


def should_reject_hardness(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
) -> bool:
    if "hardness_reject" in q:
        return bool(q["hardness_reject"])
    report = score_hardness(q, slot_band=slot_band, ui_difficulty=ui_difficulty)
    q.update(report)
    return bool(report.get("hardness_reject"))
