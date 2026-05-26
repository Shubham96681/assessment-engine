"""
Quadratic full-hard stem gate — reject NCERT drill stems on L5 papers.

A stem passes only if it chains ≥2 independent targets (fusion), not one skill.
"""
from __future__ import annotations

import re
from typing import List, Tuple

# Each pattern is one fusion / depth signal (not mutually exclusive).
_FUSION_SIGNALS: Tuple[Tuple[str, str], ...] = (
    (r"without\s+solv", "without_solving"),
    (r"\(i\).*\(ii\)", "multi_part"),
    (r"answer\s+one|\bor\s+\(ii\)|\(a\).*\bor.*\(b\)", "balanced_or"),
    (r"hence\s+.*(?:find|verify|show|form|obtain|state)", "hence_chain"),
    (r"form\s+(?:the\s+)?quadratic", "form_equation"),
    (r"sum\s+of\s+(?:the\s+)?squares", "sum_of_squares"),
    (r"roots?\s+(?:differ|reciprocal|reciprocals)", "root_relation"),
    (r"both\s+(?:distinct\s+)?(?:real\s+)?roots?\s+(?:are\s+)?positive", "root_sign_condition"),
    (r"α²\s*\+\s*β²|alpha\^2\s*\+\s*beta\^2", "alpha_beta_squares"),
    (r"greatest\s+integer|least\s+integer|all\s+(?:real\s+)?values\s+of", "parameter_interval"),
    (r"reject\s+(?:the\s+)?(?:negative|invalid)|valid\s+(?:length|breadth|dimension|root)", "reject_root"),
    (r"integer\s+coefficients.*roots?\s+are", "form_from_roots"),
    (r"reversed|two[\s-]digit|consecutive", "word_fusion"),
    (r"speed.*(?:longer|hour)|stream|upstream|downstream", "speed_time"),
)

_MIN_WORDS_DEFAULT = 32
_MIN_WORDS_SPARSE = 22
_MIN_FUSION_SCORE = 2


def fusion_signals(stem: str) -> List[str]:
    low = (stem or "").lower()
    hits: List[str] = []
    for pat, tag in _FUSION_SIGNALS:
        if re.search(pat, low, re.I | re.S):
            hits.append(tag)
    return hits


def evaluate_quadratic_full_hard_stem(
    stem: str,
    *,
    sparse_hard: bool = False,
) -> dict:
    """
    Returns ok, fusion_score, flags for quadratic chapter + full_hard UI.
    """
    content = (stem or "").strip()
    n_words = len(content.split())
    signals = fusion_signals(content)
    fusion_score = len(set(signals))
    flags: List[str] = []

    min_words = _MIN_WORDS_SPARSE if sparse_hard else _MIN_WORDS_DEFAULT
    if n_words < min_words:
        flags.append(f"quad_stem_too_short:{n_words}<{min_words}")

    if fusion_score < _MIN_FUSION_SCORE:
        flags.append(f"quad_insufficient_fusion:{fusion_score}<{_MIN_FUSION_SCORE}")

    # Single-skill drills (always fail full-hard)
    low = content.lower()
    if re.search(r"^find\s+(?:the\s+)?value\s+of\s+[kp]\b", low) and fusion_score < 2:
        flags.append("quad_thin_parameter_find")
    if re.search(r"^solve\s+.*by\s+factoris", low) and fusion_score < 2:
        flags.append("quad_bare_factorisation")
    if re.search(r"^factoris", low) and "hence" not in low and "(ii)" not in low:
        flags.append("quad_bare_factorisation")

    ok = not flags
    return {
        "quadratic_hard_stem_ok": ok,
        "quadratic_fusion_score": fusion_score,
        "quadratic_fusion_signals": signals,
        "quadratic_hard_stem_flags": flags,
    }


def should_reject_quadratic_full_hard_stem(
    stem: str,
    *,
    sparse_hard: bool = False,
) -> bool:
    return not evaluate_quadratic_full_hard_stem(stem, sparse_hard=sparse_hard).get(
        "quadratic_hard_stem_ok", True
    )
