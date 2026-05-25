"""
Numeric consistency validator — givens must satisfy theorems used in the item.

Catches contradictions like TA² ≠ TC·TD for tangent–secant power, or
OT/radius/tangent length mismatch.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

REL_TOL = 0.02  # 2% relative tolerance for integer cm values


def _extract_labeled_lengths(text: str) -> Dict[str, float]:
    """Map point labels or names to numeric lengths in cm (or unitless)."""
    if not text:
        return {}
    out: Dict[str, float] = {}
    blob = text.replace("×", "x").replace("·", ".")

    # TA = 9 cm, TC = 6, angle APB = 50
    for m in re.finditer(
        r"\b([A-Z]{1,3})\s*=\s*(\d+(?:\.\d+)?)\s*(?:cm|m)?\b",
        blob,
        re.I,
    ):
        key = m.group(1).upper()
        out[key] = float(m.group(2))

    for m in re.finditer(
        r"\b(?:radius|radii)\s+(?:are\s+)?(\d+(?:\.\d+)?)\s*(?:cm|and\s+(\d+(?:\.\d+)?))?",
        blob,
        re.I,
    ):
        out["R_outer"] = float(m.group(1))
        if m.group(2):
            out["R_inner"] = float(m.group(2))

    for m in re.finditer(
        r"\bradius\s+(?:is\s+)?(\d+(?:\.\d+)?)\s*cm",
        blob,
        re.I,
    ):
        out["radius"] = float(m.group(1))

    for m in re.finditer(
        r"\bOT\s*=\s*(\d+(?:\.\d+)?)",
        blob,
        re.I,
    ):
        out["OT"] = float(m.group(1))

    for m in re.finditer(
        r"\bOP\s*=\s*(\d+(?:\.\d+)?)",
        blob,
        re.I,
    ):
        out["OP"] = float(m.group(1))

    for m in re.finditer(
        r"\bOQ\s*=\s*(\d+(?:\.\d+)?)",
        blob,
        re.I,
    ):
        out["OQ"] = float(m.group(1))

    return out


def _rel_close(a: float, b: float, tol: float = REL_TOL) -> bool:
    if a == 0 and b == 0:
        return True
    denom = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / denom <= tol


def _detect_theorem_targets(stem: str, answer: str) -> List[str]:
    low = f"{stem} {answer}".lower()
    targets: List[str] = []
    if re.search(r"ta\s*\^?\s*2\s*=\s*tc\s*[\.\·x\*]\s*td|tc\s*[\.\·x\*]\s*td|tangent.?secant|power of a point", low):
        targets.append("tangent_secant")
    if re.search(r"show that ta\^2|verify that ta\^2|ta\^2\s*=\s*tc", low):
        targets.append("tangent_secant")
    if re.search(r"\bop\s*=\s*\d.*\boq\s*=\s*\d.*\bfind\s+pq\b", low, re.I):
        targets.append("tangent_pythagoras")
    if re.search(r"\bfind\s+pq\b", low) and "tangent" in low and "op" in low:
        targets.append("tangent_pythagoras")
    if re.search(r"concentric|radii\s+\d.*\d.*chord", low):
        targets.append("concentric_chord")
    if re.search(r"ot\s*=\s*\d.*radius\s*=\s*\d|ta\^2\s*=\s*ot\^2", low):
        targets.append("tangent_length_ot")
    if re.search(r"angle\s+apb.*angle\s+aob|quadrilateral\s+oapb", low, re.I):
        targets.append("tangent_angle_quad")
    return targets


def _validate_tangent_secant(
    lengths: Dict[str, float], flags: List[str]
) -> bool:
    ta = lengths.get("TA")
    tc = lengths.get("TC")
    td = lengths.get("TD")
    if ta is None or tc is None or td is None:
        return True
    lhs = ta * ta
    rhs = tc * td
    if not _rel_close(lhs, rhs):
        flags.append(f"tangent_secant_mismatch:TA^2={lhs:.2f},TC*TD={rhs:.2f}")
        return False
    return True


def _validate_tangent_pythagoras(
    lengths: Dict[str, float], flags: List[str]
) -> bool:
    op = lengths.get("OP")
    oq = lengths.get("OQ")
    if op is None or oq is None:
        return True
    if oq <= op:
        flags.append(f"tangent_pythagoras_unsolvable:OQ={oq}<=OP={op}")
        return False
    return True


def _validate_concentric_chord(
    lengths: Dict[str, float], flags: List[str]
) -> bool:
    r_outer = lengths.get("R_outer")
    r_inner = lengths.get("R_inner")
    if r_outer is None or r_inner is None:
        return True
    if r_outer <= r_inner:
        flags.append(f"concentric_invalid_radii:{r_outer}<={r_inner}")
        return False
    return True


def _validate_tangent_length_ot(
    lengths: Dict[str, float], flags: List[str]
) -> bool:
    ot = lengths.get("OT")
    r = lengths.get("radius")
    ta = lengths.get("TA")
    if ot is None or r is None:
        return True
    expected = math.sqrt(max(0, ot * ot - r * r))
    if ta is not None and not _rel_close(ta, expected):
        flags.append(
            f"tangent_length_mismatch:TA={ta:.2f},expected_sqrt(OT^2-r^2)={expected:.2f}"
        )
        return False
    return True


def _validate_tangent_angle_quad(
    stem: str, lengths: Dict[str, float], flags: List[str]
) -> bool:
    m_apb = re.search(r"angle\s+apb\s*=\s*(\d+)", stem, re.I)
    m_aob = re.search(r"angle\s+aob\s*=\s*(\d+)", stem, re.I)
    if not m_apb:
        return True
    apb = float(m_apb.group(1))
    if m_aob:
        aob = float(m_aob.group(1))
        if not _rel_close(apb + aob, 180.0, tol=0.01):
            flags.append(f"tangent_angle_quad_mismatch:APB+AOB={apb+aob},expected_180")
            return False
    return True


def validate_numeric_constraints(q: Dict[str, Any]) -> Dict[str, Any]:
    stem = (q.get("content") or "").strip()
    answer = ""
    for key in ("correct_answer", "answer", "explanation"):
        v = q.get(key)
        if isinstance(v, str):
            answer += " " + v

    # Givens come from the stem; answer may contain computed products (e.g. TC.TD = 90)
    lengths = _extract_labeled_lengths(stem)
    if not lengths.get("TA") and not lengths.get("TC"):
        lengths.update(_extract_labeled_lengths(answer))
    flags: List[str] = []
    ok = True

    from app.generation.geometric_feasibility import validate_geometric_feasibility

    gf = validate_geometric_feasibility(q)
    if not gf.get("geometric_feasibility_ok", True):
        flags.extend(gf.get("geometric_feasibility_flags") or [])
        ok = False

    for theorem in _detect_theorem_targets(stem, answer):
        if theorem == "tangent_secant":
            ok = _validate_tangent_secant(lengths, flags) and ok
        elif theorem == "tangent_pythagoras":
            ok = _validate_tangent_pythagoras(lengths, flags) and ok
        elif theorem == "concentric_chord":
            ok = _validate_concentric_chord(lengths, flags) and ok
        elif theorem == "tangent_length_ot":
            ok = _validate_tangent_length_ot(lengths, flags) and ok
        elif theorem == "tangent_angle_quad":
            ok = _validate_tangent_angle_quad(stem, lengths, flags) and ok

    # Answer text claiming equality when numbers contradict
    if re.search(r"hence the relation holds|relation holds", answer, re.I):
        if any("mismatch" in f for f in flags):
            flags.append("answer_claims_valid_but_numbers_contradict")
            ok = False

    score = 1.0 if ok else max(0.0, 0.35 - 0.1 * len(flags))
    return {
        "numeric_consistency_ok": ok,
        "numeric_consistency_score": round(score, 3),
        "numeric_flags": flags,
        "numeric_lengths": lengths,
    }


def should_reject_numeric(q: Dict[str, Any]) -> bool:
    if "numeric_consistency_ok" not in q:
        q.update(validate_numeric_constraints(q))
    if not q.get("numeric_consistency_ok", True):
        return True
    flags = q.get("numeric_flags") or []
    critical = (
        "tangent_secant_mismatch",
        "answer_claims_valid_but_numbers_contradict",
        "secant_chord_exceeds_diameter",
        "answer_secant_chord_exceeds_diameter",
        "secant_near_segment_too_small",
    )
    return any(any(c in f for c in critical) for f in flags)


def numeric_prompt_block(chapter: str = "generic") -> str:
    from app.generation.chapter_prompt_isolation import numeric_prompt_block as _chapter_block

    return _chapter_block(chapter) or (
        "NUMERIC CONSISTENCY: every Find/Show/Verify must use values consistent with the chapter."
    )
