"""
Trigonometry full-hard stem gate — enforce 20 Hardest Trigonometry depth.

Gold reference (Q19, Section F): evaluate a sin² sum at π/8 family, then
Hence deduce Σ sin²(kπ/(2n+1)). Rejects board-medium one-liners on L5 papers.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Fusion / depth signals (trigonometry)
_TRIG_FUSION_SIGNALS: Tuple[Tuple[str, str], ...] = (
    (r"evaluate\s+exactly", "evaluate_exactly"),
    (r"\bhence\b", "hence_chain"),
    (r"\(i\).*\(ii\)", "multi_part"),
    (r"general\s+solution", "general_solution"),
    (r"how\s+many\s+(?:distinct\s+)?solutions", "interval_count"),
    (r"answer\s+one|\bor\s+\(i\)", "balanced_or"),
    (r"prove\s+that.*\bhence\b", "prove_hence"),
    (r"sin\s*[²^2].*cos\s*[²^2]|sin\^2.*cos\^2", "sin2_cos2"),
    (r"Σ|∑|\bsum\s+from\s+k\s*=\s*1", "series_sum"),
    (r"k\s*π\s*/\s*\(\s*2\s*n\s*\+\s*1\s*\)|kπ/\(2n\+1\)", "series_denominator"),
    (r"A\s*\+\s*B\s*\+\s*C\s*=\s*π", "conditional_pi"),
    (r"inverse|tan\s*[-−]?\s*1|sin\s*[-−]?\s*1", "inverse_trig"),
    (r"interval\s*\[|∈\s*\[0", "stated_interval"),
)

# Q19 gold: evaluate sin²(π/8)+…; Hence find Σ sin²(kπ/(2n+1))
_SERIES_GOLD_PATTERN = re.compile(
    r"sin\s*[²^2].*hence.*(?:sum|Σ|∑)",
    re.I | re.S,
)
_SERIES_GOLD_ALT = re.compile(
    r"evaluate\s+exactly.*sin\s*[²^2].*hence.*(?:k\s*π|2n\s*\+\s*1|\bn\b)",
    re.I | re.S,
)

_MIN_WORDS_DEFAULT = 30
_MIN_WORDS_SPARSE = 22
_MIN_FUSION_SCORE = 2
_MIN_FUSION_SCORE_SERIES_SLOT = 3


def fusion_signals(stem: str) -> List[str]:
    low = (stem or "").lower()
    hits: List[str] = []
    for pat, tag in _TRIG_FUSION_SIGNALS:
        if re.search(pat, low, re.I | re.S):
            hits.append(tag)
    return hits


def is_series_gold_stem(stem: str) -> bool:
    """True when stem matches Q19-style evaluate + Hence general sin² sum."""
    text = stem or ""
    if _SERIES_GOLD_PATTERN.search(text):
        return True
    if _SERIES_GOLD_ALT.search(text):
        return True
    low = text.lower()
    if not re.search(r"sin\s*[²^2]", low):
        return False
    if "hence" not in low:
        return False
    if not re.search(r"evaluate\s+exactly|find\s+the\s+exact\s+value", low):
        return False
    if not re.search(r"sum|Σ|∑|k\s*=\s*1", low):
        return False
    if not re.search(r"2n\s*\+\s*1|kπ|k\s*π", low):
        return False
    return True


def evaluate_trigonometry_full_hard_stem(
    stem: str,
    *,
    sparse_hard: bool = False,
    slot_meta: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Returns ok, fusion_score, flags for trigonometry chapter + full_hard UI.
    """
    meta = slot_meta or {}
    content = (stem or "").strip()
    low = content.lower()
    n_words = len(content.split())
    signals = fusion_signals(content)
    fusion_score = len(set(signals))
    flags: List[str] = []

    skill = (meta.get("skill") or "").upper()
    ref_slot = int(meta.get("ref_slot") or meta.get("slot") or 0)
    section = (meta.get("section") or "").upper()
    requires_series_gold = skill == "S-S" or ref_slot == 19 or section == "F"

    min_words = _MIN_WORDS_SPARSE if sparse_hard else _MIN_WORDS_DEFAULT
    if requires_series_gold:
        min_words = 14
    if n_words < min_words and not is_series_gold_stem(content):
        flags.append(f"trig_stem_too_short:{n_words}<{min_words}")

    min_fusion = _MIN_FUSION_SCORE_SERIES_SLOT if requires_series_gold else _MIN_FUSION_SCORE
    if fusion_score < min_fusion:
        flags.append(f"trig_insufficient_fusion:{fusion_score}<{min_fusion}")

    if requires_series_gold and not is_series_gold_stem(content):
        flags.append("trig_series_slot_not_q19_quality")

    # Thin drills
    if re.search(r"^find\s+(?:sin|cos|tan)\s", low) and fusion_score < 2:
        flags.append("trig_bare_value_find")
    if re.search(r"evaluate\s+exactly", low) and "hence" not in low:
        if re.search(r"sin\s*[²^2]", low):
            flags.append("trig_sin2_sum_without_hence_generalization")
    if re.search(r"prove\s+that", low) and "hence" not in low and "(ii)" not in low:
        if len(low.split()) < 35 and fusion_score < 2:
            flags.append("trig_proof_without_hence_or_depth")

    ok = not flags
    return {
        "trig_hard_stem_ok": ok,
        "trig_fusion_score": fusion_score,
        "trig_fusion_signals": signals,
        "trig_hard_stem_flags": flags,
        "trig_series_gold": is_series_gold_stem(content),
    }


def should_reject_trigonometry_full_hard_stem(
    stem: str,
    *,
    sparse_hard: bool = False,
    slot_meta: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[str]]:
    result = evaluate_trigonometry_full_hard_stem(
        stem, sparse_hard=sparse_hard, slot_meta=slot_meta
    )
    flags = result.get("trig_hard_stem_flags") or []
    return not result.get("trig_hard_stem_ok", True), list(flags)
