"""
Canonical question signature — zero-duplicate policy per exam.

Signature tuple (stable across relabelled points/numbers):
  primary_theorem, reasoning_pattern, answer_structure, diagram_archetype
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from app.generation.reasoning_signature import (
    extract_reasoning_signature,
    reasoning_signature_for_question,
    signature_key,
)


@dataclass(frozen=True)
class CanonicalSignature:
    primary_theorem: str
    reasoning_pattern: str
    answer_structure: str
    diagram_archetype: str

    def key(self) -> str:
        return "|".join(
            (
                self.primary_theorem,
                self.reasoning_pattern,
                self.answer_structure,
                self.diagram_archetype,
            )
        )


def _answer_text(q: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("correct_answer", "answer", "explanation"):
        v = q.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts)


def _primary_theorem(stem: str, answer: str, archetype: str) -> str:
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
    return archetype or "generic_circle"


def _reasoning_pattern(stem: str, answer: str, archetype: str) -> str:
    comps = extract_reasoning_signature(stem, answer=answer, archetype_id=archetype)
    return signature_key(comps) or reasoning_signature_for_question(
        {"content": stem, "correct_answer": answer, "archetype_id": archetype}
    )


def _answer_structure(stem: str, answer: str) -> str:
    low = f"{stem} {answer}".lower()
    if re.search(r"\bprove\b", low) and re.search(r"\bhence\b|\(ii\)", low):
        return "proof_then_numeric"
    if re.search(r"\bprove\b", low):
        return "proof_only"
    if re.search(r"\(i\).*\(ii\)", stem, re.I | re.S):
        return "multi_part_numeric"
    if re.search(r"\bfind\s+angle\b", low):
        return "numeric_angle"
    if re.search(r"\bfind\b", low):
        return "numeric_length"
    return "mixed"


def _diagram_archetype(q: Dict[str, Any], stem: str) -> str:
    spec = q.get("figure_spec") or {}
    elements = spec.get("elements") or []
    labels = set()
    for el in elements:
        if isinstance(el, dict) and el.get("label"):
            labels.add(str(el["label"]).upper())
    low = stem.lower()
    if "concentric" in low:
        return "concentric_two_circles"
    if re.search(r"\btwo\s+circles?\b", low) and re.search(r"\bcentres?\b", low):
        return "two_circles_common_tangent"
    if re.search(r"centres?\s+[A-Z].*centres?\s+[B-Z]", stem, re.I):
        return "two_circles_common_tangent"
    if re.search(r"tangents?\s+[A-Z]{2}\s+and\s+[A-Z]{2}", stem, re.I):
        return "external_point_two_tangents"
    if re.search(r"\bsecant\b", low) and re.search(r"\btangent\b", low):
        return "external_point_tangent_secant"
    if re.search(r"\btangent\b", low) and len(labels) <= 4:
        return "single_circle_tangent"
    if q.get("figure_type") == "labeled_diagram":
        return "labeled_circle_diagram"
    return "no_diagram"


def build_canonical_signature(q: Dict[str, Any]) -> CanonicalSignature:
    stem = q.get("content") or q.get("question") or ""
    answer = _answer_text(q)
    arch = (q.get("archetype_id") or q.get("slot_archetype") or "").strip()
    return CanonicalSignature(
        primary_theorem=_primary_theorem(stem, answer, arch),
        reasoning_pattern=_reasoning_pattern(stem, answer, arch),
        answer_structure=_answer_structure(stem, answer),
        diagram_archetype=_diagram_archetype(q, stem),
    )


def annotate_canonical_signatures(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for q in questions:
        sig = build_canonical_signature(q)
        q["canonical_signature"] = sig.key()
        q["canonical_signature_parts"] = {
            "primary_theorem": sig.primary_theorem,
            "reasoning_pattern": sig.reasoning_pattern,
            "answer_structure": sig.answer_structure,
            "diagram_archetype": sig.diagram_archetype,
        }
    return questions


def filter_zero_duplicate_signatures(
    questions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Step 1 policy: zero repeated canonical signatures per paper."""
    annotate_canonical_signatures(questions)
    kept: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for q in questions:
        key = q.get("canonical_signature") or ""
        if key in seen:
            q["dedup_reason"] = f"canonical_signature_duplicate:{key}"
            continue
        seen.add(key)
        kept.append(q)
    if not kept and questions:
        q0 = dict(questions[0])
        q0["dedup_warning"] = "all_canonical_duplicates_kept_one"
        return [q0]
    return kept


def paper_has_duplicate_signatures(questions: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    annotate_canonical_signatures(questions)
    counts: Dict[str, int] = {}
    for q in questions:
        k = q.get("canonical_signature") or ""
        if k:
            counts[k] = counts.get(k, 0) + 1
    dups = [f"{k}×{n}" for k, n in counts.items() if n > 1]
    return (len(dups) > 0, dups)
