"""
Per-generation uniqueness while preserving Template A slot roles (Q1→Q5 chain).

- Fresh numeric givens and point labels each generation
- Reject papers too similar to prior stems (skeleton / slot pattern)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.generation.concentric_values import RECOMMENDED_PAIRS, parse_concentric_radii
from app.generation.structural_dedup import _stem_skeleton, structural_signature

# Rotate external-point labels so Q2/Q5 are not always P/A/G/H
LABEL_ROTATIONS: List[Dict[str, str]] = [
    {"q2_ext": "P", "q2_tan": "PA", "q2_sec": "PQR", "fusion_ext": "G", "fusion_tan": "GH", "fusion_sec": "GJK"},
    {"q2_ext": "N", "q2_tan": "NE", "q2_sec": "NFK", "fusion_ext": "L", "fusion_tan": "LM", "fusion_sec": "LJK"},
    {"q2_ext": "T", "q2_tan": "TS", "q2_sec": "TUV", "fusion_ext": "W", "fusion_tan": "WX", "fusion_sec": "WYZ"},
    {"q2_ext": "D", "q2_tan": "DE", "q2_sec": "DFG", "fusion_ext": "H", "fusion_tan": "HJ", "fusion_sec": "HJK"},
    {"q2_ext": "M", "q2_tan": "MN", "q2_sec": "MPQ", "fusion_ext": "R", "fusion_tan": "RS", "fusion_sec": "RUV"},
]

_CONCENTRIC_PAIR_RE = re.compile(
    r"\bradii\s+(\d+(?:\.\d+)?)\s*cm\s+and\s+(\d+(?:\.\d+)?)\s*cm",
    re.I,
)


def extract_concentric_pairs(stems: List[str]) -> Set[Tuple[int, int]]:
    used: Set[Tuple[int, int]] = set()
    for stem in stems or []:
        m = _CONCENTRIC_PAIR_RE.search(stem or "")
        if not m:
            continue
        a, b = int(float(m.group(1))), int(float(m.group(2)))
        used.add((max(a, b), min(a, b)))
    return used


def pick_fresh_concentric_pair(
    generation_num: int,
    used_pairs: Set[Tuple[int, int]],
) -> Tuple[int, int, int]:
    """Return (R, r, chord) from RECOMMENDED_PAIRS, preferring unused pairs."""
    available = [
        (R, r, chord)
        for R, r, chord in RECOMMENDED_PAIRS
        if (R, r) not in used_pairs
    ]
    pool = available or list(RECOMMENDED_PAIRS)
    idx = max(0, (generation_num or 1) - 1) % len(pool)
    return pool[idx]


def pick_label_rotation(
    generation_num: int,
    prior_stems: List[str],
) -> Dict[str, str]:
    """Pick a label set not dominant in recent Q2 stems."""
    blob = " ".join(prior_stems[:15]).upper()
    n = len(LABEL_ROTATIONS)
    start = max(0, (generation_num or 1) - 1) % n
    for offset in range(n):
        rot = LABEL_ROTATIONS[(start + offset) % n]
        ext = rot["q2_ext"]
        if f"POINT {ext}" not in blob and f" {ext} " not in f" {blob} ":
            return rot
    return LABEL_ROTATIONS[start % n]


def build_rag_uniqueness_block(
    *,
    generation_num: int,
    prior_stems: List[str],
    chapter: str = "circles",
    question_count: int = 5,
    full_hard: bool = True,
) -> str:
    """Inject into rag_query.txt — unique givens but mandatory slot chain."""
    lines = [
        "UNIQUENESS MANDATE (mandatory — follow slot chain from EXERCISE BLUEPRINT / dependency graph):",
        "- Every generation MUST use NEW numbers and point labels vs PRIOR QUESTIONS.",
        "- Keep Q1→Q5 roles: concentric anchor → Hence tangent–secant → converse proof → two-circle tangent → fusion.",
        "- Do NOT copy stems, radii pairs, or label sets from PRIOR QUESTIONS (paraphrase with new labels).",
        f"- Generation #{generation_num or 1}: treat as a fresh paper.",
    ]
    ch = (chapter or "").lower()
    if ch == "circles" and question_count >= 5 and full_hard:
        used = extract_concentric_pairs(prior_stems)
        R, r, chord = pick_fresh_concentric_pair(generation_num, used)
        rot = pick_label_rotation(generation_num, prior_stems)
        lines.extend(
            [
                "",
                "SUGGESTED FRESH GIVENS (use these or equivalent clean integers — NOT prior radii):",
                f"- Q1: concentric centre O, radii {R} cm and {r} cm (chord of larger = {chord} cm).",
                f"- Q2: external point {rot['q2_ext']}, tangent {rot['q2_tan']}, secant {rot['q2_sec']} — Hence only, cite Q1.",
                f"- Q3: independent converse tangent proof (new point label, not {rot['q2_ext']}).",
                f"- Q4: two circles with centres/labels different from O and {rot['q2_ext']}.",
                f"- Q5: fusion with {rot['fusion_ext']} from O, tangent {rot['fusion_tan']}, secant {rot['fusion_sec']}; cite Q1+Q2.",
            ]
        )
        if used:
            banned = ", ".join(f"({a},{b})" for a, b in sorted(used)[:8])
            lines.append(f"- FORBIDDEN radii pairs already used: {banned}.")
    lines.append("")
    return "\n".join(lines)


def _slot_skeletons(questions: List[Dict[str, Any]]) -> List[str]:
    ordered = sorted(
        questions,
        key=lambda q: int(q.get("slot_number") or q.get("order_index", 0) + 1),
    )
    return [_stem_skeleton(q.get("content") or "") for q in ordered]


def paper_matches_prior_skeleton(
    questions: List[Dict[str, Any]],
    prior_stems: List[str],
) -> Tuple[bool, str]:
    """
    True if this paper's slot skeletons match a contiguous block of prior stems
    (same theorem pattern with relabelled numbers only).
    """
    if not questions or not prior_stems:
        return False, ""
    new_skel = _slot_skeletons(questions)
    if not any(new_skel):
        return False, ""
    prior_skel = [_stem_skeleton(s) for s in prior_stems if s]
    n = len(new_skel)
    for i in range(len(prior_skel) - n + 1):
        block = prior_skel[i : i + n]
        if block == new_skel:
            return True, f"paper_skeleton_matches_prior_stems_at_index_{i}"
    # Full-paper fingerprint: all 5 slots identical skeleton to last assessment
    if n >= 5 and prior_skel[-5:] == new_skel:
        return True, "paper_skeleton_matches_last_5_prior_stems"
    return False, ""


def validate_unique_vs_priors(
    questions: List[Dict[str, Any]],
    prior_stems: List[str],
) -> Tuple[bool, List[str]]:
    """Reject if any slot or whole paper duplicates prior generation."""
    issues: List[str] = []
    if not prior_stems:
        return True, issues

    matched, reason = paper_matches_prior_skeleton(questions, prior_stems)
    if matched:
        issues.append(reason)

    prior_sigs = {structural_signature({"content": s}) for s in prior_stems if s}
    for i, q in enumerate(questions):
        sig = structural_signature(q)
        if sig in prior_sigs:
            issues.append(f"Q{i + 1}:structural_signature_in_history")
        sk = _stem_skeleton(q.get("content") or "")
        for ps in prior_stems:
            if sk and sk == _stem_skeleton(ps):
                issues.append(f"Q{i + 1}:skeleton_duplicate_of_prior")
                break

    return (not issues, issues)
