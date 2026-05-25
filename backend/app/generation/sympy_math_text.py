"""
Format embedded math in exam stems using SymPy Unicode symbols.

Keeps prose unchanged; rewrites parseable trig / Greek / relation fragments
to consistent Unicode (θ, π, ≤, sin(5⋅θ), etc.) for UI and PDF.

"""
from __future__ import annotations

import re
from typing import Callable, Dict, Optional

_SYM = None
_FUNCS: Dict[str, Callable] = {}


def _ensure_sympy() -> bool:
    global _SYM, _FUNCS
    if _SYM is not None:
        return bool(_FUNCS)
    try:
        import sympy as sp
        from sympy.abc import theta as th
        from sympy.parsing.sympy_parser import (
            convert_xor,
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )
        from sympy.printing.pretty import pretty

        _SYM = {
            "sp": sp,
            "parse_expr": parse_expr,
            "pretty": pretty,
            "theta": th,
            "pi": sp.pi,
            "transformations": standard_transformations
            + (implicit_multiplication_application, convert_xor),
        }
        _FUNCS = {
            "sin": sp.sin,
            "cos": sp.cos,
            "tan": sp.tan,
            "sec": sp.sec,
            "cosec": sp.csc,
            "cot": sp.cot,
        }
        return True
    except ImportError:
        _SYM = {}
        _FUNCS = {}
        return False


