"""
Clean Q5 fusion values — tangent GH and secant GJ×GK with outer radius R from Q1.

Goals (board-friendly):
  GH² = OG² − R²  ideally a perfect square
  GK = GH² / GJ   integer
  JK = GK − GJ ≤ 2R  (secant chord feasible)
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Tuple

from app.generation.concentric_values import parse_concentric_radii
from app.generation.tangent_secant_values import _divisors

_FUSION_RE = re.compile(
    r"using\s+(?:the\s+)?outer\s+circle\s+from\s+question\s+1|"
    r"configuration\s+of\s+question\s+1",
    re.I,
)
_OG_RE = re.compile(
    r"\bpoint\s+G\s+is\s+(\d+(?:\.\d+)?)\s*cm\s+from\s+O\b",
    re.I,
)
_GJ_RE = re.compile(
    r"\bGJ\s*=\s*(\d+(?:\.\d+)?)\s*cm",
    re.I,
)
_PA_RE = re.compile(
    r"\btangent\s+([A-Z])([A-Z])\s*=\s*(\d+(?:\.\d+)?)\s*cm",
    re.I,
)


def _is_fusion_stem(stem: str) -> bool:
    low = (stem or "").lower()
    return bool(_FUSION_RE.search(stem)) and "hence" in low and bool(
        re.search(r"\(\s*i{1,2}\s*\)", stem, re.I)
    )


def parse_fusion_givens(stem: str) -> Optional[Dict[str, float]]:
    if not stem:
        return None
    og_m = _OG_RE.search(stem)
    gj_m = _GJ_RE.search(stem)
    if not og_m or not gj_m:
        return None
    return {"OG": float(og_m.group(1)), "GJ": float(gj_m.group(1))}


def _gh_sq(og: float, r: float) -> float:
    return og * og - r * r


def _score_pair(
    og: int, gj: int, r: float
) -> Optional[Tuple[int, int, int, int, int]]:
    """Return (score, og, gj, gh, gk) if feasible; else None."""
    if og <= r:
        return None
    diff = _gh_sq(og, r)
    if diff <= 0:
        return None
    gh_i = math.isqrt(int(diff))
    perfect_sq = gh_i * gh_i == int(diff)
    if gj <= 0 or int(diff) % gj != 0:
        return None
    gk = int(diff) // gj
    if gk <= gj:
        return None
    if gk - gj > 2 * r + 0.01:
        return None
    score = 0
    if perfect_sq:
        score += 100
    if gk <= 60:
        score += 20
    if gj in (6, 8, 9, 10, 12, 15, 16, 18):
        score += 10
    if og - r <= 12:
        score += 5
    return (score, og, gj, gh_i if perfect_sq else 0, gk)


def find_best_fusion_givens(
    outer_r: float,
    *,
    seed: int = 0,
) -> Tuple[int, int, int, int]:
    """Return (OG, GJ, GH, GK) with best cleanliness for fixed outer radius R."""
    r = float(outer_r)
    r_int = int(round(r))
    candidates: List[Tuple[int, int, int, int, int]] = []
    for og in range(r_int + 3, r_int + 55):
        for gj in range(3, 22):
            row = _score_pair(og, gj, r)
            if row:
                candidates.append(row)
    if not candidates:
        # Fallback: integer GK only (GH may be surd)
        og = r_int + 5
        diff = int(_gh_sq(og, r))
        for gj in sorted(_divisors(diff)):
            if 3 <= gj <= 20 and diff // gj > gj and (diff // gj) - gj <= 2 * r:
                return og, gj, math.isqrt(diff), diff // gj
        return r_int + 6, 9, 0, 35

    # Prefer score, board-style GJ ≈ 9, then larger integer GK, then moderate OG
    candidates.sort(key=lambda x: (-x[0], abs(x[2] - 9), -x[4], x[1]))
    idx = abs(seed) % min(3, len(candidates))
    _, og, gj, gh, gk = candidates[idx]
    return og, gj, gh, gk


def fusion_values_are_clean(outer_r: float, og: float, gj: float) -> bool:
    """True when OG/GJ match the best board-friendly pair for this outer radius."""
    diff = _gh_sq(og, outer_r)
    if diff <= 0:
        return False
    gj_i = int(round(gj))
    og_i = int(round(og))
    if int(diff) % gj_i != 0:
        return False
    gk = int(diff) // gj_i
    if gk <= gj_i or gk - gj_i > 2 * outer_r + 0.01:
        return False
    best_og, best_gj, _, _ = find_best_fusion_givens(outer_r, seed=0)
    return og_i == best_og and gj_i == best_gj


def repair_fusion_q5_stem(
    stem: str,
    outer_r: float,
    *,
    seed: int = 0,
) -> Tuple[str, bool]:
    """Replace OG / GJ in fusion Q5 when GK is decimal or GH² is messy."""
    if not _is_fusion_stem(stem) or outer_r <= 0:
        return stem, False
    parsed = parse_fusion_givens(stem)
    if parsed and fusion_values_are_clean(outer_r, parsed["OG"], parsed["GJ"]):
        return stem, False

    og, gj, gh, gk = find_best_fusion_givens(outer_r, seed=seed)
    new = stem
    if _OG_RE.search(new):
        new = _OG_RE.sub(f"point G is {og} cm from O", new, count=1)
    if _GJ_RE.search(new):
        new = _GJ_RE.sub(f"GJ = {gj} cm", new, count=1)
    return new, new != stem


def outer_radius_from_paper(q1_stem: str) -> Optional[float]:
    parsed = parse_concentric_radii(q1_stem or "")
    if parsed:
        return max(parsed[0], parsed[1])
    m = re.search(r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm", q1_stem or "", re.I)
    if m:
        return max(float(m.group(1)), float(m.group(2)))
    return None
