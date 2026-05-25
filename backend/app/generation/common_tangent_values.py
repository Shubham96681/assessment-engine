"""
Board-friendly two-circle external tangent triples.

Direct common external tangent exists iff d > r_large + r_small (separate circles).
Clean integer length: EF = sqrt(d² − (r_large − r_small)²).
"""
from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

_EXTERNAL_TANGENT_RE = re.compile(
    r"\b(?:direct\s+)?common\s+external\s+tangent\b|"
    r"\bexternal\s+tangent\b.*\bboth\s+circles\b",
    re.I,
)
_RADII_PAIR_RE = re.compile(
    r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm",
    re.I,
)
_CENTRE_DIST_RE = re.compile(
    r"\b([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)\s*cm",
)
_CENTRES_RE = re.compile(
    r"\bcentres?\s+([A-Z])\s+and\s+([A-Z])\b",
    re.I,
)


def external_tangent_length(r_small: float, r_large: float, d: float) -> float:
    """Length of direct common external tangent (r_small ≤ r_large)."""
    return math.sqrt(max(0.0, d * d - (r_large - r_small) ** 2))


def is_valid_external_tangent_geometry(
    r_small: float, r_large: float, d: float
) -> bool:
    """
    Separate circles with a direct common external tangent.
    Requires d > r_large + r_small (not intersecting, not nested).
    """
    if r_small < 0 or r_large < r_small:
        return False
    if d <= r_large + r_small:
        return False
    if d <= r_large - r_small:
        return False
    return True


def validate_external_tangent_triple(
    r1: float, r2: float, d: float,
) -> Tuple[bool, str]:
    rs, rl = min(r1, r2), max(r1, r2)
    if d <= rl - rs:
        return False, "one_circle_inside_other"
    if d <= rl + rs:
        return False, "circles_intersect_no_external_tangent"
    return True, ""


def is_clean_external_tangent_triple(r1: float, r2: float, d: float) -> bool:
    rs, rl = min(r1, r2), max(r1, r2)
    if not is_valid_external_tangent_geometry(rs, rl, d):
        return False
    ef = external_tangent_length(rs, rl, d)
    return abs(ef - round(ef)) < 1e-6 and ef > 0


def _build_recommended_triples() -> List[Tuple[int, int, int, int]]:
    """(r_small, r_large, d, EF) — only geometrically valid external tangents."""
    out: List[Tuple[int, int, int, int]] = []
    seen: set[Tuple[int, int, int]] = set()
    for d in range(6, 30):
        for r_small in range(2, 11):
            for r_large in range(r_small + 1, 12):
                if not is_clean_external_tangent_triple(r_small, r_large, d):
                    continue
                ef = int(round(external_tangent_length(r_small, r_large, d)))
                key = (r_small, r_large, d)
                if key in seen:
                    continue
                seen.add(key)
                out.append((r_small, r_large, d, ef))
    priority = [(3, 8, 13, 12), (5, 12, 20, 16), (4, 7, 14, 10), (3, 5, 11, 8)]
    ordered: List[Tuple[int, int, int, int]] = []
    for p in priority:
        if p in out:
            ordered.append(p)
    for t in sorted(out, key=lambda x: (-x[3], x[2])):
        if t not in ordered:
            ordered.append(t)
    return ordered[:24]


RECOMMENDED_EXTERNAL_TANGENT: List[Tuple[int, int, int, int]] = _build_recommended_triples()


def is_common_external_tangent_stem(stem: str) -> bool:
    return bool(_EXTERNAL_TANGENT_RE.search(stem or ""))


def parse_external_tangent_givens(stem: str) -> Optional[Tuple[float, float, float]]:
    """Return (r_small, r_large, centre_distance) if all present."""
    if not stem:
        return None
    radii = _RADII_PAIR_RE.search(stem)
    dist_m = _CENTRE_DIST_RE.search(stem)
    if not radii or not dist_m:
        return None
    a, b = float(radii.group(1)), float(radii.group(2))
    d = float(dist_m.group(2))
    return (min(a, b), max(a, b), d)


def stem_has_valid_external_tangent_givens(stem: str) -> bool:
    if not is_common_external_tangent_stem(stem):
        return True
    parsed = parse_external_tangent_givens(stem)
    if not parsed:
        return False
    return validate_external_tangent_triple(*parsed)[0]


def stem_has_required_external_tangent_givens(stem: str) -> bool:
    if not is_common_external_tangent_stem(stem):
        return True
    return parse_external_tangent_givens(stem) is not None


def pick_external_tangent_triple(seed: int = 0) -> Tuple[int, int, int, int]:
    if not RECOMMENDED_EXTERNAL_TANGENT:
        return (3, 8, 13, 12)
    idx = abs(seed) % len(RECOMMENDED_EXTERNAL_TANGENT)
    return RECOMMENDED_EXTERNAL_TANGENT[idx]


def build_external_tangent_stem(
    c1: str,
    c2: str,
    r_small: int,
    r_large: int,
    dist: int,
    *,
    tangent_labels: Tuple[str, str] = ("E", "F"),
) -> str:
    e, f = tangent_labels
    return (
        f"Circles with centres {c1} and {c2} have radii {r_small} cm and {r_large} cm "
        f"respectively. If {c1}{c2} = {dist} cm, find the length of the direct common "
        f"external tangent {e}{f} touching both circles."
    )


def _extract_centre_labels(stem: str) -> Tuple[str, str]:
    centres = _CENTRES_RE.search(stem)
    c1 = centres.group(1).upper() if centres else "G"
    c2 = centres.group(2).upper() if centres else "H"
    if c1 == c2:
        c2 = "H" if c1 != "H" else "G"
    return c1, c2


def repair_external_tangent_stem(
    stem: str,
    *,
    seed: int = 0,
) -> Tuple[str, bool]:
    """
    Inject or replace radii + centre distance for common-external-tangent stems.
    Fixes missing givens and impossible geometry (d ≤ r₁ + r₂).
    """
    if not is_common_external_tangent_stem(stem):
        return stem, False

    parsed = parse_external_tangent_givens(stem)
    if parsed and stem_has_valid_external_tangent_givens(stem):
        return stem, False

    c1, c2 = _extract_centre_labels(stem)
    r_small, r_large, dist, _ = pick_external_tangent_triple(seed)
    return build_external_tangent_stem(c1, c2, r_small, r_large, dist), True
