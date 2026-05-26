"""
Symbolic and pattern checks for LLM-generated stems/answers.

Catches hallucinated formulas, calculus in trig papers, encoding corruption,
and impossible geometry — issues seen in Groq/minimal generation paths.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# False tan(A+B): (tan A + tan B - tan A tan B) / (1 + tan A tan B)
_FALSE_TAN_ADD = re.compile(
    r"tan\s*\(\s*[A-Zαβγθ]\s*\+\s*[A-Zαβγθ]\s*\)"
    r"[\s\S]{0,120}?"
    r"tan\s*[A-Zαβγθ]\s*\+\s*tan\s*[A-Zαβγθ]\s*[-−]\s*tan",
    re.I,
)
_FALSE_TAN_DENOM_PLUS = re.compile(
    r"tan\s*[A-Zαβγθ]\s*\+\s*tan\s*[A-Zαβγθ]\s*[-−]\s*tan\s*[A-Zαβγθ]\s*tan\s*[A-Zαβγθ]"
    r"[\s\S]{0,80}?1\s*\+\s*tan\s*[A-Zαβγθ]\s*tan\s*[A-Zαβγθ]",
    re.I,
)

_CALCULUS = re.compile(
    r"∫|\\\s*int\b|\bintegral\b|\bdx\b|\bdu\b|\bd/dx\b|\bderivative\b|\blimit\s*\(",
    re.I,
)
_UNICODE_GARBAGE = re.compile(
    r"0\s*3\s*c[09]|0394|03c9|03c0|03b8|\(\s*['\"]Step\s*\d",
    re.I,
)
_PYTHON_TUPLE_ANSWER = re.compile(r"^\s*\[\s*\(\s*['\"]Step", re.I)
_RAW_LATEX_LEAK = re.compile(
    r"\\mathsf|\\mathbf|\\sum\b(?!\s*of\s)|\\\s*cap\\",
    re.I,
)
_ORPHAN_SIGMA = re.compile(r"(?<![a-zA-Z])∑(?![a-zA-Z])|\+\s*∑\s*\+", re.I)
_TRIANGLE_IMPOSSIBLE_ANGLE = re.compile(
    r"(?:Δ|triangle|right-angled)[\s\S]{0,80}?"
    r"(?:3\s*π\s*/\s*2|π\s*\+\s*π\s*/\s*2|270\s*°)",
    re.I,
)
_CHAINED_TAN_EQUALITY = re.compile(
    r"tan\s*[A-Zαβγθ]\s*=\s*tan\s*2[A-Zαβγθ]\s*\+\s*tan\s*[A-Zαβγθ]\s*=\s*tan\s*\(",
    re.I,
)
_ANSWER_REPEATS_STEM_ONLY = re.compile(
    r"^(?:Prove|Hence|If|In)\b",
    re.I,
)
_FIND_TAN_AB = re.compile(
    r"find\s+(?:the\s+value\s+of\s+)?tan\s*\(\s*A\s*\+\s*B\s*\)",
    re.I,
)
_ANGLE_B_GIVEN = re.compile(
    r"\b(?:tan|sin|cos|cot|sec|cosec)\s+B\b|\bangle\s+B\b|\bB\s+lies\s+in\b",
    re.I,
)
_FALSE_TAN_4THETA = re.compile(
    r"tan\s*\(\s*4\s*(?:θ|theta)\s*\)\s*=\s*\(\s*tan\s*(?:θ|theta)\s*\+\s*sec",
    re.I,
)
_PROVE_TAN_3THETA_NUMERIC = re.compile(
    r"cos\s*(?:θ|theta)\s*=\s*\([^)]+\)[\s\S]{0,60}?tan\s*3\s*(?:θ|theta)\s*=\s*",
    re.I,
)
_TAN_AT_RIGHT_ANGLE = re.compile(
    r"(?:∠|angle)\s*A\s*=\s*π\s*/\s*2[\s\S]{0,80}?find\s+tan\s*A",
    re.I,
)


def _sympy_rejects_trig_claim(stem: str, answer: str) -> bool:
    """Spot-check false tan(4θ) identity and tan 3θ numeric claims when SymPy is available."""
    from app.generation.sympy_math_text import sympy_available

    if not sympy_available():
        return False
    try:
        from sympy import N, Rational, acos, cos, pi, simplify, sqrt, tan
        from app.generation.sympy_math_text import _SYM

        th = _SYM["theta"]
    except Exception:
        return False

    if _FALSE_TAN_4THETA.search(stem):
        lhs = tan(4 * th)
        rhs = (tan(th) + (1 / cos(th)) ** 2) / (1 + tan(th) * (1 / cos(th)) ** 2)
        diff = simplify(lhs - rhs)
        if abs(float(N(diff.subs(th, pi / 12)))) > 0.05:
            return True

    m = re.search(
        r"cos\s*(?:θ|theta)\s*=\s*\(\s*3\s*[-−]\s*√?2\s*\)\s*/\s*4",
        stem,
        re.I,
    )
    if m and re.search(r"tan\s*3\s*(?:θ|theta)\s*=\s*7\s*√?2\s*/\s*5", stem, re.I):
        cval = (Rational(3, 1) - sqrt(2)) / 4
        t3 = tan(3 * acos(cval))
        if abs(float(N(t3)) - float(N(7 * sqrt(2) / 5))) > 0.15:
            return True
    return False


def _combined_text(q: Dict[str, Any]) -> str:
    parts = [
        q.get("content") or q.get("question") or "",
        q.get("correct_answer") or "",
        q.get("explanation") or "",
    ]
    return "\n".join(p for p in parts if p)


def evaluate_math_stem(
    q: Dict[str, Any],
    *,
    locked_chapter: str = "",
) -> Dict[str, Any]:
    text = _combined_text(q)
    answer = (q.get("correct_answer") or "").strip()
    stem = (q.get("content") or q.get("question") or "").strip()
    flags: List[str] = []

    if _UNICODE_GARBAGE.search(text):
        flags.append("unicode_encoding_corruption")
    if _RAW_LATEX_LEAK.search(text):
        flags.append("raw_latex_in_stem_or_answer")
    if _PYTHON_TUPLE_ANSWER.search(answer):
        flags.append("python_tuple_not_solution")
    if _ORPHAN_SIGMA.search(text):
        flags.append("orphan_summation_symbol")
    if _FALSE_TAN_ADD.search(text) or _FALSE_TAN_DENOM_PLUS.search(text):
        flags.append("false_tan_a_plus_b_formula")
    if _CHAINED_TAN_EQUALITY.search(text):
        flags.append("impossible_tan_chain")
    if _TRIANGLE_IMPOSSIBLE_ANGLE.search(text):
        flags.append("impossible_triangle_angle")
    if _FALSE_TAN_4THETA.search(text):
        flags.append("false_tan_multiple_angle_identity")
    if _FIND_TAN_AB.search(stem) and not _ANGLE_B_GIVEN.search(stem):
        flags.append("compound_angle_B_undefined")
    if _PROVE_TAN_3THETA_NUMERIC.search(stem):
        flags.append("unverified_tan_triple_claim")
    if _TAN_AT_RIGHT_ANGLE.search(stem):
        flags.append("tan_undefined_at_right_angle")

    ch = (locked_chapter or q.get("locked_chapter") or "").strip().lower()
    trig_sympy_critical: List[str] = []
    if ch == "quadratic":
        from app.core.config import settings
        from app.generation.quadratic_math_gate import should_block_quadratic_math

        if settings.ENABLE_QUADRATIC_MATH_VERIFY and should_block_quadratic_math(q):
            flags.append("quadratic_math_verification_failed")
    if ch == "trigonometry":
        if _CALCULUS.search(stem):
            flags.append("calculus_outside_trigonometry")
        if _sympy_rejects_trig_claim(stem, answer):
            flags.append("sympy_numeric_claim_false")
        from app.generation.trig_sympy_verifier import evaluate_trig_sympy

        ts = evaluate_trig_sympy(q, locked_chapter=ch)
        flags.extend(ts.get("trig_sympy_flags") or [])
        trig_sympy_critical = list(ts.get("trig_sympy_critical") or [])

    if stem and answer:
        stem_norm = re.sub(r"\s+", " ", stem.lower())[:200]
        ans_norm = re.sub(r"\s+", " ", answer.lower())[:200]
        if stem_norm and ans_norm.startswith(stem_norm[: min(80, len(stem_norm))]):
            if len(answer) < len(stem) * 1.15 and "step 1" not in answer.lower():
                flags.append("answer_echoes_stem_not_derived")

    if answer and _ANSWER_REPEATS_STEM_ONLY.match(answer) and "step" not in answer.lower():
        flags.append("answer_not_a_solution")

    critical = {
        "quadratic_math_verification_failed",
        "unicode_encoding_corruption",
        "false_tan_a_plus_b_formula",
        "false_tan_multiple_angle_identity",
        "compound_angle_B_undefined",
        "sympy_numeric_claim_false",
        "unverified_tan_triple_claim",
        "impossible_tan_chain",
        "impossible_triangle_angle",
        "tan_undefined_at_right_angle",
        "calculus_outside_trigonometry",
        "python_tuple_not_solution",
        "orphan_summation_symbol",
    }
    critical_hits = [f for f in flags if f in critical]
    critical_hits = list(dict.fromkeys(critical_hits + trig_sympy_critical))
    return {
        "math_stem_ok": len(critical_hits) == 0,
        "math_stem_flags": flags,
        "math_stem_critical": critical_hits,
        "trig_sympy_ok": len(trig_sympy_critical) == 0,
    }


def should_reject_math_stem(
    q: Dict[str, Any],
    *,
    locked_chapter: str = "",
) -> bool:
    return not evaluate_math_stem(q, locked_chapter=locked_chapter).get(
        "math_stem_ok", True
    )
