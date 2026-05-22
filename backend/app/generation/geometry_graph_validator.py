"""
Geometry graph validator — entity/label consistency and minimum context for stems.

Builds a lightweight graph from stem + figure_spec, then checks:
- every referenced point is defined (stem or figure),
- angle symbols use vertices present in the graph,
- prove/find tasks have minimum textbook context (even when compressed).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class GeometryGraph:
    points: Set[str] = field(default_factory=set)
    center: Optional[str] = None
    tangents: List[Tuple[str, str, str]] = field(default_factory=list)  # external, contact, contact
    radii: List[Tuple[str, str]] = field(default_factory=list)  # center, on_circle
    angles: List[Tuple[str, str, str]] = field(default_factory=list)  # vertex triple
    segments: List[Tuple[str, str]] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)


def _stem_points(stem: str) -> Set[str]:
    pts: Set[str] = set()
    if not stem:
        return pts
    patterns = [
        r"(?:centre|center)\s+([A-Z])\b",
        r"\bpoint\s+([A-Z])\b",
        r"\bat\s+([A-Z])\b",
        r"\bfrom\s+([A-Z])\b",
        r"\bthrough\s+(?:point\s+)?([A-Z])\b",
        r"\btangents?\s+([A-Z])([A-Z])\b",
        r"\b(?:angle|triangle|quadrilateral)\s+([A-Z])([A-Z])([A-Z]?)\b",
        r"\b([A-Z])([A-Z])\s+is\s+a\s+tangent",
        r"\b([A-Z])([A-Z])\s+and\s+([A-Z])([A-Z])\b",
        r"\b([A-Z])\s*=\s*\d",
    ]
    for pat in patterns:
        for m in re.finditer(pat, stem, re.I):
            for g in m.groups():
                if g and len(g) == 1 and g.isalpha():
                    pts.add(g.upper())
                elif g and len(g) == 2 and g.isalpha():
                    pts.add(g[0].upper())
                    pts.add(g[1].upper())
    for pair in re.finditer(r"\b([A-Z])([A-Z])\b", stem):
        pts.add(pair.group(1).upper())
        pts.add(pair.group(2).upper())
    return pts


def _figure_points(q: Dict[str, Any]) -> Set[str]:
    pts: Set[str] = set()
    spec = q.get("figure_spec") or {}
    for el in spec.get("elements") or []:
        if not isinstance(el, dict):
            continue
        for key in ("label", "from", "to"):
            v = el.get(key)
            if v and len(str(v)) == 1 and str(v).isalpha():
                pts.add(str(v).upper())
    for k in (spec.get("labels") or {}).keys():
        if len(k) == 1:
            pts.add(k.upper())
    return pts


def build_geometry_graph(stem: str, q: Optional[Dict[str, Any]] = None) -> GeometryGraph:
    g = GeometryGraph()
    g.points = _stem_points(stem)
    if q:
        g.points |= _figure_points(q)

    low = stem.lower()
    m = re.search(r"(?:centre|center)\s+([A-Z])\b", stem, re.I)
    if m:
        g.center = m.group(1).upper()
        g.points.add(g.center)

    for m in re.finditer(
        r"\bfrom\s+([A-Z]),?\s*tangents?\s+([A-Z])([A-Z])\s+and\s+([A-Z])([A-Z])\b",
        stem,
        re.I,
    ):
        ext, a1, a2, b1, b2 = m.group(1).upper(), m.group(2).upper(), m.group(3).upper(), m.group(4).upper(), m.group(5).upper()
        g.tangents.append((ext, a1 + a2, b1 + b2))
        g.points.update({ext, a1, a2, b1, b2})

    for m in re.finditer(r"\btangents?\s+([A-Z])([A-Z])\s+and\s+([A-Z])([A-Z])\b", stem, re.I):
        g.tangents.append(("", m.group(1).upper() + m.group(2).upper(), m.group(3).upper() + m.group(4).upper()))
        g.points.update({m.group(1).upper(), m.group(2).upper(), m.group(3).upper(), m.group(4).upper()})

    for m in re.finditer(r"\b([A-Z])([A-Z])\s+is\s+a\s+tangent\s+at\s+([A-Z])\b", stem, re.I):
        g.tangents.append((m.group(2).upper(), m.group(1).upper() + m.group(2).upper(), m.group(3).upper()))
        g.points.update({m.group(1).upper(), m.group(2).upper(), m.group(3).upper()})

    for m in re.finditer(r"\bangle\s+([A-Z])([A-Z])([A-Z])\b", stem, re.I):
        triple = (m.group(1).upper(), m.group(2).upper(), m.group(3).upper())
        g.angles.append(triple)
        g.points.update(triple)

    for m in re.finditer(r"\b([A-Z])([A-Z])\s*=\s*\d", stem):
        g.segments.append((m.group(1).upper(), m.group(2).upper()))
        g.points.update({m.group(1).upper(), m.group(2).upper()})

    if g.center and "radius" in low:
        g.radii.append((g.center, ""))

    return g


def validate_geometry_graph(stem: str, q: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    g = build_geometry_graph(stem, q)
    flags: List[str] = []
    score = 1.0

    fig_pts = _figure_points(q) if q else set()
    stem_pts = _stem_points(stem)
    all_pts = g.points | fig_pts

    for a, b, c in g.angles:
        missing = [p for p in (a, b, c) if p not in all_pts]
        if missing:
            flags.append(f"angle_vertices_undefined:{a}{b}{c}")
            score -= 0.25
        if g.center and b == g.center:
            arms = {a, c}
            on_circle = set()
            for t in g.tangents:
                if len(t) == 3 and t[1]:
                    on_circle.add(t[1][-1])
                    on_circle.add(t[2][-1])
            if arms and on_circle and not arms.issubset(on_circle | {g.center}):
                if "POQ" in f"{a}{b}{c}" and any(
                    x in stem for x in ("TA", "TB", "tangents TA", "tangents TP")
                ):
                    flags.append("angle_center_mismatch:use_AOB_not_POQ")
                    score -= 0.35

    orphan = stem_pts - all_pts
    if orphan:
        flags.append(f"orphan_points:{','.join(sorted(orphan))}")
        score -= min(0.3, 0.08 * len(orphan))

    if re.search(r"\bprove\b", stem, re.I) and re.search(r"\b([A-Z])([A-Z])\s*=\s*([A-Z])([A-Z])\b", stem):
        if not g.tangents and "tangent" not in stem.lower():
            flags.append("prove_equality_missing_tangent_setup")
            score -= 0.4

    from app.generation.angle_target_validator import validate_angle_targets

    angle_tgt = validate_angle_targets(stem, q)
    for f in angle_tgt.get("angle_target_flags") or []:
        flags.append(f)
        score -= 0.35 if "wrong_central" in f else 0.2

    if re.search(r"\bfind\s+(?:the\s+)?angle\b", stem, re.I):
        if not g.angles:
            flags.append("angle_find_missing_angle_symbol")
            score -= 0.3
        if not re.search(r"\d+\s*(?:°|degrees?)?|\d+°", stem, re.I) and " or " not in stem.lower():
            if not re.search(r"right angle|90\s*°", stem, re.I):
                flags.append("angle_find_missing_numeric_given")
                score -= 0.2

    integrity = max(0.0, min(1.0, score))
    return {
        "geometry_integrity_score": round(integrity, 3),
        "geometry_flags": flags,
        "geometry_graph_ok": integrity >= 0.62 and "prove_equality_missing_tangent_setup" not in flags,
        "graph_points": sorted(all_pts),
    }


def apply_minimum_context(stem: str, q: Optional[Dict[str, Any]] = None) -> Tuple[str, bool]:
    """Expand over-compressed stems to textbook-minimum context when safe."""
    if not stem:
        return stem, False
    s = stem.strip()
    low = s.lower()

    m = re.match(
        r"^prove\s+that\s+([A-Z])([A-Z])\s*=\s*([A-Z])([A-Z])\s*\.?$",
        s,
        re.I,
    )
    if m and "tangent" not in low and "from " not in low:
        a, b, c, d = m.group(1).upper(), m.group(2).upper(), m.group(3).upper(), m.group(4).upper()
        ext = b if b not in (a, c, d) else "P"
        if a == c and a not in (b, d):
            ext = a
        return (
            f"From {ext}, tangents {a}{b} and {c}{d} are drawn to a circle. Prove that {a}{b} = {c}{d}.",
            True,
        )

    if re.search(r"angle\s+POQ", s, re.I) and re.search(
        r"tangents?\s+TA\s+and\s+TB|tangents?\s+TA\b", s, re.I
    ):
        fixed = re.sub(r"angle\s+POQ", "angle AOB", s, count=1, flags=re.I)
        if fixed != s:
            return fixed, True

    if re.search(r"angle\s+POQ", s, re.I) and re.search(
        r"tangents?\s+TP\s+and\s+TQ", s, re.I
    ) and re.search(r"find\s+angle\s+PTQ", s, re.I) is None:
        fixed = re.sub(r"find\s+angle\s+ATB", "find angle PTQ", s, flags=re.I)
        fixed = re.sub(r"angle\s+POQ", "angle POQ", fixed, flags=re.I)
        if fixed != s:
            return fixed, True

    return s, False


def repair_question_geometry(q: Dict[str, Any]) -> Dict[str, Any]:
    """Apply minimum context + re-validate; mutates content in place."""
    stem = (q.get("content") or "").strip()
    expanded, changed = apply_minimum_context(stem, q)
    if changed:
        q["content"] = expanded
        q["geometry_repaired"] = True
    report = validate_geometry_graph(q.get("content") or "", q)
    q["geometry_integrity_score"] = report["geometry_integrity_score"]
    q["geometry_flags"] = report["geometry_flags"]
    q["geometry_graph_ok"] = report["geometry_graph_ok"]
    return q
