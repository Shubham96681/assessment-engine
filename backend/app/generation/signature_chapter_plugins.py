"""
Chapter-specific primary-theorem detectors — registered by chapter_key from rule packs.

Keeps canonical_question_signature.py chapter-agnostic.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, Optional

PluginFn = Callable[[str, str, str], Optional[str]]

_REGISTRY: Dict[str, PluginFn] = {}


def register_chapter_signature_plugin(chapter_key: str, fn: PluginFn) -> None:
    _REGISTRY[(chapter_key or "").strip().lower()] = fn


def detect_chapter_primary_theorem(
    chapter: str,
    stem: str,
    answer: str,
    archetype: str,
) -> Optional[str]:
    fn = _REGISTRY.get((chapter or "").strip().lower())
    if fn:
        return fn(stem, answer, archetype)
    return None


def _circles_primary(stem: str, answer: str, archetype: str) -> Optional[str]:
    low = f"{stem} {answer}".lower()
    if "concentric" in low and "chord" in low:
        return "concentric_chord_theorem"
    if re.search(r"\bprove\b", low) and (
        "meets the circle only" in low
        or re.search(r"only\s+at\s+[A-Z]\b", stem, re.I)
    ):
        return "tangent_converse"
    if re.search(r"\bprove\b", low) and re.search(r"\bperpendicular\b", low):
        return "tangent_perpendicular_radius"
    if re.search(r"\bprove\b", low) and re.search(
        r"\b(?:pa|pb|rc|rd|jl|jm)\s*=\s*", stem, re.I
    ):
        return "equal_tangents_theorem"
    if re.search(r"\bsecant\b", low) and (
        "²" in answer or "×" in answer or "power" in low
    ):
        return "secant_tangent_power"
    if "common" in low and "external" in low:
        return "common_external_tangent"
    if re.search(r"tangent.*chord|chord.*tangent", low) and re.search(
        r"find\s+angle", low
    ):
        return "tangent_chord_angle_theorem"
    if re.search(r"tangents?\s+[A-Z]{2}", stem, re.I) and re.search(
        r"find\s+angle\s+[A-Z]O[A-Z]", stem, re.I
    ):
        return "tangent_pair_angle_sum"
    if re.search(r"\btangent\b", low) and re.search(r"\bradius\b|distance", low):
        return "tangent_length_radius"
    if archetype == "cyclic_angle":
        return "cyclic_quadrilateral_angle"
    if "similar" in low:
        return "tangent_similarity"
    return None


register_chapter_signature_plugin("circles", _circles_primary)