def _local_dict() -> Dict:
    sp = _SYM["sp"]
    d = {c: sp.Symbol(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
    d["theta"] = _SYM["theta"]
    d["pi"] = _SYM["pi"]
    return d


def _parse_stem_expr(fragment: str):
    if not _ensure_sympy():
        return None
    s = (
        fragment.strip()
        .replace("θ", "theta")
        .replace("π", "pi")
        .replace("−", "-")
        .replace("×", "*")
        .replace("°", "")
    )
    if not s:
        return None
    try:
        return _SYM["parse_expr"](
            s,
            local_dict=_local_dict(),
            transformations=_SYM["transformations"],
            evaluate=True,
        )
    except Exception:
        return None


def _pretty_inline(expr) -> str:
    """Single-line Unicode pretty print suitable for exam stems."""
    if not _ensure_sympy():
        return str(expr)
    raw = _SYM["pretty"](expr, use_unicode=True, wrap_line=False)
    out = raw.replace("\n", " ")
    out = re.sub(r"π\s*─\s*(\d+)", r"π/\1", out)
    out = re.sub(r"(\d+)\s*─\s*(\d+)", r"\1/\2", out)
    out = out.replace("⋅", "")
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _rewrite_func_parens(m: re.Match[str]) -> str:
    name = m.group(1).lower()
    inner = m.group(2)
    fn = _FUNCS.get(name)
    if not fn:
        return m.group(0)
    arg = _parse_stem_expr(inner)
    if arg is None:
        return m.group(0)
    return _pretty_inline(fn(arg))


def _rewrite_func_spaced(m: re.Match[str]) -> str:
    name = m.group(1).lower()
    coeff = m.group(2)
    var = m.group(3)
    fn = _FUNCS.get(name)
    if not fn:
        return m.group(0)
    var_sym = _SYM["theta"] if var.lower() in ("θ", "theta") else _SYM["sp"].Symbol(var)
    arg = _SYM["sp"].Integer(int(coeff)) * var_sym
    return _pretty_inline(fn(arg))


def _rewrite_func_power(m: re.Match[str]) -> str:
    name = m.group(1).lower()
    var = m.group(2)
    fn = _FUNCS.get(name)
    if not fn:
        return m.group(0)
    var_sym = _SYM["theta"] if var.lower() in ("θ", "theta") else _SYM["sp"].Symbol(var)
    return _pretty_inline(fn(var_sym) ** 2)


def _rewrite_pi_frac(m: re.Match[str]) -> str:
    num_s, den_s = m.group(1), m.group(2)
    if not _ensure_sympy() or not den_s:
        return m.group(0)
    sp = _SYM["sp"]
    try:
        den = int(den_s)
        if num_s:
            expr = sp.Rational(int(num_s), den) * sp.pi
        else:
            expr = sp.pi / den
        return _pretty_inline(expr)
    except Exception:
        return m.group(0)


def _rewrite_relation(m: re.Match[str]) -> str:
    if not _ensure_sympy():
        return m.group(0)
    sp = _SYM["sp"]
    left = _parse_stem_expr(m.group(1))
    op = m.group(2)
    right = _parse_stem_expr(m.group(3))
    if left is None or right is None:
        return m.group(0)
    try:
        if op in ("<=", "≤"):
            expr = left <= right
        elif op in (">=", "≥"):
            expr = left >= right
        elif op in ("!=", "≠", "/="):
            expr = sp.Ne(left, right)
        else:
            return m.group(0)
        return _pretty_inline(expr)
    except Exception:
        return m.group(0)


_FUNC_PARENS = re.compile(
    r"\b(sin|cos|tan|sec|cosec|cot)\s*\(\s*([^()]+)\s*\)",
    re.I,
)
_FUNC_SPACED = re.compile(
    r"\b(sin|cos|tan|sec|cosec|cot)\s+(\d+)\s*(θ|theta)\b",
    re.I,
)
_FUNC_POWER = re.compile(
    r"\b(sin|cos|tan|sec|cosec|cot)[²2]\s*(θ|theta|[A-Z])\b",
    re.I,
)
_PI_FRAC_UNICODE = re.compile(r"(?:(\d+)\s*)?π\s*/\s*(\d+)")
_PI_FRAC_ASCII = re.compile(r"(?:(\d+)\s*)?pi\s*/\s*(\d+)", re.I)
_RELATION = re.compile(
    r"([0-9A-Za-zθπ+\-*/\s^²]+?)\s*(<=|>=|≤|≥|!=|≠)\s*([0-9A-Za-zθπ+\-*/\s^²]+)",
    re.I,
)

_FIND_ANGLE = re.compile(r"\bfind\s+angle\s+([A-Z]{1,4}|[θΘ])\b", re.I)
_ANGLE_VERTEX = re.compile(
    r"\bangle\s+([A-Z]{1,4}|[θΘ])(?=\s*(?:=|\+|-|\-|−|°|,|\.|\)|/|\s+and\s+(?:angle|∠)|\s*\+\s*(?:angle|∠)|\s+lies\b|\s+in\s+quadrant))",
    re.I,
)
_LATEX_ANGLE = re.compile(r"\\angle\s*\{?\s*([A-Za-zθΘ]{1,4})\s*\}?", re.I)

def normalize_angle_notation(text: str) -> str:
    """Vertex angles as ∠ (geometry; not SymPy's trig Symbol)."""
    if not text or "angle" not in text.lower():
        return text
    out = _FIND_ANGLE.sub(lambda m: f"find \u2220{m.group(1)}", text)
    out = _ANGLE_VERTEX.sub(lambda m: f"\u2220{m.group(1)}", out)
    return out


def apply_sympy_math_symbols(text: str) -> str:
    """Rewrite parseable math fragments with SymPy Unicode symbols."""
    if not text or not _ensure_sympy():
        return normalize_angle_notation(text)
    out = _LATEX_ANGLE.sub(lambda m: f"\u2220{m.group(1)}", text)
    out = _FUNC_PARENS.sub(_rewrite_func_parens, out)
    out = _FUNC_SPACED.sub(_rewrite_func_spaced, out)
    out = _FUNC_POWER.sub(_rewrite_func_power, out)
    out = _PI_FRAC_UNICODE.sub(_rewrite_pi_frac, out)
    out = _PI_FRAC_ASCII.sub(_rewrite_pi_frac, out)
    out = _RELATION.sub(_rewrite_relation, out)
    out = re.sub(r"\btheta\b", "θ", out, flags=re.I)
    out = re.sub(r"\bpi\b(?!\s*/)", "π", out, flags=re.I)
    return normalize_angle_notation(out)


def sympy_available() -> bool:
    return _ensure_sympy()
