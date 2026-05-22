"""
Stem dependency validation — referenced objects must appear in the stem or figure.

Catches: "the equation" without an equation, "find roots" without a polynomial, etc.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# ax² + bx + c = 0, 6x² − 7x − 20, kx² − 10x + 25
_POLY_RE = re.compile(
    r"(?:"
    r"\d*\s*[xX]\s*(?:\^|²|\u00b2)\s*[\+\-\u2212]?"  # quadratic term
    r"|[xX]\s*(?:\^|²|\u00b2)\s*[\+\-\u2212]?"
    r"|\d+\s*[xX]\s*[\+\-\u2212]"
    r"|[xX]\s*[\+\-\u2212]\s*\d+"
    r")",
    re.I,
)
_EQUATION_RE = re.compile(
    r"(?:"
    r"[0-9xX\(\)]+\s*[\+\-\u2212]\s*[0-9xX\(\)]+\s*=\s*[0-9xX\(\)\?]+"
    r"|\d*\s*[xX]\s*(?:\^|²|\u00b2)\s*[\+\-\u2212][^.;]{0,40}=\s*0"
    r"|[xX]\([^)]+\)\s*=\s*\d+"
    r")",
    re.I,
)
_THE_EQUATION_RE = re.compile(
    r"\b(?:the|this|given|above)\s+equation\b|\bequation\s+itself\b",
    re.I,
)
_FIND_ROOTS_RE = re.compile(
    r"\bfind\s+(?:the\s+)?roots?\b|\bsolve\s+[^.]{0,30}\s+by\s+factor",
    re.I,
)
_VERIFY_RE = re.compile(
    r"\bverify\s+(?:by\s+)?substitution\b|\bcheck\s+substitution\b|\bconfirm\s+substitution\b",
    re.I,
)
_DISCRIMINANT_REF_RE = re.compile(
    r"\bdiscriminant\b|\b(?:nature\s+of\s+(?:the\s+)?roots?)\b",
    re.I,
)
_PARAM_K_RE = re.compile(
    r"\bparameter\s+k\b|\bvalue\s+of\s+k\b|\bfind\s+k\b|\bfor\s+k\b",
    re.I,
)


def _text_from_question(q: Dict[str, Any]) -> str:
    stem = (q.get("content") or q.get("question") or "").strip()
    spec = q.get("figure_spec") or {}
    extra: List[str] = []
    if isinstance(spec, dict):
        for row in spec.get("rows") or []:
            if isinstance(row, (list, tuple)):
                extra.extend(str(c) for c in row)
            else:
                extra.append(str(row))
        for h in spec.get("headers") or []:
            extra.append(str(h))
        for el in spec.get("elements") or []:
            if isinstance(el, dict):
                for k in ("label", "from", "to"):
                    v = el.get(k)
                    if v:
                        extra.append(str(v))
    return stem + " " + " ".join(extra)


def _has_explicit_polynomial(text: str) -> bool:
    if _EQUATION_RE.search(text):
        return True
    if _POLY_RE.search(text) and "=" in text:
        return True
    # compact: 6x² − 7x − 20 = 0 style without strict regex
    if re.search(
        r"[xX]\s*(?:\^|²|\u00b2).{0,30}=\s*0|[xX].{0,20}=\s*0",
        text,
        re.I,
    ):
        return True
    return bool(
        re.search(
            r"\b\d+\s*[xX]\s*[\+\-\u2212\u2212]\s*\d+\s*[xX]\s*[\+\-\u2212]",
            text,
        )
    )


def _has_word_model_givens(text: str) -> bool:
    """Area / speed / sum-product setups count as self-contained models."""
    low = text.lower()
    if re.search(r"\b\d+\s*(?:km|m|m²|m2|cm|h|min|hour)\b", text, re.I):
        if any(
            w in low
            for w in (
                "area",
                "breadth",
                "length",
                "speed",
                "apart",
                "product",
                "sum",
                "integers",
                "plot",
                "rectangle",
                "grove",
                "hall",
            )
        ):
            return True
    if re.search(r"breadth|length|area|speed|product|sum of squares", low):
        return re.search(r"\d+", text) is not None
    return False


def validate_stem_dependencies(q: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return dependency_score, stem_dependency_flags, stem_dependencies_ok.
    """
    text = _text_from_question(q)
    flags: List[str] = []
    score = 1.0

    if not text.strip():
        return {
            "dependency_score": 0.0,
            "stem_dependency_flags": ["empty_stem"],
            "stem_dependencies_ok": False,
        }

    has_poly = _has_explicit_polynomial(text)
    has_model = _has_word_model_givens(text)

    if _THE_EQUATION_RE.search(text) and not has_poly:
        flags.append("missing_equation_after_reference")
        score -= 0.55

    if _FIND_ROOTS_RE.search(text) and not has_poly and not has_model:
        flags.append("missing_polynomial_for_roots")
        score -= 0.5

    if _DISCRIMINANT_REF_RE.search(text) and not has_poly:
        flags.append("discriminant_without_equation")
        score -= 0.45

    if _PARAM_K_RE.search(text) and not has_poly:
        # "parameter k" must name the equation containing k
        if not re.search(r"[xX]\s*(?:\^|²|\u00b2)|\bk\s*[xX]|kx\s*(?:\^|²|\u00b2)", text, re.I):
            flags.append("parameter_k_without_equation")
            score -= 0.5

    if _VERIFY_RE.search(text):
        if not re.search(
            r"\b(?:root|value|x\s*=|k\s*=|repeated|that\s+k)\b",
            text,
            re.I,
        ) and not has_poly:
            flags.append("verify_without_target")
            score -= 0.35

    if re.search(r"\bthe\s+expression\b", text, re.I) and not has_poly:
        flags.append("missing_expression")
        score -= 0.4

    if re.search(r"\bthe\s+table\b|\bin the table\b", text, re.I):
        if not (q.get("figure_spec") or {}).get("rows"):
            flags.append("table_reference_without_spec")
            score -= 0.25

    dep_score = max(0.0, min(1.0, score))
    return {
        "dependency_score": round(dep_score, 3),
        "stem_dependency_flags": flags,
        "stem_dependencies_ok": dep_score >= 0.62 and "missing_equation" not in " ".join(
            flags
        ),
    }


def should_reject_stem_dependencies(q: Dict[str, Any]) -> bool:
    if "dependency_score" not in q:
        q.update(validate_stem_dependencies(q))
    flags = q.get("stem_dependency_flags") or []
    critical = {
        "missing_equation_after_reference",
        "missing_polynomial_for_roots",
        "discriminant_without_equation",
        "parameter_k_without_equation",
        "missing_expression",
        "empty_stem",
    }
    if any(f in critical for f in flags):
        return True
    return not q.get("stem_dependencies_ok", True)
