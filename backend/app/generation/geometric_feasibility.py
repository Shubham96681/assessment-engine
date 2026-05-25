"""
Geometric feasibility — secant chord length, external point, tangent existence.

Catches impossible configurations (e.g. secant chord PQ > diameter 2R).
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.numeric_constraint_validator import REL_TOL, _rel_close

_CM = re.compile(r"(\d+(?:\.\d+)?)\s*cm", re.I)


def _text(q: Dict[str, Any]) -> str:
    return f"{q.get('content') or q.get('question') or ''} {q.get('correct_answer') or ''}"


def _seg_len(text: str, seg: str) -> Optional[float]:
    m = re.search(rf"\b{re.escape(seg)}\s*=\s*(\d+(?:\.\d+)?)\s*cm", text, re.I)
    return float(m.group(1)) if m else None


def _centre_dist(text: str, centre: str, pt: str) -> Optional[float]:
    seg = f"{centre}{pt}"
    for pat in (
        rf"\b{re.escape(seg)}\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        rf"\b{centre}{pt}\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        rf"\b{centre}\s*{pt}\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        rf"\bpoint\s+{pt}\s+with\s+{re.escape(seg)}\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        rf"\b{pt}\s+with\s+{re.escape(seg)}\s*=\s*(\d+(?:\.\d+)?)\s*cm",
    ):
        m = re.search(pat, text, re.I)
        if m:
            return float(m.group(1))
    m = re.search(
        rf"\b{centre}\s*=\s*(\d+(?:\.\d+)?)\s*cm.*\b{pt}\b",
        text,
        re.I,
    )
    if m:
        return float(m.group(1))
    return None


def _infer_outer_radius(text: str, paper_r: Optional[float]) -> Optional[float]:
    if paper_r is not None:
        return paper_r
    m = re.search(
        r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm",
        text,
        re.I,
    )
    if m:
        return max(float(m.group(1)), float(m.group(2)))
    m2 = re.search(r"\bouter\s+radius\s+(\d+(?:\.\d+)?)\s*cm", text, re.I)
    if m2:
        return float(m2.group(1))
    nums = [float(x.group(1)) for x in _CM.finditer(text)]
    if "concentric" in text.lower() and len(nums) >= 2:
        return max(nums[0], nums[1])
    return None


def secant_chord_from_power(
    tangent_len: float, near_seg: float
) -> Tuple[float, float]:
    """External point: WQ = WT²/WP, internal chord PQ = WQ − WP."""
    if near_seg <= 0:
        return 0.0, 0.0
    wq = (tangent_len * tangent_len) / near_seg
    pq = wq - near_seg
    return wq, pq


def min_near_segment_for_secant(tangent_len_sq: float, radius: float) -> float:
    """Smallest WP ≥ 0 with PQ = WT²/WP − WP ≤ 2R."""
    r = radius
    t2 = tangent_len_sq
    # WP² + 2R·WP − t² ≥ 0  →  WP ≥ (−2R + √(4R²+4t²))/2
    disc = 4 * r * r + 4 * t2
    if disc < 0:
        return float("inf")
    return (-2 * r + math.sqrt(disc)) / 2


def validate_secant_feasibility(
    *,
    radius: float,
    centre_dist: float,
    tangent_len: float,
    near_seg: float,
) -> Tuple[bool, List[str]]:
    flags: List[str] = []
    if centre_dist <= radius:
        flags.append(f"external_point_inside_circle:d={centre_dist}<=R={radius}")
    if tangent_len < 0:
        flags.append("negative_tangent_length")
    exp_t = math.sqrt(max(0, centre_dist * centre_dist - radius * radius))
    if exp_t > 0 and not _rel_close(tangent_len, exp_t, REL_TOL):
        flags.append(
            f"tangent_length_infeasible:stated={tangent_len:.2f},max={exp_t:.2f}"
        )
    wq, pq = secant_chord_from_power(tangent_len, near_seg)
    if pq > 2 * radius * (1 + REL_TOL):
        flags.append(
            f"secant_chord_exceeds_diameter:PQ={pq:.2f}>2R={2*radius:.2f}"
        )
    min_wp = min_near_segment_for_secant(tangent_len * tangent_len, radius)
    if near_seg + 1e-6 < min_wp:
        flags.append(
            f"secant_near_segment_too_small:WP={near_seg:.2f}<min_{min_wp:.2f}"
        )
    return (len(flags) == 0, flags)


def _parse_secant_config(
    text: str, *, outer_r: Optional[float], centre: str = "A"
) -> List[Dict[str, float]]:
    """Find tangent+secant configs in stem (WT, WP, AW, etc.)."""
    configs: List[Dict[str, float]] = []
    r = _infer_outer_radius(text, outer_r)
    if r is None:
        return configs

    # Pattern: tangent WT = t, secant ... WP = p, AW = d
    tangent_segs = re.findall(
        r"\btangent\s+(?:length\s+)?([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)\s*cm",
        text,
        re.I,
    )
    if not tangent_segs:
        m_t = re.search(
            r"\btangent\s+length\s+([A-Z]{2})\b",
            text,
            re.I,
        )
        m_len = re.search(
            r"\b([A-Z]{2})\s*=\s*4\s*√\s*21\s*cm|WT\s*=\s*4\s*√\s*21",
            text,
            re.I,
        )
        if m_t:
            tseg = m_t.group(1).upper()
            ans = text.lower()
            if "336" in ans or "4√21" in ans.replace(" ", ""):
                tangent_segs = [(tseg, str(math.sqrt(336)))]
    for tseg, tlen in tangent_segs:
        ext = tseg[0]
        contact = tseg[1]
        tlen_f = float(tlen)
        od = _centre_dist(text, centre, ext) or _centre_dist(text, "O", ext)
        near = None
        for m in re.finditer(rf"\b([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)\s*cm", text, re.I):
            seg = m.group(1).upper()
            if seg[0] == ext and seg != tseg:
                ctx = text[max(0, m.start() - 40) : m.end() + 20].lower()
                if "nearer" in ctx or "secant" in ctx:
                    near = float(m.group(2))
                    break
        if near is not None and od is not None:
            configs.append(
                {
                    "R": r,
                    "OD": od,
                    "tangent": tlen_f,
                    "near": near,
                    "ext": ext,
                }
            )
    return configs


def validate_geometric_feasibility(
    q: Dict[str, Any],
    *,
    outer_radius: Optional[float] = None,
    centre_label: str = "A",
) -> Dict[str, Any]:
    text = _text(q)
    flags: List[str] = []
    ok = True

    r = _infer_outer_radius(text, outer_radius)
    if r and "concentric" in text.lower():
        nums = [float(m.group(1)) for m in _CM.finditer(text)]
        if len(nums) >= 2:
            ro, ri = max(nums[0], nums[1]), min(nums[0], nums[1])
            if ro <= ri:
                flags.append("concentric_radii_invalid")
                ok = False
            from app.generation.concentric_values import is_perfect_square_chord_pair

            if not is_perfect_square_chord_pair(ro, ri):
                flags.append(
                    f"concentric_radii_not_perfect_square:R={ro}_r={ri}_diff={ro*ro-ri*ri:.0f}"
                )
                ok = False

    from app.generation.common_tangent_values import (
        is_common_external_tangent_stem,
        parse_external_tangent_givens,
        validate_external_tangent_triple,
    )

    if is_common_external_tangent_stem(text):
        parsed = parse_external_tangent_givens(text)
        if parsed:
            valid, reason = validate_external_tangent_triple(*parsed)
            if not valid:
                flags.append(f"external_tangent_{reason}")
                ok = False

    for cfg in _parse_secant_config(text, outer_r=r, centre=centre_label):
        feas, f = validate_secant_feasibility(
            radius=cfg["R"],
            centre_dist=cfg["OD"],
            tangent_len=cfg["tangent"],
            near_seg=cfg["near"],
        )
        if not feas:
            flags.extend(f)
            ok = False

    # Answer claims WQ / GH that imply impossible chord
    ans = (q.get("correct_answer") or "").lower()
    m_wq = re.search(r"\bwq\s*=\s*(\d+(?:\.\d+)?)\s*cm", ans, re.I)
    m_wp = re.search(r"\bwp\s*=\s*(\d+(?:\.\d+)?)\s*cm", ans, re.I)
    if m_wq and m_wp and r:
        wq, wp = float(m_wq.group(1)), float(m_wp.group(1))
        pq = wq - wp
        if pq > 2 * r * (1 + REL_TOL):
            flags.append(f"answer_secant_chord_exceeds_diameter:PQ={pq:.2f}>2R={2*r:.2f}")
            ok = False

    return {
        "geometric_feasibility_ok": ok,
        "geometric_feasibility_flags": flags,
    }


def should_reject_geometric_infeasibility(
    q: Dict[str, Any],
    *,
    outer_radius: Optional[float] = None,
) -> bool:
    if "geometric_feasibility_ok" not in q:
        q.update(validate_geometric_feasibility(q, outer_radius=outer_radius))
    if not q.get("geometric_feasibility_ok", True):
        return True
    critical = (
        "secant_chord_exceeds_diameter",
        "answer_secant_chord_exceeds_diameter",
        "secant_near_segment_too_small",
        "external_point_inside_circle",
        "tangent_length_infeasible",
        "external_tangent_circles_intersect",
        "external_tangent_one_circle_inside_other",
    )
    return any(
        any(c in f for c in critical)
        for f in (q.get("geometric_feasibility_flags") or [])
    )
