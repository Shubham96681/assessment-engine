"""
SymPy truth checks for trigonometry stems and model answers (Paper 8 failure modes).

Rejects contradictions, false identities, inconsistent (sin, cos) pairs,
impossible triangle data, and numerically false formulas before display.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.sympy_math_text import sympy_available

# --- Patterns ---
_QUADRANT = re.compile(
    r"quadrant\s*(IV|III|II|I|VI|IX|X|first|second|third|fourth|1st|2nd|3rd|4th|[1-4])\b",
    re.I,
)
_TAN_THETA_VAL = re.compile(
    r"\btan\s*θ\s*=\s*(-?\s*(?:√\s*)?\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)",
    re.I,
)
_SIN_COS_THETA_CLAIM = re.compile(
    r"\bsin\s*θ\s*cos\s*θ\s*=\s*(-?\s*(?:√\s*)?\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)",
    re.I,
)
_FIND_TAN_A_GIVEN_TAN_A = re.compile(
    r"\bfind\s+(?:the\s+value\s+of\s+)?tan\s*A\b[^.]{0,80}?\bgiven\s+tan\s*A\s*=",
    re.I,
)
_FALSE_TAN_PRODUCT_ID = re.compile(
    r"\btan\s*A\s*tan\s*B\s*=\s*"
    r"\(\s*tan\s*A\s*\+\s*tan\s*B\s*\)\s*/\s*\(\s*tan\s*A\s*-\s*tan\s*B\s*\)",
    re.I,
)
_COS_AB_VAL = re.compile(
    r"\bcos\s*\(\s*A\s*\+\s*B\s*\)\s*=\s*(-?\s*(?:√\s*)?\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?)",
    re.I,
)
_SIN_AB_VAL = re.compile(
    r"\bsin\s*\(\s*A\s*\+\s*B\s*\)\s*=\s*(-?\s*(?:√\s*)?\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?)",
    re.I,
)
_TAN_A_VAL = re.compile(r"\btan\s*A\s*=\s*(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)", re.I)
_TAN_B_VAL = re.compile(r"\btan\s*B\s*=\s*(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)", re.I)
_TAN_C_VAL = re.compile(r"\btan\s*C\s*=\s*(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)", re.I)
_ANGLE_A_RIGHT = re.compile(
    r"(?:∠|angle)\s*A\s*=\s*(?:π\s*/\s*2|90\s*°|90°|right\s*angle)",
    re.I,
)
_FIND_TAN_A = re.compile(r"\bfind\s+(?:the\s+value\s+of\s+)?tan\s*A\b", re.I)
_TRIANGLE_CTX = re.compile(
    r"\btriangle\s*ABC\b|(?:Δ|\u2206)\s*ABC|(?:∠|\u2220)\s*A\s*=\s*\d",
    re.I,
)
_TAN_90_USED = re.compile(r"\btan\s*\(\s*90\s*\)|\btan\s*90\s*°", re.I)
_SIN_90_DIV_COS60 = re.compile(
    r"\bsin\s*\(\s*90\s*\)\s*=\s*\([^)]{5,}\)\s*/\s*cos\s*60",
    re.I,
)
_TRIVIAL_TAN_5 = re.compile(
    r"\btan\s*\(\s*5\s*θ\s*\)\s*=\s*tan\s*\(\s*2\s*θ\s*\+\s*3\s*θ\s*\)",
    re.I,
)
_SIN_5_FORMULA = re.compile(
    r"\bsin\s*\(\s*5\s*θ\s*\)\s*=\s*16\s*sin\s*θ\s*cos\s*θ\s*"
    r"\(\s*1\s*-\s*10\s*sin\s*[²2]\s*θ\s*cos\s*[²2]\s*θ\s*\)",
    re.I,
)
_TAN_AB_VAL = re.compile(
    r"\btan\s*\(\s*A\s*\+\s*B\s*\)\s*=\s*(-?\s*(?:√\s*)?\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?)",
    re.I,
)
_TAN_SUM_AB = re.compile(
    r"\btan\s*A\s*\+\s*tan\s*B\s*=\s*(-?\s*(?:\d+\s*)?√?\s*\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)",
    re.I,
)
_TAN_PROD_AB = re.compile(
    r"\btan\s*A\s*tan\s*B\s*=\s*(-?\s*\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)",
    re.I,
)
_COS_AB_EXPAND = re.compile(
    r"\bcos\s*A\s*cos\s*B\s*[-−]\s*sin\s*A\s*sin\s*B\s*=\s*"
    r"(-?\s*(?:√\s*)?\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?)",
    re.I,
)
_FALSE_COS_SUM_3 = re.compile(
    r"\bcos\s*\(\s*A\s*\+\s*B\s*\+\s*C\s*\)\s*=\s*"
    r"cos\s*A\s*cos\s*B\s*cos\s*C\s*\+\s*sin\s*A\s*sin\s*B\s*sin\s*C\b",
    re.I,
)
_ANGLE_A_30 = re.compile(
    r"(?:∠|\u2220|angle)\s*A\s*=\s*30\s*(?:°|\u00b0)|"
    r"30\s*(?:°|\u00b0)\s*,?\s*(?:∠|\u2220|angle)\s*C\s*=\s*60",
    re.I,
)
_ANGLE_C_60 = re.compile(r"(?:∠|\u2220|angle)\s*C\s*=\s*60\s*(?:°|\u00b0)", re.I)
_SIN_AC_VAL = re.compile(
    r"\bsin\s*\(\s*A\s*\+\s*C\s*\)\s*=\s*(-?\s*(?:√\s*)?\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)",
    re.I,
)
_SIN_AC_WRONG_2 = re.compile(
    r"\bsin\s*\(\s*A\s*\+\s*C\s*\)\s*=\s*2\b|sin\s*\(\s*90\s*°\s*\)\s*=\s*2",
    re.I,
)
_TAN_SUM_90 = re.compile(
    r"\btan\s*\(\s*A\s*\+\s*B\s*\).{0,120}?(?:90\s*°|π\s*/\s*2)",
    re.I,
)
_FRAC_PAIR = re.compile(
    r"\b(sin|cos)\s*\(\s*A\s*\+\s*B\s*\)\s*=\s*"
    r"(-?\s*(?:√\s*)?\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?)",
    re.I,
)


def _parse_sqrt_expr(s: str) -> Optional[Any]:
    """Parse 4√7, √3, 4*sqrt(7), fractions."""
    if not sympy_available():
        return None
    from sympy import Rational, sqrt

    t = (s or "").strip().replace("−", "-").replace(" ", "")
    neg = t.startswith("-")
    if neg:
        t = t[1:]
    m = re.match(r"(?:(\d+))?(?:√|sqrt)(\d+(?:\.\d+)?)", t, re.I)
    if m:
        coef = Rational(m.group(1) or "1")
        val = sqrt(Rational(m.group(2)))
        out = coef * val
        return -out if neg else out
    return _parse_rational_expr(s)


def _parse_rational_expr(s: str) -> Optional[Any]:
    """Parse a/b, √n/m, -√10/3 into SymPy Rational or expression."""
    if not sympy_available():
        return None
    from sympy import Rational, sqrt

    s = (s or "").strip().replace("−", "-").replace(" ", "")
    if not s:
        return None
    neg = s.startswith("-")
    if neg:
        s = s[1:].lstrip()
    sqrt_part = False
    if s.startswith("√") or s.startswith("sqrt"):
        sqrt_part = True
        s = re.sub(r"^√|^sqrt", "", s, flags=re.I)
    m = re.match(r"(\d+(?:\.\d+)?)(?:/(\d+(?:\.\d+)?))?", s)
    if not m:
        return None
    num = m.group(1)
    den = m.group(2) or "1"
    try:
        if sqrt_part:
            val = sqrt(Rational(num)) / Rational(den)
        else:
            val = Rational(num) / Rational(den)
        return -val if neg else val
    except Exception:
        return None


def _quadrant_signs(qname: str) -> Tuple[int, int, int]:
    """Expected signs (sin, cos, tan): QI(+,+,+), QII(+,-,-), QIII(-,-,+), QIV(-,+,-)."""
    q = (qname or "").upper().replace(" ", "")
    if q in ("II", "2", "2ND", "SECOND"):
        return (1, -1, -1)
    if q in ("III", "3", "THIRD", "3RD"):
        return (-1, -1, 1)
    if q in ("IV", "4", "FOURTH", "4TH"):
        return (-1, 1, -1)
    return (1, 1, 1)


def _check_quadrant_tan_consistency(text: str) -> Optional[str]:
    qm = _QUADRANT.search(text)
    tm = _TAN_THETA_VAL.search(text)
    if not qm or not tm:
        # Explicit "quadrant IV" + tan θ = positive surd
        if re.search(r"quadrant\s*IV\b", text, re.I) and tm:
            tval = _parse_sqrt_expr(tm.group(1).replace("√", "sqrt"))
            if tval is None:
                tval = _parse_rational_expr(tm.group(1).replace("√", "sqrt"))
            if tval is not None:
                from sympy import N

                if float(N(tval)) > 0:
                    return "quadrant_tan_sign_contradiction"
        return None
    tval = _parse_sqrt_expr(tm.group(1).replace("√", "sqrt"))
    if tval is None:
        tval = _parse_rational_expr(tm.group(1).replace("√", "sqrt"))
    if tval is None:
        return None
    from sympy import N

    _, _, tan_sign = _quadrant_signs(qm.group(1))
    if float(N(tval)) * tan_sign < 0:
        return "quadrant_tan_sign_contradiction"
    return None


def _check_sin_cos_from_tan(text: str) -> Optional[str]:
    tm = _TAN_THETA_VAL.search(text)
    sm = _SIN_COS_THETA_CLAIM.search(text)
    if not tm or not sm:
        return None
    tval = _parse_rational_expr(tm.group(1).replace("√", "sqrt"))
    claimed = _parse_rational_expr(sm.group(1).replace("√", "sqrt"))
    if tval is None or claimed is None:
        return None
    from sympy import N, simplify

    # sin θ cos θ = tan θ / (1 + tan²θ)
    actual = simplify(tval / (1 + tval**2))
    if abs(float(N(actual - claimed))) > 0.02:
        return "sin_cos_theta_value_inconsistent"
    return None


def _check_self_referential_tan_a(text: str) -> Optional[str]:
    if _FIND_TAN_A_GIVEN_TAN_A.search(text):
        return "self_referential_find_tan_a"
    return None


def _check_false_tan_product_identity(text: str) -> Optional[str]:
    """tan A tan B = (tan A+tan B)/(tan A−tan B) is not a valid identity."""
    if not _FALSE_TAN_PRODUCT_ID.search(text):
        return None
    if not sympy_available():
        return "false_tan_product_identity"
    from sympy import N

    ta = (
        _parse_rational_expr(_TAN_A_VAL.search(text).group(1))
        if _TAN_A_VAL.search(text)
        else None
    )
    tb = (
        _parse_rational_expr(_TAN_B_VAL.search(text).group(1))
        if _TAN_B_VAL.search(text)
        else None
    )
    ta = ta if ta is not None else 2
    tb = tb if tb is not None else 3
    from sympy import simplify

    lhs = ta * tb
    rhs = (ta + tb) / (ta - tb)
    if abs(float(N(simplify(lhs - rhs)))) > 0.05:
        return "false_tan_product_identity"
    return "false_tan_product_identity"


def _check_sin_cos_ab_pythagoras(text: str) -> Optional[str]:
    cm = _COS_AB_VAL.search(text)
    sm = _SIN_AB_VAL.search(text)
    if not cm or not sm:
        return None
    cval = _parse_rational_expr(cm.group(1).replace("√", "sqrt"))
    sval = _parse_rational_expr(sm.group(1).replace("√", "sqrt"))
    if cval is None or sval is None:
        return None
    from sympy import N, simplify

    if abs(float(N(simplify(cval**2 + sval**2 - 1)))) > 0.05:
        return "sin_cos_ab_not_unit"
    return None


def _check_right_triangle_tan_bc(text: str) -> Optional[str]:
    if not _TRIANGLE_CTX.search(text) or not _ANGLE_A_RIGHT.search(text):
        return None
    bm = _TAN_B_VAL.search(text)
    cm = _TAN_C_VAL.search(text)
    if not bm or not cm:
        return None
    tb = _parse_rational_expr(bm.group(1))
    tc = _parse_rational_expr(cm.group(1))
    if tb is None or tc is None:
        return None
    from sympy import N

    # Right angle at A => B + C = 90° => tan B * tan C = 1
    if abs(float(N(tb * tc - 1))) > 0.08:
        return "right_triangle_tan_bc_inconsistent"
    return None


def _check_tan_a_undefined_then_find(text: str) -> Optional[str]:
    if _ANGLE_A_RIGHT.search(text) and _FIND_TAN_A.search(text):
        return "find_tan_a_at_right_angle"
    return None


def _check_trivial_tan_5_proof(text: str) -> Optional[str]:
    if _TRIVIAL_TAN_5.search(text) and "1 - tan" not in text.replace(" ", "").lower():
        return "trivial_tan_5_substitution_proof"
    return None


def _cos_ab_value_from_text(text: str) -> Optional[Any]:
    """cos(A+B) from cos(A+B)=… or cos A cos B − sin A sin B = …"""
    cm = re.search(
        r"\bcos\s*\(\s*A\s*\+\s*B\s*\)\s*=\s*"
        r"(-?\s*(?:√\s*)?\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?)",
        text,
        re.I,
    )
    if cm:
        return _parse_rational_expr(cm.group(1).replace("√", "sqrt"))
    em = _COS_AB_EXPAND.search(text)
    if em:
        return _parse_rational_expr(em.group(1).replace("√", "sqrt"))
    return None


def _check_all_sin_cos_ab_pairs(text: str) -> Optional[str]:
    """Any sin(A+B), cos(A+B) fraction pair must satisfy sin²+cos²=1."""
    if not sympy_available():
        return None
    from sympy import N, simplify

    pairs: Dict[str, Any] = {}
    for m in _FRAC_PAIR.finditer(text):
        pairs[m.group(1).lower()] = _parse_rational_expr(
            m.group(2).replace("√", "sqrt")
        )
    if "sin" in pairs and "cos" in pairs:
        s, c = pairs["sin"], pairs["cos"]
        if s is not None and c is not None:
            if abs(float(N(simplify(s**2 + c**2 - 1)))) > 0.05:
                return "sin_cos_ab_not_unit"
    return None


def _check_tan_ab_sum_product_formula(text: str) -> Optional[str]:
    """tan(A+B) must equal (tan A+tan B)/(1-tan A tan B) when sum and product given."""
    sm = _TAN_SUM_AB.search(text)
    pm = _TAN_PROD_AB.search(text)
    tm = _TAN_AB_VAL.search(text)
    if not (sm and pm and tm):
        return None
    if not sympy_available():
        return None
    from sympy import N, simplify

    sval = _parse_sqrt_expr(sm.group(1).replace("√", "sqrt"))
    pval = _parse_rational_expr(pm.group(1))
    tclaim = _parse_rational_expr(tm.group(1))
    if sval is None or pval is None or tclaim is None:
        return None
    actual = simplify(sval / (1 - pval))
    if abs(float(N(actual - tclaim))) > 0.08:
        return "tan_ab_wrong_from_sum_product"
    return None


def _check_tan_ab_vs_cos_ab(text: str) -> Optional[str]:
    """tan(A+B) must match sin/cos implied by cos(A+B)=k (Paper 9 Q3)."""
    if not sympy_available():
        return None
    tm = _TAN_AB_VAL.search(text)
    cval = _cos_ab_value_from_text(text)
    if not tm or cval is None:
        return None
    t_claim = _parse_rational_expr(tm.group(1).replace("√", "sqrt"))
    if t_claim is None:
        return None
    from sympy import N, sqrt, simplify

    # cos φ = cval => |tan φ| = sqrt(1-c²)/|c|
    sin_sq = simplify(1 - cval**2)
    if float(N(sin_sq)) < 0:
        return "cos_ab_out_of_range"
    tan_mag = sqrt(sin_sq) / abs(cval)
    if abs(float(N(abs(t_claim) - tan_mag))) > 0.15:
        return "tan_ab_inconsistent_with_cos_ab"
    return None


def _check_false_cos_sum_three_angles(text: str) -> Optional[str]:
    """cos(A+B+C) ≠ cos A cos B cos C + sin A sin B sin C (Paper 9 Q4)."""
    if not _FALSE_COS_SUM_3.search(text):
        return None
    if not sympy_available():
        return "false_cos_a_plus_b_plus_c_formula"
    try:
        from sympy import N, cos, pi, sin, symbols, simplify

        A, B, C = symbols("A B C")
        lhs = cos(A + B + C)
        rhs = cos(A) * cos(B) * cos(C) + sin(A) * sin(B) * sin(C)
        diff = simplify(lhs - rhs)
        val = pi / 3  # 60°
        err = abs(float(N(diff.subs({A: val, B: val, C: val}))))
        if err > 0.1:
            return "false_cos_a_plus_b_plus_c_formula"
    except Exception:
        return "false_cos_a_plus_b_plus_c_formula"
    return "false_cos_a_plus_b_plus_c_formula"


def _check_sin_ac_when_angles_30_60(text: str) -> Optional[str]:
    """∠A=30°, ∠C=60° in triangle => sin(A+C)=sin 90°=1 (Paper 9 Q5)."""
    if not (_TRIANGLE_CTX.search(text) and _ANGLE_A_30.search(text) and _ANGLE_C_60.search(text)):
        return None
    if _SIN_AC_WRONG_2.search(text):
        return "sin_ac_wrong_at_90"
    sm = _SIN_AC_VAL.search(text)
    if sm:
        sval = _parse_rational_expr(sm.group(1).replace("√", "sqrt"))
        if sval is not None:
            from sympy import N

            if abs(float(N(sval - 1))) > 0.05:
                return "sin_ac_not_one_when_a_plus_c_90"
    return None


def _check_tan_at_90_in_working(text: str) -> Optional[str]:
    """Using tan(A+B) when A+B=90° is undefined."""
    if _TAN_SUM_90.search(text):
        return "tan_undefined_at_90_in_working"
    if re.search(
        r"(?:∠|angle)\s*A\s*=\s*30\s*°.{0,80}(?:∠|angle)\s*B\s*=\s*60\s*°|"
        r"(?:∠|angle)\s*B\s*=\s*60\s*°.{0,80}(?:∠|angle)\s*A\s*=\s*30\s*°",
        text,
        re.I,
    ) and re.search(r"\btan\s*\(\s*A\s*\+\s*B\s*\)", text, re.I):
        return "tan_undefined_at_90_in_working"
    return None


def _check_tan_90_used(text: str) -> Optional[str]:
    if _TAN_90_USED.search(text):
        return "tan_90_undefined_used"
    return None


def _check_sin_90_wrong_division(text: str) -> Optional[str]:
    """sin(90°)=1 but (sin30cos60+cos30sin60)/cos60 = 2 (Paper 9 Q5 answer)."""
    if _SIN_90_DIV_COS60.search(text):
        return "sin_90_wrong_formula_divide_cos60"
    if not sympy_available():
        return None
    if re.search(r"\bsin\s*\(\s*90", text, re.I):
        from sympy import N, Rational, sqrt, sin, cos, pi

        num = sin(pi / 6) * cos(pi / 3) + cos(pi / 6) * sin(pi / 3)
        wrong = num / cos(pi / 3)
        if abs(float(N(wrong - 2))) < 0.01:
            return "sin_90_wrong_formula_divide_cos60"
    return None


def _check_misapplied_tan_for_sin_ac(text: str) -> Optional[str]:
    """Paper 9 Q5: sin(A+C) with A=30°, C=60° must be 1 — not via tan(A+B)."""
    if not _TRIANGLE_CTX.search(text):
        return None
    if not (_ANGLE_A_30.search(text) and _ANGLE_C_60.search(text)):
        return None
    if re.search(r"\bsin\s*\(\s*A\s*\+\s*C\s*\)", text, re.I) and re.search(
        r"\btan\s*\(\s*A\s*\+\s*B\s*\)", text, re.I
    ):
        return "misapplied_tan_ab_for_sin_ac"
    return None


def _check_sin_5_formula_numeric(text: str) -> Optional[str]:
    if not _SIN_5_FORMULA.search(text):
        return None
    if not sympy_available():
        return None
    try:
        from sympy import N, Rational, pi, sin, cos, symbols

        th = symbols("theta")
        from app.generation.sympy_math_text import _SYM

        th = _SYM["theta"]
        lhs = sin(5 * th)
        rhs = 16 * sin(th) * cos(th) * (1 - 10 * sin(th) ** 2 * cos(th) ** 2)
        from sympy import simplify

        diff = simplify(lhs - rhs)
        # θ = 30° = pi/6
        if abs(float(N(diff.subs(th, pi / 6)))) > 0.05:
            return "false_sin_5theta_formula"
    except Exception:
        return None
    return None


def evaluate_trig_sympy(
    q: Dict[str, Any],
    *,
    locked_chapter: str = "",
) -> Dict[str, Any]:
    ch = (locked_chapter or q.get("locked_chapter") or "").strip().lower()
    if ch != "trigonometry":
        return {"trig_sympy_ok": True, "trig_sympy_flags": [], "trig_sympy_critical": []}

    text = "\n".join(
        p
        for p in (
            q.get("content") or q.get("question") or "",
            q.get("correct_answer") or "",
            q.get("explanation") or "",
        )
        if p
    )
    flags: List[str] = []
    checks = (
        _check_quadrant_tan_consistency,
        _check_sin_cos_from_tan,
        _check_self_referential_tan_a,
        _check_false_tan_product_identity,
        _check_sin_cos_ab_pythagoras,
        _check_all_sin_cos_ab_pairs,
        _check_tan_ab_sum_product_formula,
        _check_tan_ab_vs_cos_ab,
        _check_false_cos_sum_three_angles,
        _check_sin_ac_when_angles_30_60,
        _check_tan_at_90_in_working,
        _check_misapplied_tan_for_sin_ac,
        _check_tan_90_used,
        _check_sin_90_wrong_division,
        _check_right_triangle_tan_bc,
        _check_tan_a_undefined_then_find,
        _check_trivial_tan_5_proof,
        _check_sin_5_formula_numeric,
    )
    for fn in checks:
        hit = fn(text)
        if hit:
            flags.append(hit)

    critical = {
        "quadrant_tan_sign_contradiction",
        "sin_cos_theta_value_inconsistent",
        "self_referential_find_tan_a",
        "false_tan_product_identity",
        "sin_cos_ab_not_unit",
        "tan_ab_wrong_from_sum_product",
        "tan_ab_inconsistent_with_cos_ab",
        "cos_ab_out_of_range",
        "false_cos_a_plus_b_plus_c_formula",
        "sin_ac_wrong_at_90",
        "sin_ac_not_one_when_a_plus_c_90",
        "tan_undefined_at_90_in_working",
        "misapplied_tan_ab_for_sin_ac",
        "tan_90_undefined_used",
        "sin_90_wrong_formula_divide_cos60",
        "right_triangle_tan_bc_inconsistent",
        "find_tan_a_at_right_angle",
        "trivial_tan_5_substitution_proof",
        "false_sin_5theta_formula",
    }
    critical_hits = [f for f in flags if f in critical]
    return {
        "trig_sympy_ok": len(critical_hits) == 0,
        "trig_sympy_flags": flags,
        "trig_sympy_critical": critical_hits,
    }


def should_reject_trig_sympy(q: Dict[str, Any], *, locked_chapter: str = "") -> bool:
    return not evaluate_trig_sympy(q, locked_chapter=locked_chapter).get(
        "trig_sympy_ok", True
    )
