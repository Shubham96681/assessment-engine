"""
Arc-direction and coordinate sanity checks for Circles stems/answers.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Invented identity patterns (reject unless coordinate check passes)
_INVENTED_DIFF_SQUARES = re.compile(
    r"\bMA\s*[²2]\s*[-−]\s*MB\s*[²2]\s*=\s*(\d+(?:\.\d+)?)",
    re.I,
)


def _stem(q: Dict[str, Any]) -> str:
    return (q.get("content") or q.get("question") or "").strip()


def _answer(q: Dict[str, Any]) -> str:
    parts: List[str] = []
    for k in ("correct_answer", "answer", "explanation"):
        v = q.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts)


def validate_arc_angle_consistency(
    stem: str, answer: str
) -> Tuple[bool, List[str]]:
    """
    If stem places C on minor/major arc and asks angle ACB with central angle AOB given,
    check inscribed angle matches the arc NOT containing C.
    """
    flags: List[str] = []
    low = stem.lower()
    ans_low = answer.lower()

    arc_minor = "minor arc" in low
    arc_major = "major arc" in low
    if not (arc_minor or arc_major):
        return True, flags

    if not re.search(r"\bangle\s+ACB\b|\bangle\s+acb\b", stem, re.I):
        return True, flags

    m_apb = re.search(r"angle\s+APB\s*=\s*(\d+)", stem, re.I)
    m_aob_ans = re.search(r"angle\s+AOB\s*=\s*(\d+)", answer, re.I)
    m_acb_ans = re.search(
        r"Hence[^;]*angle\s+ACB\s*=\s*(\d+)",
        answer,
        re.I,
    )
    if not m_acb_ans:
        for m in re.finditer(r"angle\s+ACB\s*=\s*(\d+)\s*°", answer, re.I):
            m_acb_ans = m
    if not (m_apb and m_aob_ans and m_acb_ans):
        return True, flags

    apb = int(m_apb.group(1))
    aob = int(m_aob_ans.group(1))
    acb = int(m_acb_ans.group(1))

    if abs((aob + apb) - 180) > 2:
        flags.append("aob_apb_quadrilateral_mismatch")
        return False, flags

    # C on minor arc → subtends major arc → (360 - aob) / 2
    # C on major arc → subtends minor arc → aob / 2
    if arc_minor:
        expected_acb = (360 - aob) // 2
    else:
        expected_acb = aob // 2

    if abs(acb - expected_acb) > 2:
        flags.append(
            f"arc_angle_mismatch:expected_ACB_{expected_acb}_got_{acb}"
        )
        return False, flags

    return True, flags


def _verify_common_tangent_ma_mb(
    r1: float, r2: float, op: float
) -> Tuple[bool, float]:
    """
    External tangent: O=(0,0), P=(op,0), A=(0,r1), B=(op,r2).
    M = midpoint of OP. Return (identity_holds, ma2_minus_mb2).
    """
    mx, my = op / 2.0, 0.0
    ma2 = (mx - 0) ** 2 + (my - r1) ** 2
    mb2 = (mx - op) ** 2 + (my - r2) ** 2
    return True, ma2 - mb2


def validate_coordinate_identities(
    stem: str, answer: str
) -> Tuple[bool, List[str]]:
    flags: List[str] = []
    m = _INVENTED_DIFF_SQUARES.search(answer)
    if not m:
        return True, flags

    claimed = float(m.group(1))
    # Standard external tangent numeric template
    m_r = re.search(
        r"radii?\s+(\d+)\s*cm\s+and\s+(\d+)\s*cm.*OP\s*=\s*(\d+)",
        stem,
        re.I | re.S,
    )
    if not m_r:
        m_r = re.search(
            r"(\d+)\s*cm\s+and\s+(\d+)\s*cm.*OP\s*=\s*(\d+)",
            stem,
            re.I | re.S,
        )
    if m_r:
        r1, r2, op = float(m_r.group(1)), float(m_r.group(2)), float(m_r.group(3))
        _, actual = _verify_common_tangent_ma_mb(r1, r2, op)
        if abs(actual - claimed) > 0.5:
            flags.append(
                f"invented_invariant:MA2_MB2_claimed_{claimed}_coord_{actual:.2f}"
            )
            return False, flags
    else:
        flags.append("unverified_geometry_identity")
        return False, flags

    return True, flags


def validate_circle_geometry(
    q: Dict[str, Any],
    *,
    ui_difficulty: str = "medium",
) -> Dict[str, Any]:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return {"arc_geometry_ok": True, "arc_geometry_flags": []}

    stem = _stem(q)
    answer = _answer(q)
    flags: List[str] = []

    ok_arc, arc_flags = validate_arc_angle_consistency(stem, answer)
    flags.extend(arc_flags)
    ok_coord, coord_flags = validate_coordinate_identities(stem, answer)
    flags.extend(coord_flags)

    # Unclear "PC meets tangent at B" when P is external to circle
    if re.search(r"\bPC\b.*\btangent\s+at\s+B\b", stem, re.I) and re.search(
        r"\bfrom\s+.*\s+P\b.*\btangents?\s+PA\b",
        stem,
        re.I,
    ):
        flags.append("ambiguous_PC_tangent_intersection")
        ok_arc = False

    return {
        "arc_geometry_ok": ok_arc and ok_coord,
        "arc_geometry_flags": flags,
    }


def should_reject_arc_geometry(
    q: Dict[str, Any],
    *,
    ui_difficulty: str = "medium",
) -> bool:
    ui = (ui_difficulty or "medium").lower()
    if ui not in ("hard", "difficult"):
        return False
    if "arc_geometry_ok" not in q:
        q.update(validate_circle_geometry(q, ui_difficulty=ui_difficulty))
    return not q.get("arc_geometry_ok", True)
