"""
Cross-question numeric consistency — chained papers must share one geometry world.

Catches contradictions like Q1 setting r = 12 cm while Q5 claims a 5 cm tangent from OF = 17.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.generation.numeric_constraint_validator import REL_TOL, _rel_close

_CM = re.compile(r"(\d+(?:\.\d+)?)\s*cm", re.I)


@dataclass
class PaperNumericState:
    """Shared givens extracted across ordered questions."""
    centre: str = "O"
    outer_radius: Optional[float] = None
    inner_radius: Optional[float] = None
    tangent_lengths: Dict[str, float] = field(default_factory=dict)
    secant_near: Dict[str, float] = field(default_factory=dict)
    centre_distances: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "outer_radius": self.outer_radius,
            "inner_radius": self.inner_radius,
            "tangent_lengths": dict(self.tangent_lengths),
            "secant_near": dict(self.secant_near),
            "centre_distances": dict(self.centre_distances),
        }


def _text(q: Dict[str, Any]) -> str:
    return f"{q.get('content') or q.get('question') or ''} {q.get('correct_answer') or ''}"


def _first_two_radii(text: str) -> Tuple[Optional[float], Optional[float]]:
    nums = [float(m.group(1)) for m in _CM.finditer(text)]
    if "concentric" in text.lower() and len(nums) >= 2:
        a, b = nums[0], nums[1]
        return (max(a, b), min(a, b))
    m = re.search(
        r"\bouter\s+radius\s+(\d+(?:\.\d+)?)\s*cm",
        text,
        re.I,
    )
    if m:
        return float(m.group(1)), None
    m2 = re.search(
        r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm",
        text,
        re.I,
    )
    if m2:
        a, b = float(m2.group(1)), float(m2.group(2))
        return max(a, b), min(a, b)
    return None, None


def _tangent_seg_lengths(text: str) -> Dict[str, float]:
    """e.g. tangent QR = 8 cm, QR = 8 cm with tangent nearby."""
    out: Dict[str, float] = {}
    for m in re.finditer(
        r"\btangent\s+([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        text,
        re.I,
    ):
        out[m.group(1).upper()] = float(m.group(2))
    for m in re.finditer(
        r"\b([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)\s*cm\b",
        text,
        re.I,
    ):
        seg = m.group(1).upper()
        if "tangent" in text.lower() and seg not in out:
            ctx = text[max(0, m.start() - 40) : m.end() + 10].lower()
            if "tangent" in ctx:
                out[seg] = float(m.group(2))
    return out


def _secant_near(text: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for m in re.finditer(
        r"\b([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)\s*cm\b",
        text,
        re.I,
    ):
        seg = m.group(1).upper()
        ctx = text[max(0, m.start() - 50) : m.end() + 20].lower()
        if "nearer" in ctx or "secant" in ctx:
            out[seg] = float(m.group(2))
    return out


def _of_distance(text: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for m in re.finditer(
        r"\bO([A-Z])\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        text,
        re.I,
    ):
        out[m.group(1).upper()] = float(m.group(2))
    for m in re.finditer(
        r"\bpoint\s+([A-Z])\s+with\s+O\1\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        text,
        re.I,
    ):
        out[m.group(1).upper()] = float(m.group(2))
    return out


def build_paper_numeric_state(questions: List[Dict[str, Any]]) -> PaperNumericState:
    state = PaperNumericState()
    ordered = sorted(questions, key=lambda x: x.get("order_index", 0))
    for q in ordered:
        text = _text(q)
        ro, ri = _first_two_radii(text)
        if ro is not None:
            state.outer_radius = ro
        if ri is not None:
            state.inner_radius = ri
        for seg, val in _tangent_seg_lengths(text).items():
            state.tangent_lengths[seg] = val
        for seg, val in _secant_near(text).items():
            state.secant_near[seg] = val
        for pt, val in _of_distance(text).items():
            state.centre_distances[pt] = val
        m = re.search(
            r"\btangent\s+(?:from\s+point\s+)?([A-Z])\s+(?:to\s+)?(?:the\s+)?(?:outer\s+)?circle\s+has\s+length\s+(\d+(?:\.\d+)?)\s*cm",
            text,
            re.I,
        )
        if m:
            pt = m.group(1).upper()
            state.tangent_lengths[f"T_{pt}"] = float(m.group(2))
        m2 = re.search(
            r"\bfrom\s+point\s+([A-Z])\s+.*\btangent\s+.*\s+(\d+(?:\.\d+)?)\s*cm",
            text,
            re.I,
        )
        if m2:
            state.tangent_lengths[f"T_{m2.group(1).upper()}"] = float(m2.group(2))
    return state


def _expected_tangent_length(od: float, radius: float) -> float:
    if od <= radius:
        return 0.0
    return math.sqrt(od * od - radius * radius)


def validate_cross_question_consistency(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
) -> Dict[str, Any]:
    """
    Paper-level numeric chain validation.
    Attaches cross_question_flags / cross_question_ok on each question.
    """
    ch = (chapter or "").strip().lower()
    if ch != "circles" or len(questions) < 2:
        return {
            "cross_question_ok": True,
            "cross_question_score": 1.0,
            "cross_question_flags": [],
            "paper_numeric_state": {},
        }

    state = build_paper_numeric_state(questions)
    flags: List[str] = []
    ordered = sorted(questions, key=lambda x: x.get("order_index", 0))

    R = state.outer_radius
    r_in = state.inner_radius

    if R and r_in and R <= r_in:
        flags.append("concentric_outer_not_greater_than_inner")

    for i, q in enumerate(ordered):
        text = _text(q)
        slot = i + 1
        q_flags: List[str] = []

        if R and r_in:
            chord_expected = 2 * math.sqrt(max(0, R * R - r_in * r_in))
            if slot == 1 and re.search(r"\bfind\s+[A-Z]{2}\b", text, re.I):
                ans = (q.get("correct_answer") or "").lower()
                if "119" in ans or "√119" in ans or "sqrt(119)" in ans:
                    if not _rel_close(chord_expected, 2 * math.sqrt(119), 0.01):
                        q_flags.append("q1_chord_numeric_mismatch")

        if slot >= 2 and R:
            for seg, tlen in state.tangent_lengths.items():
                if len(seg) != 2:
                    continue
                contact = seg[1]
                ext = seg[0]
                od_key = ext
                od = state.centre_distances.get(od_key)
                if od is None and f"T_{ext}" in state.tangent_lengths:
                    od = math.sqrt(R * R + tlen * tlen)
                if od and tlen:
                    exp = _expected_tangent_length(od, R)
                    if exp > 0 and not _rel_close(tlen, exp, REL_TOL):
                        q_flags.append(
                            f"tangent_length_mismatch_{seg}_expected_{exp:.2f}"
                        )

        if slot >= 5 and R:
            for pt, od in state.centre_distances.items():
                for key, tlen in state.tangent_lengths.items():
                    if key == f"T_{pt}" or (len(key) == 2 and key[0] == pt):
                        exp = _expected_tangent_length(od, R)
                        if exp > 0 and not _rel_close(tlen, exp, REL_TOL):
                            q_flags.append(
                                f"q5_tangent_inconsistent_O{pt}={od}_r={R}_given={tlen}_need_sqrt_{exp:.2f}"
                            )

        if R:
            m = re.search(
                r"\bO([A-Z])\s*=\s*(\d+(?:\.\d+)?)\s*cm",
                text,
                re.I,
            )
            tlen_m = re.search(
                r"\btangent\s+(?:to\s+)?(?:the\s+)?(?:outer\s+)?circle\s+has\s+length\s+(\d+(?:\.\d+)?)\s*cm",
                text,
                re.I,
            )
            if not tlen_m:
                tlen_m = re.search(
                    r"\btangent\s+length\s+(\d+(?:\.\d+)?)\s*cm",
                    text,
                    re.I,
                )
            if m and tlen_m:
                od = float(m.group(2))
                tlen = float(tlen_m.group(1))
                exp = _expected_tangent_length(od, R)
                if exp > 0 and not _rel_close(tlen, exp, REL_TOL):
                    q_flags.append(
                        f"false_tangent_length_O{m.group(1)}={od}_r={R}_stated={tlen}_actual_sqrt={exp:.2f}"
                    )
            if m and not tlen_m and slot >= 5:
                od = float(m.group(2))
                exp = _expected_tangent_length(od, R)
                if exp > 0 and re.search(r"\bfind\s+(?:the\s+)?tangent\b", text, re.I):
                    q_flags.append(
                        f"q5_should_derive_tangent_O{m.group(1)}={od}_r={R}_expected_sqrt_{exp:.2f}"
                    )

        from app.generation.geometric_feasibility import validate_geometric_feasibility

        gf = validate_geometric_feasibility(
            q, outer_radius=R, centre_label=state.centre or "A"
        )
        if not gf.get("geometric_feasibility_ok", True):
            q_flags.extend(gf.get("geometric_feasibility_flags") or [])

        q["cross_question_flags"] = q_flags
        flags.extend(q_flags)
        q["cross_question_ok"] = len(q_flags) == 0
        q["cross_question_score"] = 1.0 if not q_flags else max(0.0, 1.0 - 0.35 * len(q_flags))

    score = max(0.0, 1.0 - 0.22 * len(flags))
    return {
        "cross_question_ok": len(flags) == 0,
        "cross_question_score": round(score, 3),
        "cross_question_flags": flags,
        "paper_numeric_state": state.as_dict(),
    }


def should_reject_cross_question_inconsistency(
    q: Dict[str, Any],
    *,
    ui_difficulty: str = "medium",
) -> bool:
    if (ui_difficulty or "").lower() not in ("hard", "difficult"):
        return False
    flags = q.get("cross_question_flags") or []
    critical = (
        "false_tangent_length",
        "q5_tangent_inconsistent",
        "tangent_length_mismatch",
        "concentric_outer_not_greater_than_inner",
        "secant_chord_exceeds_diameter",
        "answer_secant_chord_exceeds_diameter",
        "secant_near_segment_too_small",
        "external_point_inside_circle",
        "tangent_length_infeasible",
    )
    return any(any(c in f for c in critical) for f in flags)


def trim_redundant_q2_reference(stem: str) -> Tuple[str, bool]:
    """Prefer reference-only OR radii restatement, not both."""
    if not stem:
        return stem, False
    low = stem.lower()
    if "question 1" not in low:
        return stem, False
    m = re.search(
        r"(in the same concentric circles as in question 1)\s*\(\s*centre\s+O\s*,\s*radii\s+[^)]+\)\s*\.?",
        stem,
        re.I,
    )
    if m:
        new = stem[: m.start(1)] + "In the same concentric circles as in Question 1." + stem[m.end() :]
        return new.strip(), True
    return stem, False
