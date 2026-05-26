"""
Build valid circle geometry figure_spec from question stems.
Fixes Cursor/RAG specs that omit the circle element (which caused rectangle layouts).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

_Q1_CONFIG_RE = re.compile(
    r"configuration\s+of\s+question\s+1|using\s+the\s+configuration\s+in\s+question\s+1",
    re.I,
)
_INNER_RADIUS_RATIO = 21 / 29


def _uses_q1_concentric(stem: str) -> bool:
    return bool(_Q1_CONFIG_RE.search(stem or ""))


def _circle_elements(stem: str) -> List[Dict[str, Any]]:
    if _uses_q1_concentric(stem):
        return [
            {"shape": "circle", "label": "outer"},
            {"shape": "circle", "label": "inner", "radius_ratio": _INNER_RADIUS_RATIO},
        ]
    return [{"shape": "circle", "label": "Circle"}]


def _seg(frm: str, to: str, style: str = "") -> Dict[str, Any]:
    el: Dict[str, Any] = {"shape": "segment", "from": frm, "to": to}
    if style:
        el["style"] = style
    return el


def _pt(label: str, position: str) -> Dict[str, Any]:
    return {"shape": "point", "label": label, "position": position}


def _extract_labels(stem: str) -> Set[str]:
    labels: Set[str] = set()
    stem_u = stem or ""
    for m in re.finditer(
        r"\b(?:centre|center)\s+([A-Z])\b|\bpoint\s+([A-Z])\b|"
        r"\btangent\s+([A-Z])([A-Z])\b|\b(?:secant|chord)\s+([A-Z])([A-Z]{1,2})\b|"
        r"\b([A-Z])([A-Z])\s+(?:is|are|touch|touches)\b",
        stem_u,
        re.I,
    ):
        for g in m.groups():
            if not g:
                continue
            if len(g) == 1 and g.isalpha():
                labels.add(g.upper())
            elif len(g) == 2 and g.isalpha():
                labels.add(g[0].upper())
                labels.add(g[1].upper())
            elif len(g) == 3 and g.isalpha():
                for c in g:
                    labels.add(c)
    for m in re.finditer(r"\b([A-Z])([A-Z])\b", stem_u):
        labels.add(m.group(1).upper())
        labels.add(m.group(2).upper())
    return labels


def primary_external_from_stem_for_build(stem: str) -> Optional[str]:
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
    return None


def _centre_label(stem: str, labels: Set[str]) -> str:
    m = re.search(r"\b(?:centre|center)\s+([A-Z])\b", stem, re.I)
    if m:
        return m.group(1).upper()
    if "O" in labels:
        return "O"
    return "O"


_UNIT_CIRCLE_RE = re.compile(
    r"unit\s+circle|standard\s+position|quadrant\s+(?:of\s+)?θ|quadrant\s+of\s+theta",
    re.I,
)
_ANGLE_DEG_RE = re.compile(
    r"(?:∠\s*)?(?:angle\s+)?θ\s*=\s*(-?\d+(?:\.\d+)?)\s*°|"
    r"(-?\d+(?:\.\d+)?)\s*°\s+in\s+standard\s+position|"
    r"shows\s+(?:∠\s*)?θ\s*=\s*(-?\d+(?:\.\d+)?)\s*°",
    re.I,
)


def _is_unit_circle_stem(stem: str) -> bool:
    return bool(_UNIT_CIRCLE_RE.search(stem or ""))


def _extract_angle_degrees(stem: str) -> Optional[float]:
    for m in _ANGLE_DEG_RE.finditer(stem or ""):
        for g in m.groups():
            if g is not None:
                try:
                    return float(g)
                except ValueError:
                    continue
    m = re.search(r"\b(\d{2,3})\s*°\b", stem or "")
    if m and _is_unit_circle_stem(stem):
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _build_unit_circle_spec(stem: str) -> Optional[Dict[str, Any]]:
    """Unit circle with θ in standard position (trigonometry FigureBased)."""
    if not _is_unit_circle_stem(stem):
        return None
    angle = _extract_angle_degrees(stem)
    if angle is None:
        angle = 45.0
    return {
        "type": "unit_circle",
        "title": "Diagram",
        "angle_deg": angle % 360,
        "theta_label": "θ",
        "show_axes": True,
        "show_quadrant_labels": False,
    }


def _is_circle_stem(stem: str) -> bool:
    if _is_unit_circle_stem(stem):
        return False
    low = (stem or "").lower()
    return any(
        k in low
        for k in (
            "circle",
            "tangent",
            "secant",
            "concentric",
            "radius",
            "chord",
            "circumscribe",
        )
    )


def _build_from_stem(stem: str) -> Optional[Dict[str, Any]]:
    """Construct a geometry figure_spec when the stem is clearly Circles content."""
    if not _is_circle_stem(stem):
        return None

    labels = _extract_labels(stem)
    centre = _centre_label(stem, labels)
    elements: List[Dict[str, Any]] = [
        *_circle_elements(stem),
        _pt(centre, "centre"),
    ]
    segments: List[Dict[str, Any]] = []
    show_right_angle = False

    low = stem.lower()

    # Q5 fusion: point X from O, tangent XY, secant XYZ (before generic tangent from Q2)
    fusion_pt = re.search(
        r"\b(?:hence\s+)?point\s+([A-Z])\s+is\s+\d+(?:\.\d+)?\s*cm\s+from\s+O\b",
        stem,
        re.I,
    )
    if fusion_pt:
        ext = fusion_pt.group(1).upper()
        tan_m = re.search(rf"\btangent\s+{ext}([A-Z])\b", stem, re.I)
        sec_m = re.search(rf"\bsecant\s+{ext}([A-Z])([A-Z])\b", stem, re.I)
        if tan_m and sec_m:
            contact = tan_m.group(1).upper()
            s_from, s_to = sec_m.group(1).upper(), sec_m.group(2).upper()
            fusion_labels = {ext, contact, s_from, s_to, centre}
            fusion_pts = [
                _pt(ext, "outside"),
                _pt(contact, "on_circle"),
                _pt(s_from, "on_circle"),
                _pt(s_to, "on_circle"),
            ]
            fusion_segs = [
                _seg(ext, contact),
                _seg(centre, contact, "dashed"),
                _seg(ext, s_from),
                _seg(s_from, s_to),
            ]
            q2_ref = re.search(
                r"\b([A-Z])([A-Z])\s*=\s*\d+(?:\.\d+)?\s*cm\s+from\s+question\s+2\b",
                stem,
                re.I,
            )
            cites_q2 = bool(
                q2_ref
                or re.search(r"\bfrom\s+question\s+2\b", stem, re.I)
                or re.search(r"\btangent\s+PA\b", stem, re.I)
            )
            if cites_q2:
                if q2_ref:
                    q2_ext, q2_contact = q2_ref.group(1).upper(), q2_ref.group(2).upper()
                else:
                    q2_ext, q2_contact = "P", "A"
                fusion_labels.update({q2_ext, q2_contact})
                fusion_pts.extend(
                    [_pt(q2_ext, "outside"), _pt(q2_contact, "on_circle")]
                )
                fusion_segs.extend(
                    [
                        _seg(q2_ext, q2_contact),
                        _seg(centre, q2_contact, "dashed"),
                    ]
                )
            elements.extend(fusion_pts)
            segments.extend(fusion_segs)
            spec = _finalize(
                elements,
                segments,
                fusion_labels,
                centre,
                True,
                right_angle_at=contact,
                right_angle_legs=[centre, s_from],
                tangent_marks=[contact],
            )
            spec["layout"] = "fusion_q5"
            return spec

    # Two circles — direct common external tangent
    if (
        ("common" in low and "external" in low and "tangent" in low)
        or (
            re.search(r"\btwo\s+circles?\b", low)
            and re.search(r"\bcentres?\b", low)
            and "external" in low
        )
    ):
        centres_m = re.search(r"\bcentres?\s+([A-Z])\s+and\s+([A-Z])\b", stem, re.I)
        radii_m = re.search(
            r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm",
            stem,
            re.I,
        )
        dist_m = re.search(r"\b([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)\s*cm", stem)
        tan_m = re.search(
            r"\b(?:external\s+)?tangent\s+([A-Z])([A-Z])\b", stem, re.I
        )
        c1 = centres_m.group(1).upper() if centres_m else "G"
        c2 = centres_m.group(2).upper() if centres_m else "H"
        e, f = (
            (tan_m.group(1).upper(), tan_m.group(2).upper())
            if tan_m
            else ("E", "F")
        )
        r1 = float(radii_m.group(1)) if radii_m else 3.0
        r2 = float(radii_m.group(2)) if radii_m else 8.0
        dist = float(dist_m.group(2)) if dist_m else 13.0
        labels.update({c1, c2, e, f})
        spec: Dict[str, Any] = {
            "type": "labeled_diagram",
            "title": "Diagram",
            "layout": "two_circle_external_tangent",
            "centres": [c1, c2],
            "radii": {c1: r1, c2: r2},
            "centre_distance": dist,
            "tangent_segment": [e, f],
            "elements": [
                {"shape": "circle", "centre": c1, "radius_ratio": 1.0},
                {"shape": "circle", "centre": c2, "radius_ratio": r2 / max(r1, 0.01)},
                _pt(c1, "centre"),
                _pt(c2, "centre"),
                _pt(e, "on_circle"),
                _pt(f, "on_circle"),
                _seg(e, f),
                _seg(c1, c2, "dashed"),
            ],
            "labels": {lbl: lbl for lbl in labels if len(lbl) == 1},
            "show_right_angle": False,
        }
        return spec

    # Concentric: two radii + chord AB tangent at T
    if "concentric" in low:
        chord_m = re.search(r"\bchord\s+([A-Z])([A-Z])\b", stem, re.I)
        touch_m = re.search(
            r"\btouch(?:es|ing)?\s+(?:the\s+)?(?:inner|smaller)\s+(?:circle\s+)?at\s+([A-Z])\b",
            stem,
            re.I,
        )
        contact = touch_m.group(1).upper() if touch_m else "T"
        if chord_m:
            a, b = chord_m.group(1).upper(), chord_m.group(2).upper()
            labels.update({a, b, contact})
            elements.append({"shape": "circle", "label": "inner", "radius_ratio": 0.55})
            elements.extend([_pt(a, "on_circle"), _pt(b, "on_circle"), _pt(contact, "on_circle")])
            segments.extend(
                [
                    _seg(centre, contact, "dashed"),
                    _seg(a, b),
                ]
            )
            show_right_angle = True
            return _finalize(
                elements,
                segments,
                labels,
                centre,
                show_right_angle,
                right_angle_at=contact,
                right_angle_legs=[centre, a],
                tangent_marks=[contact],
                chord_bisect_at=contact,
            )

    # External point + tangent at K + secant HLM
    ext_m = re.search(r"\b(?:from|at)\s+point\s+([A-Z])\s+outside", stem, re.I)
    if not ext_m:
        ext_m = re.search(r"\bfrom\s+external\s+point\s+([A-Z])\b", stem, re.I)
    tangent_matches = list(
        re.finditer(r"\btangent\s+([A-Z])([A-Z])\b", stem, re.I)
    )
    secant_m = re.search(r"\bsecant\s+([A-Z])([A-Z]{1,2})\b", stem, re.I)

    if tangent_matches and secant_m:
        ext_point = primary_external_from_stem_for_build(stem)
        tangent_m = tangent_matches[-1]
        if ext_point:
            for tm in tangent_matches:
                if tm.group(1).upper() == ext_point:
                    tangent_m = tm
                    break
        ext = ext_point or tangent_m.group(1).upper()
        contact = tangent_m.group(2).upper()
        sec = secant_m.group(2).upper()
        if len(sec) >= 3:
            s_from, s_mid, s_to = sec[0], sec[1], sec[2]
        elif len(sec) == 2:
            s_from, s_to = sec[0], sec[1]
            s_mid = s_to
        else:
            s_from = s_to = sec[0]
            s_mid = sec[0]
        if ext == contact:
            ext = secant_m.group(1).upper()
        elements.extend(
            [
                _pt(ext, "outside"),
                _pt(contact, "on_circle"),
                _pt(s_from, "on_circle"),
                _pt(s_to, "on_circle"),
            ]
        )
        segments.extend(
            [
                _seg(ext, contact),
                _seg(centre, contact, "dashed"),
                _seg(ext, s_from),
                _seg(s_from, s_to),
            ]
        )
        show_right_angle = True
        spec = _finalize(
            elements,
            segments,
            labels,
            centre,
            show_right_angle,
            right_angle_at=contact,
            right_angle_legs=[centre, s_from if s_from in labels else s_to],
            tangent_marks=[contact],
        )
        if _uses_q1_concentric(stem):
            spec["layout"] = "secant_tangent_concentric"
        return spec

    # Two tangents SR and ST from external point S
    pair_m = re.search(
        r"\btangents?\s+([A-Z])([A-Z])\s+and\s+([A-Z])([A-Z])\b", stem, re.I
    )
    from_m = re.search(r"\bfrom\s+([A-Z])\b", stem, re.I)
    if pair_m:
        c1, c2 = pair_m.group(2).upper(), pair_m.group(4).upper()
        ext = (
            (from_m.group(1).upper() if from_m else None)
            or (ext_m.group(1).upper() if ext_m else None)
            or pair_m.group(1).upper()
        )
        if ext in (c1, c2, centre):
            ext = _pick_external(labels, centre, pair_m)
        elements.extend([_pt(ext, "outside"), _pt(c1, "on_circle"), _pt(c2, "on_circle")])
        segments.extend(
            [
                _seg(ext, c1),
                _seg(ext, c2),
                _seg(centre, c1, "dashed"),
                _seg(centre, c2, "dashed"),
                _seg(centre, ext, "dashed"),
            ]
        )
        show_right_angle = True
        return _finalize(elements, segments, labels, centre, show_right_angle)

    # Converse / sparse: line through S meets circle only at S; OS ⟂ line → tangent at S
    converse_m = re.search(
        r"\bline\s+through\s+point\s+([A-Z])\b.*\bmeets\s+the\s+circle\s+only\s+at\s+\1\b",
        stem,
        re.I | re.S,
    )
    if converse_m or (
        re.search(r"\bprove\b", low)
        and re.search(r"\bperpendicular\b", low)
        and re.search(r"\btangent\b", low)
        and re.search(r"\bpoint\s+([A-Z])\s+on\s+a\s+circle", stem, re.I)
    ):
        sm = re.search(r"\bpoint\s+([A-Z])\s+on\s+a\s+circle", stem, re.I)
        contact = (converse_m.group(1).upper() if converse_m else None) or (
            sm.group(1).upper() if sm else "S"
        )
        perp_m = re.search(
            rf"\b{re.escape(centre)}\s*{contact}\s+is\s+perpendicular\b|"
            rf"\b{re.escape(centre)}{contact}\s+is\s+perpendicular\b|"
            rf"\b{re.escape(centre)}\s+is\s+perpendicular\s+to\s+this\s+line\b",
            stem,
            re.I,
        )
        line_m = re.search(r"\bline\s+([A-Z])\b", stem, re.I)
        ext = line_m.group(1).upper() if line_m else "A"
        if ext == contact or ext == centre:
            ext = "A" if ext == contact else "B"
        labels.update({contact, ext, centre})
        elements.extend(
            [
                _pt(contact, "on_circle"),
                _pt(ext, "outside" if ext != contact else "outside"),
            ]
        )
        segments.extend(
            [
                _seg(centre, contact, "dashed"),
                _seg(contact, ext),
            ]
        )
        return _finalize(
            elements,
            segments,
            labels,
            centre,
            True,
            right_angle_at=contact,
            right_angle_legs=[centre, ext],
            tangent_marks=[contact],
        )

    # Sparse prove PA = PB
    prove_m = re.search(r"\bprove\s+that\s+([A-Z])([A-Z])\s*=\s*([A-Z])([A-Z])\b", stem, re.I)
    if prove_m:
        ext = prove_m.group(1).upper()
        a, b = prove_m.group(2).upper(), prove_m.group(4).upper()
        elements.extend([_pt(ext, "outside"), _pt(a, "on_circle"), _pt(b, "on_circle")])
        segments.extend(
            [
                _seg(ext, a),
                _seg(ext, b),
                _seg(centre, a, "dashed"),
                _seg(centre, b, "dashed"),
            ]
        )
        show_right_angle = True
        return _finalize(elements, segments, labels, centre, show_right_angle)

    # Angle between tangents TP, TQ
    ang_m = re.search(r"\btangents?\s+([A-Z])([A-Z])\s+and\s+([A-Z])([A-Z])\b", stem, re.I)
    if ang_m:
        ext = (ext_m.group(1).upper() if ext_m else "T")
        p, q = ang_m.group(2).upper(), ang_m.group(4).upper()
        elements.extend([_pt(ext, "outside"), _pt(p, "on_circle"), _pt(q, "on_circle")])
        segments.extend(
            [
                _seg(ext, p),
                _seg(ext, q),
                _seg(centre, p, "dashed"),
                _seg(centre, q, "dashed"),
            ]
        )
        return _finalize(elements, segments, labels, centre, show_right_angle)

    return None


def _pick_external(labels: Set[str], centre: str, *match_objs) -> str:
    used = {centre}
    for m in match_objs:
        if hasattr(m, "groups"):
            for g in m.groups():
                if g and len(g) >= 1:
                    used.add(g[0].upper())
                    if len(g) == 2:
                        used.add(g[1].upper())
    for lbl in sorted(labels):
        if lbl not in used and lbl != centre:
            return lbl
    return "P"


def _finalize(
    elements: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
    labels: Set[str],
    centre: str,
    show_right_angle: bool,
    *,
    right_angle_at: Optional[str] = None,
    right_angle_legs: Optional[List[str]] = None,
    tangent_marks: Optional[List[str]] = None,
    chord_bisect_at: Optional[str] = None,
) -> Dict[str, Any]:
    seen = {(el.get("label") or "").upper() for el in elements if el.get("shape") == "point"}
    used_in_segments: Set[str] = set()
    for el in segments:
        if (el.get("shape") or "").lower() != "segment":
            continue
        for key in ("from", "to"):
            v = el.get(key)
            if isinstance(v, str) and len(v) == 1 and v.isalpha():
                used_in_segments.add(v.upper())
    for lbl in labels:
        if len(lbl) != 1 or not lbl.isalpha() or lbl in seen or lbl == centre:
            continue
        if lbl.upper() not in used_in_segments:
            continue
        elements.append(_pt(lbl, "on_circle"))
    elements.extend(segments)
    label_map = {
        lbl: lbl
        for lbl in (used_in_segments | {centre.upper()})
        if len(lbl) == 1 and lbl.isalpha()
    }
    label_map.setdefault(centre, centre)
    spec: Dict[str, Any] = {
        "type": "labeled_diagram",
        "title": "Diagram",
        "elements": elements,
        "labels": label_map,
        "show_right_angle": show_right_angle,
    }
    if right_angle_at:
        spec["right_angle_at"] = right_angle_at
    if right_angle_legs and len(right_angle_legs) >= 2:
        spec["right_angle_legs"] = right_angle_legs[:2]
    if tangent_marks:
        spec["tangent_marks"] = tangent_marks
    if chord_bisect_at:
        spec["chord_bisect_at"] = chord_bisect_at
    return spec


def enrich_figure_spec(stem: str, spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ensure circle geometry questions get a circle + correct point positions.
    Replaces weak RAG specs; merges with existing segments when possible.
    """
    spec = dict(spec or {})
    stem = stem or ""

    unit = _build_unit_circle_spec(stem)
    if unit:
        if spec.get("angle_deg") is not None:
            unit["angle_deg"] = float(spec["angle_deg"]) % 360
        return unit

    built = _build_from_stem(stem)
    if built:
        # Do not merge stale segments from prior slots (e.g. Q2 point P into Q5 figure G)
        return built

    elements = list(spec.get("elements") or [])
    has_circle = any((el.get("shape") or "").lower() == "circle" for el in elements)
    positions = {
        (el.get("position") or "").lower()
        for el in elements
        if (el.get("shape") or "").lower() == "point"
    }
    if _is_circle_stem(stem) and not has_circle:
        elements.insert(0, {"shape": "circle", "label": "Circle"})
        centre = _centre_label(stem, _extract_labels(stem))
        if not any(
            (el.get("label") or "").upper() == centre
            and (el.get("shape") or "").lower() == "point"
            for el in elements
        ):
            elements.insert(1, _pt(centre, "centre"))
        for el in elements:
            if (el.get("shape") or "").lower() != "point":
                continue
            pos = (el.get("position") or "").lower()
            if pos in ("center", "inside", ""):
                lbl = (el.get("label") or "").upper()
                if lbl == centre:
                    el["position"] = "centre"
                elif lbl in _extract_labels(stem):
                    el["position"] = _infer_position_from_segments(lbl, elements, centre)
        spec["elements"] = elements
        spec.setdefault("show_right_angle", True)

    return spec


def _infer_position_from_segments(label: str, elements: List[Dict], centre: str) -> str:
    on_circle_touch = 0
    external_links = 0
    for el in elements:
        if (el.get("shape") or "").lower() != "segment":
            continue
        frm, to = (el.get("from") or "").upper(), (el.get("to") or "").upper()
        if label not in (frm, to):
            continue
        other = to if frm == label else frm
        if other == centre:
            continue
        external_links += 1
        if other != centre:
            on_circle_touch += 1
    if external_links >= 2:
        return "outside"
    if label == centre:
        return "centre"
    return "on_circle"
