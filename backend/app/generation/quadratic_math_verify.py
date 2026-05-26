"""
Computational verification for quadratic stems and model answers.

Catches:
- Claimed factorisation that does not match ax² + bx + c (wrong middle term / ac)
- 'By factorisation only' when no integer factor pair sums to b
- Equal-root parameter answers inconsistent with D = 0 / perfect square
"""
from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

# ax² + bx + c  (a may be omitted = 1)
_EQ_RE = re.compile(
    r"(?:(\d+)\s*)?x²\s*([+\−-])\s*(\d+)\s*x\s*([+\−-])\s*(\d+)",
    re.I,
)

# (11x − 4)(2x − 7) or (5x + 3)(x - 2)
_FACTOR_RE = re.compile(
    r"\((\d+)\s*x\s*([+\−-])\s*(\d+)\)\s*\((\d+)\s*x\s*([+\−-])\s*(\d+)\)",
    re.I,
)

# ax² ± bx ± (letter ± N) = 0
_EQ_PARAM_RE = re.compile(
    r"(?:(\d+)\s*)?x²\s*([+\−-])\s*(\d+)\s*x\s*([+\−-])\s*\(\s*([a-z])\s*([+\−-])\s*(\d+)\s*\)",
    re.I,
)

# p + 51 or (k + 22) anywhere in text
_PARAM_CONST_RE = re.compile(
    r"([+\−-])\s*\(\s*([a-z])\s*([+\−-])\s*(\d+)\s*\)",
    re.I,
)


def _sign_char(ch: str) -> int:
    return -1 if ch in ("−", "-", "–") else 1


def parse_quadratic_equation(text: str) -> Optional[Tuple[int, int, int]]:
    """Return (a, b, c) for ax² + bx + c = 0, or None."""
    m = _EQ_RE.search(text.replace(" ", ""))
    if not m:
        return None
    a = int(m.group(1) or "1")
    b = _sign_char(m.group(2)) * int(m.group(3))
    c = _sign_char(m.group(4)) * int(m.group(5))
    return a, b, c


def expand_binomial_factors(text: str) -> Optional[Tuple[int, int, int]]:
    """Expand (px ± q)(rx ± s) to (a, b, c) for monic standard form coefficients."""
    m = _FACTOR_RE.search(text.replace(" ", ""))
    if not m:
        return None
    p, s1, q = int(m.group(1)), _sign_char(m.group(2)), int(m.group(3))
    r, s2, t = int(m.group(4)), _sign_char(m.group(5)), int(m.group(6))
    a = p * r
    # (px + s1*q)(rx + s2*t) → middle: p*s2*t + r*s1*q
    b = p * s2 * t + r * s1 * q
    c = s1 * q * s2 * t
    return a, b, c


