"""
Target-angle plausibility — tangent-pair items must ask for the central angle, not a spurious angle at O involving the external point.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def _center_label(stem: str) -> Optional[str]:
    m = re.search(r"(?:centre|center)\s+([A-Z])\b", stem, re.I)
    return m.group(1).upper() if m else None


def _external_tangent_contacts(stem: str) -> Optional[Tuple[str, str, str]]:
    """
    Return (external, contact1_letter, contact2_letter) e.g. (W, T, U) for tangents WT and WU.
    """
    m = re.search(
        r"\bfrom\s+([A-Z]),?\s*tangents?\s+([A-Z])([A-Z])\s+and\s+([A-Z])([A-Z])\b",
        stem,
        re.I,
    )
    if m:
        ext = m.group(1).upper()
        return (ext, m.group(3).upper(), m.group(5).upper())
    m = re.search(
        r"\btangents?\s+([A-Z])([A-Z])\s+and\s+([A-Z])([A-Z])\s+from\s+([A-Z])\b",
        stem,
        re.I,
    )
    if m:
        return (m.group(5).upper(), m.group(2).upper(), m.group(4).upper())
    return None


def _parse_angle_triple(stem: str) -> List[Tuple[str, str, str]]:
    return [
        (m.group(1).upper(), m.group(2).upper(), m.group(3).upper())
        for m in re.finditer(r"\bangle\s+([A-Z])([A-Z])([A-Z])\b", stem, re.I)
    ]


def validate_angle_targets(stem: str, q: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    flags: List[str] = []
    score = 1.0
    fixes: List[str] = []

    if not stem or not re.search(r"\bfind\s+angle\b", stem, re.I):
        return {
            "angle_target_ok": True,
            "angle_target_score": 1.0,
            "angle_target_flags": [],
            "angle_target_suggested_fix": None,
        }

    center = _center_label(stem)
    pair = _external_tangent_contacts(stem)
    if not center or not pair:
        return {
            "angle_target_ok": True,
            "angle_target_score": 1.0,
            "angle_target_flags": [],
            "angle_target_suggested_fix": None,
        }

    ext, c1, c2 = pair
    contacts = {c1, c2}

    for m in re.finditer(r"\bfind\s+angle\s+([A-Z])([A-Z])([A-Z])\b", stem, re.I):
        a, b, c = m.group(1).upper(), m.group(2).upper(), m.group(3).upper()
        if b != center:
            continue
        # Wrong: central vertex O but one arm is external point (TOW, UOW, WOT)
        if a in contacts and c == ext:
            flags.append(f"wrong_central_angle_target:{a}{b}{c}_use_{c1}{center}{c2}")
            score -= 0.45
            fixes.append(f"find angle {c1}{center}{c2}")
        elif c in contacts and a == ext:
            flags.append(f"wrong_central_angle_target:{a}{b}{c}_use_{c1}{center}{c2}")
            score -= 0.45
            fixes.append(f"find angle {c1}{center}{c2}")

    # Given angle at external point (TWU) → should find central TOU not TOW
    ext_angles = [
        t
        for t in _parse_angle_triple(stem)
        if t[1] == ext and t[0] in contacts | {center} and t[2] in contacts | {center}
    ]
    if ext_angles:
        for m in re.finditer(r"\bfind\s+angle\s+([A-Z])([A-Z])([A-Z])\b", stem, re.I):
            a, b, c = m.group(1).upper(), m.group(2).upper(), m.group(3).upper()
            if b == center and (a == ext or c == ext):
                preferred = f"{c1}{center}{c2}"
                if f"{a}{b}{c}" != preferred:
                    flags.append(
                        f"tangent_pair_use_central_angle:{a}{b}{c}_expected_{preferred}"
                    )
                    score -= 0.4
                    fixes.append(f"find angle {preferred}")

    ok = score >= 0.65 and not any(
        f.startswith("wrong_central_angle_target") for f in flags
    )
    suggested = fixes[0] if fixes else None
    return {
        "angle_target_ok": ok,
        "angle_target_score": round(max(0.0, min(1.0, score)), 3),
        "angle_target_flags": flags,
        "angle_target_suggested_fix": suggested,
    }


def should_reject_angle_target(q: Dict[str, Any]) -> bool:
    stem = q.get("content") or ""
    report = validate_angle_targets(stem, q)
    q.update(
        {
            "angle_target_ok": report["angle_target_ok"],
            "angle_target_flags": report.get("angle_target_flags"),
            "angle_target_score": report.get("angle_target_score"),
        }
    )
    flags = report.get("angle_target_flags") or []
    return any(
        f.startswith("wrong_central_angle_target")
        or f.startswith("tangent_pair_use_central_angle")
        for f in flags
    )


def try_fix_angle_target(stem: str) -> Tuple[str, bool]:
    """Replace TOW-style targets with TOU when tangent-pair context is clear."""
    report = validate_angle_targets(stem)
    fix = report.get("angle_target_suggested_fix")
    if not fix:
        return stem, False
    m = re.search(r"\bfind\s+angle\s+([A-Z])([A-Z])([A-Z])\b", stem, re.I)
    if not m:
        return stem, False
    old = m.group(0)
    new_angle = fix.replace("find angle ", "").strip()
    new_phrase = f"find angle {new_angle}"
    if old.lower() == new_phrase.lower():
        return stem, False
    return stem.replace(old, new_phrase, 1), True
