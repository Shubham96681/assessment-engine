"""
Validate figure_spec point labels against question stem (Fig.5 must show G not Q).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

from app.generation.figure_spec_builder import _extract_labels


def labels_in_figure_spec(spec: Dict[str, Any]) -> Set[str]:
    labels: Set[str] = set()
    for el in spec.get("elements") or []:
        if not isinstance(el, dict):
            continue
        for key in ("label", "from", "to"):
            v = el.get(key)
            if isinstance(v, str) and len(v) == 1 and v.isalpha():
                labels.add(v.upper())
    for k in (spec.get("labels") or {}).keys():
        if len(k) == 1 and k.isalpha():
            labels.add(k.upper())
    return labels


def primary_external_from_stem(stem: str) -> str | None:
    """External point for current question (not prior Question references)."""
    m = re.search(
        r"\bpoint\s+([A-Z])\s+is\s+\d+(?:\.\d+)?\s*cm\s+from\s+O\b",
        stem,
        re.I,
    )
    if m:
        return m.group(1).upper()
    m = re.search(r"\bfrom\s+external\s+point\s+([A-Z])\b", stem, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"\bexternal\s+point\s+([A-Z])\b", stem, re.I)
    if m:
        return m.group(1).upper()
    return None


def figure_matches_stem(stem: str, spec: Dict[str, Any]) -> Tuple[bool, List[str]]:
    flags: List[str] = []
    stem_pts = _extract_labels(stem or "")
    fig_pts = labels_in_figure_spec(spec)
    ext = primary_external_from_stem(stem)
    if ext and fig_pts:
        outside_in_spec = ext in fig_pts
        if not outside_in_spec:
            flags.append(f"figure_missing_external:{ext}")
        wrong = [p for p in ("P", "Q", "T") if p in fig_pts and p != ext and ext == "G"]
        if ext == "G" and "P" in fig_pts and "G" not in fig_pts:
            flags.append("figure_reuses_P_not_G")
    if spec.get("layout") == "two_circle_external_tangent":
        centres = spec.get("centres") or []
        for c in centres:
            if c and c.upper() not in stem_pts:
                flags.append(f"two_circle_centre_not_in_stem:{c}")
    return (not flags, flags)


def needs_figure_rebuild(stem: str, spec: Dict[str, Any] | None) -> bool:
    if not spec:
        return True
    ok, _ = figure_matches_stem(stem, spec)
    if not ok:
        return True
    if is_common_external_stem(stem) and spec.get("layout") != "two_circle_external_tangent":
        return True
    return False


def is_common_external_stem(stem: str) -> bool:
    low = (stem or "").lower()
    return "common" in low and "external" in low and "tangent" in low