def integer_factor_pairs_ac(ac: int) -> List[Tuple[int, int]]:
    """Positive factor pairs (d1, d2) with d1*d2 = |ac|."""
    n = abs(ac)
    pairs: List[Tuple[int, int]] = []
    d = 1
    while d * d <= n:
        if n % d == 0:
            pairs.append((d, n // d))
            if d != n // d:
                pairs.append((n // d, d))
        d += 1
    return pairs


def can_factorise_over_integers(a: int, b: int, c: int) -> bool:
    """True if some factor pair of |ac| can sum to |b| with correct sign pattern."""
    if a == 0:
        return False
    ac = a * c
    target = abs(b)
    for d1, d2 in integer_factor_pairs_ac(ac):
        if d1 + d2 == target:
            return True
    return False


def verify_factorisation_consistency(
    equation_text: str,
    answer_text: str,
) -> List[str]:
    """Compare parsed equation in stem vs factors claimed in answer."""
    flags: List[str] = []
    eq = parse_quadratic_equation(equation_text)
    fac = expand_binomial_factors(answer_text)
    if not eq or not fac:
        return flags
    a1, b1, c1 = eq
    a2, b2, c2 = fac
    if a1 != a2:
        flags.append(f"factorisation_leading_coeff_mismatch:{a1}!={a2}")
    if b1 != b2:
        flags.append(f"factorisation_middle_term_mismatch:eq_b={b1}_from_factors={b2}")
    if c1 != c2:
        flags.append(f"factorisation_constant_mismatch:eq_c={c1}_from_factors={c2}")
    return flags


def verify_factorisation_required(stem: str, answer_text: str) -> List[str]:
    """Stem demands factorisation but equation may not factor over integers."""
    flags: List[str] = []
    low = stem.lower()
    if not re.search(r"factoris", low):
        return flags
    eq = parse_quadratic_equation(stem)
    if not eq:
        return flags
    a, b, c = eq
    if not can_factorise_over_integers(a, b, c):
        flags.append(f"factorisation_impossible_integer_coeffs:a={a}_b={b}_c={c}")
    flags.extend(verify_factorisation_consistency(stem, answer_text))
    return flags


def _verify_param_internal_consistency(answer_text: str, letter: str) -> List[str]:
    """e.g. 'p = 68' but 'p + 51 = 68' implies p = 17."""
    flags: List[str] = []
    ans = answer_text.replace(" ", "")
    m = re.search(
        rf"{letter}\s*\+\s*(\d+)\s*=\s*(\d+)",
        ans,
        re.I,
    )
    if not m:
        return flags
    offset, target = int(m.group(1)), int(m.group(2))
    implied = target - offset
    claimed = _parse_param_value(answer_text, letter)
    if claimed is not None and claimed != implied:
        flags.append(
            f"equal_roots_param_internal_contradiction:stated_{letter}={claimed}_implied_{implied}"
        )
    return flags


def verify_stem_integer_factorisation(stem: str) -> List[str]:
    """Flag when stem requires factorisation but coefficients do not allow it."""
    if not re.search(r"factoris", stem, re.I):
        return []
    eq = parse_quadratic_equation(stem)
    if not eq:
        return []
    a, b, c = eq
    if not can_factorise_over_integers(a, b, c):
        return [f"factorisation_impossible_integer_coeffs:a={a}_b={b}_c={c}"]
    return []


def _parse_param_value(answer: str, letter: str) -> Optional[int]:
    m = re.search(
        rf"{letter}\s*=\s*([+\-−]?\d+)",
        answer.replace(" ", ""),
        re.I,
    )
    if not m:
        return None
    return int(m.group(1).replace("−", "-"))


def verify_equal_roots_parameter(
    stem: str,
    answer_text: str,
) -> List[str]:
    """Check D = 0 parameter and repeated root against stem equation."""
    flags: List[str] = []
    eq_text = stem.replace(" ", "")
    m_eq = _EQ_PARAM_RE.search(eq_text)
    if not m_eq:
        return flags
    a = int(m_eq.group(1) or "1")
    b = _sign_char(m_eq.group(2)) * int(m_eq.group(3))
    letter = m_eq.group(5).lower()

    claimed = _parse_param_value(answer_text, letter)
    if claimed is None:
        return flags

    # Standard stem form: ax² + bx + (letter ± N) = 0  →  c = letter ± N
    if m_eq.group(6) in ("+", ""):
        c_when_param = claimed + int(m_eq.group(7))
    else:
        c_when_param = claimed - int(m_eq.group(7))

    flags.extend(_verify_param_internal_consistency(answer_text, letter))

    d = b * b - 4 * a * c_when_param
    if d != 0:
        flags.append(f"equal_roots_D_nonzero:D={d}_for_{letter}={claimed}")

    # Repeated root r = -b/(2a)
    if 2 * a != 0:
        expected_r_num = -b
        if expected_r_num % (2 * a) == 0:
            expected_r = expected_r_num // (2 * a)
            m_r = re.search(r"r\s*=\s*([+\-−]?\d+)", answer_text.replace(" ", ""))
            if m_r:
                stated_r = int(m_r.group(1).replace("−", "-"))
                if stated_r != expected_r:
                    flags.append(f"equal_roots_repeated_root_mismatch:{stated_r}!={expected_r}")

    # Perfect square constant: a*r² should equal c_when_param
    if 2 * a != 0 and d == 0:
        r = -b // (2 * a)
        lhs = a * r * r
        if lhs != c_when_param:
            flags.append(
                f"equal_roots_perfect_square_mismatch:ar²={lhs}_c={c_when_param}"
            )
    return flags


_SPEED_DIST_RE = re.compile(
    r"(\d+)\s*km\s+at\s+([a-z])\s*km/h",
    re.I,
)
_SPEED_RETURN_RE = re.compile(
    r"\(\s*([a-z])\s*\+\s*(\d+)\s*\)\s*km/h",
    re.I,
)
_SPEED_TIME_DIFF_RE = re.compile(
    r"(?:taking|takes|return\s+takes)\s+(.{1,20}?)\s+(?:hour|h)\s+less",
    re.I,
)
_QUAD_VAR_RE = re.compile(
    r"([a-z])²\s*\+\s*(\d+)\s*([a-z])\s*([+\−-])\s*(\d+)\s*=\s*0",
    re.I,
)
_LINEAR_DIM_RE = re.compile(
    r"\((\d+)\s*x\s*([+\−-])\s*(\d+)\s*\)\s*m",
    re.I,
)
_AREA_GIVEN_RE = re.compile(
    r"area\s*(\d+)\s*m²",
    re.I,
)
_X_ROOT_RE = re.compile(
    r"x\s*=\s*([+\-−]?\d+)\s*/\s*(\d+)|x\s*=\s*([+\-−]?\d+)",
    re.I,
)
_DIM_ANSWER_RE = re.compile(
    r"(?:length|breadth)\s+(\d+)\s*/\s*(\d+)\s*m",
    re.I,
)


def _parse_time_hours(text: str) -> Optional[float]:
    t = text.replace(" ", "").lower()
    if "½" in t or "1/2" in t or "0.5" in t:
        return 0.5
    if "⅓" in t or "1/3" in t:
        return 1.0 / 3.0
    if "⅔" in t or "2/3" in t:
        return 2.0 / 3.0
    if "¾" in t or "3/4" in t:
        return 0.75
    m = re.search(r"(\d+)\s*/\s*(\d+)", t)
    if m:
        return int(m.group(1)) / int(m.group(2))
    m = re.search(r"(\d+)", t)
    if m:
        return float(m.group(1))
    return None


def _positive_root_from_quadratic(b: int, c: int) -> Optional[float]:
    """For x² + bx + c = 0, return smallest positive root if any."""
    d = b * b - 4 * c
    if d < 0:
        return None
    r1 = (-b - math.sqrt(d)) / 2
    r2 = (-b + math.sqrt(d)) / 2
    for r in (r1, r2):
        if r > 0:
            return r
    return None


def verify_speed_time_word_problem(stem: str, answer_text: str) -> List[str]:
    """
    Check D/s − D/(s+Δ) equals stated time difference for speed/return stems.
    Uses quadratic in answer: s² + ps + q = 0 (standard motion setup).
    """
    flags: List[str] = []
    if not re.search(r"km/h|km\s+at", stem, re.I):
        return flags
    dm = _SPEED_DIST_RE.search(stem)
    rm = _SPEED_RETURN_RE.search(stem)
    tm = _SPEED_TIME_DIFF_RE.search(stem)
    if not dm or not rm or not tm:
        return flags
    dist = int(dm.group(1))
    dv = int(rm.group(2))
    hours = _parse_time_hours(tm.group(1))
    if hours is None or hours <= 0:
        return flags

    qm = _QUAD_VAR_RE.search(answer_text.replace(" ", ""))
    if not qm:
        return flags
    p = int(qm.group(2))
    c = _sign_char(qm.group(4)) * int(qm.group(5))
    speed = _positive_root_from_quadratic(p, c)
    if speed is None:
        return flags

    actual = dist / speed - dist / (speed + dv)
    if abs(actual - hours) > 0.02:
        flags.append(
            f"speed_time_stem_answer_mismatch:dist={dist}_dv={dv}_"
            f"stated_diff={hours}h_actual={actual:.4f}h_speed={speed:.4f}"
        )
    return flags


def _linear_value(coef: int, sign_ch: str, const: int, x: Fraction) -> Fraction:
    offset = const if sign_ch in ("+", "") else -const
    return Fraction(coef, 1) * x + Fraction(offset, 1)


def _parse_x_from_answer(answer_text: str) -> Optional[Fraction]:
    m = _X_ROOT_RE.search(answer_text.replace(" ", ""))
    if not m:
        return None
    if m.group(2):
        return Fraction(int(m.group(1).replace("−", "-")), int(m.group(2)))
    return Fraction(int(m.group(3).replace("−", "-")), 1)


def verify_area_word_problem(stem: str, answer_text: str) -> List[str]:
    """Check length × breadth at found x equals stated area; catch wrong dimensions."""
    flags: List[str] = []
    if not re.search(r"rectangle|area\s+\d+", stem, re.I):
        return flags
    dims = _LINEAR_DIM_RE.findall(stem)
    am = _AREA_GIVEN_RE.search(stem)
    if len(dims) < 2 or not am:
        return flags
    target_area = int(am.group(1))
    x = _parse_x_from_answer(answer_text)
    if x is None:
        return flags

    lengths: List[Fraction] = []
    for coef_s, sign_ch, const_s in dims[:2]:
        lengths.append(
            _linear_value(int(coef_s), sign_ch, int(const_s), x)
        )
    if len(lengths) < 2:
        return flags
    product = lengths[0] * lengths[1]
    if product != Fraction(target_area, 1):
        flags.append(
            f"area_dimension_product_mismatch:expected_area={target_area}_"
            f"from_x={x}_product={product}"
        )

    # If answer states explicit length/breadth fractions, verify those too
    stated = [
        Fraction(int(a), int(b))
        for a, b in _DIM_ANSWER_RE.findall(answer_text)
    ]
    if len(stated) >= 2:
        expected_pair = sorted(lengths)
        stated_pair = sorted(stated[:2])
        if stated_pair != expected_pair:
            flags.append(
                f"area_stated_dimensions_mismatch:stated={stated_pair}_"
                f"expected={expected_pair}_x={x}"
            )
    return flags


def verify_alpha_squared_sum(stem: str, answer_text: str) -> List[str]:
    """Recompute α²+β² = (b/a)² − 2c/a from stem coefficients."""
    flags: List[str] = []
    if "α²" not in answer_text and "α2" not in answer_text.lower():
        return flags
    eq = parse_quadratic_equation(stem)
    if not eq:
        return flags
    a, b, c = eq
    if a == 0:
        return flags
    expected = Fraction(b, a) ** 2 - 2 * Fraction(c, a)
    start = answer_text.find("α²")
    if start < 0:
        return flags
    tail = answer_text[start:]
    for sep in ("α + β", "α+β", "Hence"):
        if sep in tail:
            tail = tail.split(sep, 1)[0]
    fracs = re.findall(r"(\d+)\s*/\s*(\d+)", tail)
    if not fracs:
        return flags
    claimed = Fraction(int(fracs[-1][0]), int(fracs[-1][1]))
    if claimed != expected:
        flags.append(
            f"alpha_squared_sum_mismatch:claimed={claimed}_expected={expected}"
        )
    return flags


_MONIC_PARAM_STEM_RE = re.compile(
    r"x²\s*([+\−-])\s*(\d+)\s*x\s*([+\−-])\s*\(\s*([a-z])\s*([+\−-])\s*(\d+)\s*\)\s*=\s*0",
    re.I,
)
_ROOT_DIFF_RE = re.compile(r"differ(?:ing)?\s+by\s+(\d+)", re.I)


def verify_or_root_difference_parameter(stem: str, answer_text: str) -> List[str]:
    """OR branch (b): x² ± bx + (letter ± k) = 0 with |α − β| = d."""
    flags: List[str] = []
    if not _ROOT_DIFF_RE.search(stem):
        return flags
    m = _MONIC_PARAM_STEM_RE.search(stem.replace(" ", ""))
    if not m:
        return flags
    b = _sign_char(m.group(1)) * int(m.group(2))
    letter = m.group(4).lower()
    if m.group(5) in ("+", ""):
        c_offset = int(m.group(6))
    else:
        c_offset = -int(m.group(6))
    target_diff = int(_ROOT_DIFF_RE.search(stem).group(1))

    claimed_q = _parse_param_value(answer_text, letter)
    if claimed_q is None:
        return flags
    c_val = claimed_q + c_offset
    d_sq = b * b - 4 * c_val
    if d_sq != target_diff * target_diff:
        flags.append(
            f"root_difference_D_mismatch:diff={target_diff}_D_sq={d_sq}_for_{letter}={claimed_q}"
        )
    pairs = re.findall(r"(\d+)\s+and\s+(\d+)", answer_text, re.I)
    if pairs:
        r1, r2 = int(pairs[0][0]), int(pairs[0][1])
        if abs(abs(r1 - r2) - target_diff) > 0:
            flags.append(
                f"root_difference_numeric_mismatch:{r1},{r2}_expected_diff={target_diff}"
            )
        if r1 + r2 != -b or r1 * r2 != c_val:
            flags.append(
                f"root_difference_vieta_mismatch:sum={r1+r2}_expected={-b}_prod={r1*r2}_expected_c={c_val}"
            )
    return flags


def verify_quadratic_question_math(
    question: Dict[str, Any],
) -> Dict[str, Any]:
    """Stem + model answer computational audit."""
    stem = (
        question.get("question")
        or question.get("content")
        or ""
    ).strip()
    answer = (question.get("correct_answer") or "").strip()
    flags: List[str] = []
    if stem and not answer:
        flags.append("missing_correct_answer")
    flags.extend(verify_stem_integer_factorisation(stem))
    if stem and answer:
        flags.extend(verify_factorisation_consistency(stem, answer))
        if re.search(r"factoris", stem, re.I):
            flags.extend(verify_factorisation_required(stem, answer))
        if re.search(r"equal\s+real\s+roots|d\s*=\s*0", stem, re.I):
            flags.extend(verify_equal_roots_parameter(stem, answer))
            pm = _PARAM_CONST_RE.search(stem.replace(" ", ""))
            if pm:
                flags.extend(
                    _verify_param_internal_consistency(answer, pm.group(2).lower())
                )
        flags.extend(verify_speed_time_word_problem(stem, answer))
        flags.extend(verify_area_word_problem(stem, answer))
        flags.extend(verify_alpha_squared_sum(stem, answer))
        flags.extend(verify_or_root_difference_parameter(stem, answer))
    return {
        "math_verification_ok": not flags,
        "math_verification_flags": flags,
    }


def should_reject_quadratic_question_math(question: Dict[str, Any]) -> bool:
    return not verify_quadratic_question_math(question).get(
        "math_verification_ok", True
    )
