"""
Clean concentric-circle radii — R² − r² must be a perfect square for integer chords.
"""
from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

_RADII_RE = re.compile(
    r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm",
    re.I,
)


def chord_half_length(outer: float, inner: float) -> float:
    return math.sqrt(max(0.0, outer * outer - inner * inner))


def is_perfect_square_chord_pair(outer: float, inner: float) -> bool:
    if outer <= inner:
        return False
    d = outer * outer - inner * inner
    if d < 0:
        return False
    root = math.isqrt(int(round(d)))
    return abs(root * root - d) < 1e-6


def parse_concentric_radii(stem: str) -> Optional[Tuple[float, float]]:
    m = _RADII_RE.search(stem or "")
    if not m:
        return None
    a, b = float(m.group(1)), float(m.group(2))
    return (max(a, b), min(a, b))


# Board-friendly pairs (R, r) → chord = 2√(R²−r²) integer
RECOMMENDED_PAIRS: List[Tuple[int, int, int]] = [
    (17, 8, 30),
    (10, 6, 16),
    (13, 5, 24),
    (15, 9, 24),
    (25, 7, 48),
]


def validate_concentric_clean_values(
    stem: str,
    *,
    require_integer_chord: bool = True,
) -> Tuple[bool, List[str]]:
    """Flag stems where R² − r² is not a perfect square (messy surd answers)."""
    parsed = parse_concentric_radii(stem)
    if not parsed:
        return True, []
    outer, inner = parsed
    flags: List[str] = []
    if not is_perfect_square_chord_pair(outer, inner):
        flags.append(
            f"concentric_not_perfect_square:R={outer}_r={inner}_diff={outer**2-inner**2:.0f}"
        )
    elif require_integer_chord:
        half = chord_half_length(outer, inner)
        if abs(half - round(half)) > 0.01:
            flags.append(f"concentric_chord_not_integer_half:{half:.2f}")
    return (not flags, flags)
