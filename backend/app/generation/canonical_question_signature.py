"""
Canonical question signature — zero-duplicate policy per exam.

Signature tuple (stable across relabelled points/numbers):
  primary_theorem, reasoning_pattern, answer_structure, diagram_archetype

Chapter-specific theorem detection lives in signature_chapter_plugins (registered by rule pack).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from app.generation.reasoning_signature import (
    extract_reasoning_signature,
    reasoning_signature_for_question,
    signature_key,
)
from app.generation.signature_chapter_plugins import detect_chapter_primary_theorem


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


def _chapter_namespace(q: Dict[str, Any], chapter: str = "") -> str:
    return (
        (chapter or q.get("locked_chapter") or q.get("chapter") or "generic")
        .strip()
        .lower()
        or "generic"
    )


def _stem_structure_fingerprint(stem: str) -> str:
    """Chapter-agnostic structural hash — distinguishes stems with same answer shape."""
    norm = re.sub(r"\s+", " ", (stem or "").lower().strip())
    norm = re.sub(r"\d+(\.\d+)?", "#", norm)
    tokens = re.findall(
        r"\b(?:prove|find|express|hence|reduce|quadrant|radian|identity|"
        r"sin|cos|tan|cot|sec|cosec|or|hence)\b|π|pi",
        norm,
    )
    if not tokens:
        digest = hashlib.sha256(norm[:160].encode()).hexdigest()[:10]
        return f"fp_{digest}"
    key = "_".join(sorted(set(tokens))[:10])
    digest = hashlib.sha256(f"{norm}|{key}".encode()).hexdigest()[:8]
    return f"{key}_{digest}"


def _primary_theorem(
    stem: str,
    answer: str,
    archetype: str,
    *,
    chapter: str = "",
) -> str:
    ns = chapter or "generic"
    plugin = detect_chapter_primary_theorem(ns, stem, answer, archetype)
    if plugin:
        return f"{ns}:{plugin}"
    cognitive = (archetype or "").strip()
    if not cognitive:
        cognitive = (stem and _stem_structure_fingerprint(stem)) or "unspecified"
    return f"{ns}:{cognitive}"


def _reasoning_pattern(stem: str, answer: str, archetype: str) -> str:
    comps = extract_reasoning_signature(stem, answer=answer, archetype_id=archetype)
    base = signature_key(comps) or reasoning_signature_for_question(
        {"content": stem, "correct_answer": answer, "archetype_id": archetype}
    )
    fp = _stem_structure_fingerprint(stem)
    if base in ("fusion", "generic", "") and fp:
        return f"{base}:{fp}" if base else fp
    return base or fp or "generic"


def _answer_structure(stem: str, answer: str) -> str:
    low = f"{stem} {answer}".lower()
    if re.search(r"\bor\b", stem, re.I) and re.search(r"\(i\)", stem, re.I):
        if re.search(r"\bprove\b", low):
            return "proof_hence_or"
        return "multi_part_with_or"
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
        return "labeled_diagram"
    return "no_diagram"


def build_canonical_signature(
    q: Dict[str, Any],
    *,
    chapter: str = "",
) -> CanonicalSignature:
    stem = q.get("content") or q.get("question") or ""
    answer = _answer_text(q)
    arch = (
        q.get("archetype_id")
        or q.get("slot_archetype")
        or q.get("cognitive_type")
        or ""
    ).strip()
    ch = _chapter_namespace(q, chapter)
    return CanonicalSignature(
        primary_theorem=_primary_theorem(stem, answer, arch, chapter=ch),
        reasoning_pattern=_reasoning_pattern(stem, answer, arch),
        answer_structure=_answer_structure(stem, answer),
        diagram_archetype=_diagram_archetype(q, stem),
    )


def disambiguate_duplicate_signatures(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "",
) -> List[Dict[str, Any]]:
    """If two slots share a signature key, suffix later slots with @slotN (structural collision repair)."""
    annotate_canonical_signatures(questions, chapter=chapter)
    seen: Dict[str, int] = {}
    for q in sorted(
        questions,
        key=lambda x: int(x.get("slot_number") or x.get("order_index", 0) or 0),
    ):
        key = q.get("canonical_signature") or ""
        if not key:
            continue
        if key in seen:
            slot = int(q.get("slot_number") or (seen[key] + 1))
            parts = key.split("|", 3)
            parts[0] = f"{parts[0]}@slot{slot}"
            q["canonical_signature"] = "|".join(parts)
            q["signature_disambiguated"] = True
            parts_dict = dict(q.get("canonical_signature_parts") or {})
            parts_dict["primary_theorem"] = parts[0]
            q["canonical_signature_parts"] = parts_dict
        seen[q.get("canonical_signature") or key] = int(q.get("slot_number") or 0)
    return questions


def annotate_canonical_signatures(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "",
) -> List[Dict[str, Any]]:
    for q in questions:
        sig = build_canonical_signature(q, chapter=chapter)
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
    *,
    chapter: str = "",
) -> List[Dict[str, Any]]:
    """Step 1 policy: zero repeated canonical signatures per paper."""
    disambiguate_duplicate_signatures(questions, chapter=chapter)
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


def paper_has_duplicate_signatures(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "",
) -> Tuple[bool, List[str]]:
    annotate_canonical_signatures(questions, chapter=chapter)
    disambiguate_duplicate_signatures(questions, chapter=chapter)
    counts: Dict[str, int] = {}
    for q in questions:
        k = q.get("canonical_signature") or ""
        if k:
            counts[k] = counts.get(k, 0) + 1
    dups = [f"{k}×{n}" for k, n in counts.items() if n > 1]
    return (len(dups) > 0, dups)
