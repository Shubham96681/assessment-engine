"""
Structural dedup — reject same theorem graph + entity skeleton + numeric pattern.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


def _extract_numbers(text: str) -> Tuple[str, ...]:
    nums = re.findall(r"\b(\d+(?:\.\d+)?)\b", text or "")
    return tuple(sorted(nums[:8]))


def _extract_entities(text: str) -> frozenset:
    """Point labels and key geometry tokens."""
    pts = set(re.findall(r"\b([A-Z])\b", text or ""))
    pts |= set(re.findall(r"\b([A-Z]{2})\b", text or ""))
    low = (text or "").lower()
    concepts = set()
    for term in (
        "tangent",
        "secant",
        "radius",
        "parallelogram",
        "rhombus",
        "diagonal",
        "quadratic",
        "discriminant",
        "area",
        "prove",
        "find",
    ):
        if term in low:
            concepts.add(term)
    return frozenset(pts | concepts)


def _operation_chain(stem: str) -> str:
    low = (stem or "").lower()
    ops: List[str] = []
    for tag, pat in (
        ("factor", r"factoris"),
        ("discriminant", r"discriminant|nature\s+of\s+roots"),
        ("equal_k", r"equal\s+roots|find\s+k\b"),
        ("area", r"\barea\b"),
        ("speed", r"\bspeed\b|\bkm/h\b"),
        ("prove", r"\bprove\b"),
        ("tangent_len", r"\btangent\b.*\bfind\b"),
    ):
        if re.search(pat, low):
            ops.append(tag)
    return "+".join(ops) or "generic"


def _stem_skeleton(stem: str) -> str:
    """Normalize stem for duplicate detection (ignore relabelled numbers)."""
    s = (stem or "").lower()
    s = re.sub(r"\d+(?:\.\d+)?", "#", s)
    s = re.sub(
        r"properties of [^.,;]+ from your chapter",
        "properties of TOPIC from your chapter",
        s,
    )
    s = re.sub(
        r"properties of the concept in the passage",
        "properties of TOPIC from your chapter",
        s,
    )
    s = re.sub(r"\s+", " ", s).strip()
    return s


def structural_signature(q: Dict[str, Any]) -> str:
    stem = q.get("content") or ""
    skeleton = _stem_skeleton(stem)
    nums = _extract_numbers(stem)
    entities = _extract_entities(stem)
    from app.generation.reasoning_signature import reasoning_signature_for_question

    rs = reasoning_signature_for_question(q)
    theorem = q.get("theorem_id") or q.get("slot_theorem") or ""
    arch = q.get("archetype_id") or q.get("slot_archetype") or ""
    cog = q.get("cognitive_type") or ""
    fig = q.get("figure_type") or ""
    ops = _operation_chain(stem)
    return f"{theorem}|{arch}|{cog}|{rs}|{ops}|{fig}|{skeleton}|{sorted(entities)}|{nums}"


def is_structural_duplicate(sig_a: str, sig_b: str) -> bool:
    if sig_a == sig_b:
        return True
    parts_a = sig_a.split("|")
    parts_b = sig_b.split("|")
    # theorem + archetype + reasoning graph + operation chain (ignore relabelled numbers)
    if len(parts_a) >= 6 and len(parts_b) >= 6 and parts_a[:6] == parts_b[:6]:
        return True
    if len(parts_a) >= 5 and len(parts_b) >= 5 and parts_a[:5] == parts_b[:5]:
        return True
    if len(parts_a) >= 4 and parts_a[:4] == parts_b[:4]:
        return True
    return False


def is_theorem_equivalent(q_a: Dict[str, Any], q_b: Dict[str, Any]) -> bool:
    from app.generation.theorem_variety_engine import theorem_equivalence_key

    return theorem_equivalence_key(q_a) == theorem_equivalence_key(q_b)


def filter_structural_duplicates(
    questions: List[Dict[str, Any]],
    *,
    min_keep: int = 0,
) -> List[Dict[str, Any]]:
    """Keep first of each structural signature; never return all duplicates."""
    if not questions:
        return []
    unique: List[Dict[str, Any]] = []
    sigs: List[str] = []
    for q in questions:
        sig = structural_signature(q)
        if any(is_structural_duplicate(sig, s) for s in sigs):
            q["dedup_reason"] = "structural_duplicate"
            continue
        if any(is_theorem_equivalent(q, u) for u in unique):
            q["dedup_reason"] = "theorem_equivalence_duplicate"
            continue
        sigs.append(sig)
        q["structural_signature"] = sig
        unique.append(q)
    if not unique and questions:
        # Prefer first item over shipping 5 identical copies
        q0 = dict(questions[0])
        q0["dedup_warning"] = "all_structural_duplicates_kept_one"
        return [q0]
    if min_keep > 0 and len(unique) < min_keep:
        # RAG apply / export must not drop below slot count (e.g. Q3 proof vs Q2 power)
        by_slot = sorted(
            questions,
            key=lambda x: int(x.get("slot_number") or x.get("order_index", 0) or 99),
        )
        return by_slot[:min_keep]
    return unique
