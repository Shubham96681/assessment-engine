"""
M.Tech-level (L8–L9) stem gate for quadratic chapter at 100% hard UI.
"""
from __future__ import annotations

import re
from typing import List

from app.generation.quadratic_hard_stem_gate import fusion_signals

_MIN_WORDS = 42
_MIN_FUSION = 2

_MTECH_SIGNALS: tuple[tuple[str, str], ...] = (
    (r"prove\s+that\s+(?:no|there)", "existence_proof"),
    (r"no\s+quadratic", "impossibility"),
    (r"for\s+all\s+real|for\s+every\s+real|family\s+of", "parameter_family"),
    (r"consider\s+the\s+family|as\s+\w+\s+varies", "parameter_family"),
    (r"construct\s+a\s+quadratic|construct\s+.*equation", "constructive"),
    (r"whose\s+roots\s+are\s+α", "recursive_roots"),
    (r"α²\s*\+\s*β².*α³", "recursive_roots"),
    (r"minimum\s+possible\s+value|maximum\s+possible\s+value", "optimization"),
    (r"subject\s+to.*D\s*≥\s*0|discriminant\s*≥\s*0", "domain_optimization"),
    (r"impossib|contradiction", "proof_meta"),
    (r"without\s+(?:finding|solving)\s+(?:the\s+)?roots", "without_roots"),
    (r"without\s+finding\s+α|without\s+solving\s+for\s+α", "without_roots"),
    (r"necessary\s+and\s+sufficient|if\s+and\s+only\s+if", "iff_conditions"),
    (r"p_n\s*=|p_\{?n\}?|recurrence", "recursive_roots"),
    (r"recover\s+the\s+(?:monic\s+)?equation|reverse", "reverse_engineer"),
    (r"lie\s+in\s+(?:the\s+)?(?:closed\s+)?interval|both\s+roots\s+in", "domain_optimization"),
)

_BANNED_MTECH = (
    r"^solve\s+\d*x²",
    r"^find\s+the\s+value\s+of\s+[kp]\b",
    r"by\s+factoris(?:ation|ing)\s+only.*solve",
    r"find\s+the\s+discriminant",
    r"^factoris(?:e|e)\s+completely",
)


def mtech_signals(stem: str) -> List[str]:
    low = (stem or "").lower()
    hits: List[str] = []
    for pat, tag in _MTECH_SIGNALS:
        if re.search(pat, low, re.I):
            hits.append(tag)
    hits.extend(fusion_signals(stem))
    return list(dict.fromkeys(hits))


def evaluate_quadratic_mtech_stem(
    stem: str,
    *,
    sparse_hard: bool = False,
) -> dict:
    content = (stem or "").strip()
    n_words = len(content.split())
    signals = mtech_signals(content)
    fusion_score = len(set(signals))
    flags: List[str] = []
    low = content.lower()

    min_words = 28 if sparse_hard else _MIN_WORDS
    if n_words < min_words:
        flags.append(f"mtech_stem_too_short:{n_words}<{min_words}")

    if fusion_score < _MIN_FUSION:
        flags.append(f"mtech_insufficient_depth:{fusion_score}<{_MIN_FUSION}")

    mtech_tags = {t for t in signals if not t.startswith("quad_")}
    depth_tags = {
        "existence_proof",
        "impossibility",
        "parameter_family",
        "constructive",
        "recursive_roots",
        "optimization",
        "domain_optimization",
        "proof_meta",
        "without_roots",
        "iff_conditions",
        "reverse_engineer",
    }
    if not (mtech_tags & depth_tags):
        flags.append("mtech_missing_archetype_signal")

    for pat in _BANNED_MTECH:
        if re.search(pat, low, re.I):
            flags.append(f"mtech_board_drill:{pat}")
            break

    ok = not flags
    return {
        "quadratic_hard_stem_ok": ok,
        "quadratic_fusion_score": fusion_score,
        "quadratic_fusion_signals": signals,
        "quadratic_hard_stem_flags": flags,
        "mtech_stem_ok": ok,
        "difficulty_band": "L8" if ok else "below_L8",
    }


def should_reject_quadratic_mtech_stem(stem: str, *, sparse_hard: bool = False) -> bool:
    return not evaluate_quadratic_mtech_stem(stem, sparse_hard=sparse_hard).get(
        "mtech_stem_ok", True
    )
