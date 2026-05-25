"""
Paper integrity — slot order, cross-references, duplicate stems, role slots.

Catches failures that dedup/embedding miss (e.g. Q1 text swapped with Q5 fusion stem).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.generation.canonical_question_signature import (
    build_canonical_signature,
    paper_has_duplicate_signatures,
)
from app.generation.common_tangent_values import (
    is_common_external_tangent_stem,
    stem_has_required_external_tangent_givens,
    stem_has_valid_external_tangent_givens,
)


_REF_RE = re.compile(r"\bquestion\s+(\d+)\b", re.I)
_FUSION_STEM_RE = re.compile(
    r"using\s+(?:the\s+)?outer\s+circle\s+from\s+question\s+1",
    re.I,
)
_CONCENTRIC_ANCHOR_RE = re.compile(
    r"\bconcentric\s+circles?\b.*\bradii\b|\bchord\b.*\btouch",
    re.I | re.S,
)
_CHORD_FIND_RE = re.compile(
    r"\bfind\s+(?:the\s+)?(?:length\s+of\s+)?chord\s+[A-Z]{2}\b",
    re.I,
)
_Q2_PART_I_RE = re.compile(r"\(\s*i\s*\)", re.I)


def _slot_num(q: Dict[str, Any], fallback: int) -> int:
    sn = q.get("slot_number")
    if sn is not None and int(sn) >= 1:
        return int(sn)
    return fallback


def _normalize_stem(stem: str) -> str:
    s = (stem or "").lower()
    s = re.sub(r"\d+(?:\.\d+)?", "#", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def validate_cross_references(
    questions: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """Slot N must not cite Question M for M > N (forward reference)."""
    issues: List[str] = []
    ordered = sorted(
        questions,
        key=lambda x: (_slot_num(x, 99), x.get("order_index", 0)),
    )
    for i, q in enumerate(ordered):
        slot = _slot_num(q, i + 1)
        stem = q.get("content") or q.get("question") or ""
        for m in _REF_RE.finditer(stem):
            ref = int(m.group(1))
            if ref > slot:
                issues.append(f"forward_reference:slot{slot}_cites_Q{ref}")
            if ref == slot and slot == 1:
                if _FUSION_STEM_RE.search(stem) or (
                    "using" in stem.lower()
                    and "from question 1" in stem.lower()
                ):
                    issues.append("self_reference:Q1_cites_itself_as_prior")
    return (not issues, issues)


def _is_mixed_independent_template(paper_template_id: str) -> bool:
    return (paper_template_id or "").strip().lower() == "mixed_independent"


def question_matches_slot_role(
    q: Dict[str, Any],
    slot: int,
    *,
    chapter: str = "circles",
    paper_template_id: str = "",
) -> bool:
    """Whether stem fits the paper blueprint for this 1-based slot."""
    if chapter != "circles" or slot < 1:
        return True
    stem = (q.get("content") or q.get("question") or "").strip()
    if not stem:
        return False
    low = stem.lower()
    is_fusion = bool(_FUSION_STEM_RE.search(stem))

    if _is_mixed_independent_template(paper_template_id):
        if is_fusion and slot < 5:
            return False
        if slot == 3:
            return bool(re.search(r"\b(prove|show\s+that)\b", low))
        if slot == 5:
            return (
                re.search(r"\(\s*i{1,2}\s*\)", stem, re.I) is not None
                or "hence" in low
                or len(stem.split()) >= 24
            )
        return True

    is_concentric = "concentric" in low or bool(_CONCENTRIC_ANCHOR_RE.search(stem))
    if slot == 1:
        return is_concentric and not is_fusion
    if slot == 2:
        return "question 1" in low and not is_fusion
    if slot == 5:
        return is_fusion or ("question 1" in low and "question 2" in low)
    if slot == 3:
        return (
            not is_fusion
            and bool(re.search(r"\bprove\b", low))
            and (
                "meets the circle only" in low
                or "only at" in low
                or "converse" in low
                or ("perpendicular" in low and "tangent at" in low)
            )
        )
    if slot == 4:
        return (
            not is_fusion
            and (
                ("common" in low and "external" in low and "tangent" in low)
                or (
                    re.search(r"\btwo\s+circles?\b", low)
                    and re.search(r"\bcentres?\b", low)
                    and "tangent" in low
                )
            )
        )
    return True


def normalize_paper_slot_order(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort by slot_number/order_index and renumber 1..n for export."""
    ordered = sorted(
        questions,
        key=lambda x: (_slot_num(x, 99), x.get("order_index", 0)),
    )
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(ordered):
        q = dict(q)
        q["slot_number"] = i + 1
        q["order_index"] = i
        out.append(q)
    return out


def validate_slot_role(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
    paper_template_id: str = "",
) -> Tuple[bool, List[str]]:
    """Slot roles — chained concentric vs mixed_independent."""
    if chapter != "circles":
        return True, []
    issues: List[str] = []
    ordered = sorted(
        questions,
        key=lambda x: (_slot_num(x, 99), x.get("order_index", 0)),
    )
    if not ordered:
        return False, ["empty_paper"]

    tmpl = (paper_template_id or "").strip().lower()
    for i, q in enumerate(ordered):
        slot = _slot_num(q, i + 1)
        if not question_matches_slot_role(
            q, slot, chapter=chapter, paper_template_id=tmpl
        ):
            issues.append(f"slot_role_mismatch:slot{slot}")

    if _is_mixed_independent_template(tmpl):
        return (not issues, issues)

    q1 = ordered[0]
    s1 = (q1.get("content") or "").lower()
    if _FUSION_STEM_RE.search(s1):
        issues.append("slot1_is_fusion_stem_not_concentric_anchor")
    if not _CONCENTRIC_ANCHOR_RE.search(s1):
        if "concentric" not in s1:
            issues.append("slot1_missing_concentric_anchor")

    stems = [_normalize_stem(q.get("content") or "") for q in ordered]
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            if stems[i] == stems[j] and stems[i]:
                issues.append(f"duplicate_stem:slot{i+1}_slot{j+1}")
            if stems[i] and stems[i] in stems[j] and len(stems[i]) > 80:
                issues.append(f"stem_containment:slot{i+1}_inside_slot{j+1}")

    return (not issues, issues)


def validate_q1_q2_chord_duplicate(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
    paper_template_id: str = "",
) -> Tuple[bool, List[str]]:
    """Q2 must not repeat Q1 chord-find — only Hence / secant part."""
    if chapter != "circles" or _is_mixed_independent_template(paper_template_id):
        return True, []
    ordered = sorted(
        questions,
        key=lambda x: (_slot_num(x, 99), x.get("order_index", 0)),
    )
    if len(ordered) < 2:
        return True, []
    q1 = (ordered[0].get("content") or ordered[0].get("question") or "").lower()
    q2 = (ordered[1].get("content") or ordered[1].get("question") or "").lower()
    issues: List[str] = []
    if _CHORD_FIND_RE.search(q1) and _CHORD_FIND_RE.search(q2):
        if _Q2_PART_I_RE.search(q2) and "question 1" in q2:
            issues.append("q2_part_i_duplicates_q1_chord_find")
    # Normalized chord task overlap
    n1 = _normalize_stem(q1)
    n2 = _normalize_stem(q2)
    if "chord" in n1 and "chord" in n2 and "touch" in n1 and "touch" in n2:
        if n1 in n2 or (
            "find" in n2
            and "chord" in n2
            and "hence" not in n2.split("chord")[0][-40:]
        ):
            if _Q2_PART_I_RE.search(q2):
                issues.append("q2_part_i_duplicates_q1_chord_find")
    return (not issues, issues)


def validate_paper_integrity(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
    expected_count: int = 0,
    paper_template_id: str = "",
) -> Dict[str, Any]:
    """Run all integrity checks; attach flags to questions."""
    issues: List[str] = []
    tmpl = (paper_template_id or "").strip().lower()
    n = expected_count or len(questions)
    if len(questions) < n:
        issues.append(f"incomplete_paper:{len(questions)}/{n}")

    ok_ref, ref_issues = validate_cross_references(questions)
    issues.extend(ref_issues)

    ok_role, role_issues = validate_slot_role(
        questions, chapter=chapter, paper_template_id=tmpl
    )
    issues.extend(role_issues)

    ok_q12, q12_issues = validate_q1_q2_chord_duplicate(
        questions, chapter=chapter, paper_template_id=tmpl
    )
    issues.extend(q12_issues)

    from app.generation.concentric_values import validate_concentric_clean_values

    for q in questions:
        stem = q.get("content") or q.get("question") or ""
        slot = _slot_num(q, 0)
        if "concentric" in stem.lower() and slot == 1:
            ok_cv, cv_flags = validate_concentric_clean_values(stem)
            issues.extend(cv_flags)
        if slot == 4 and is_common_external_tangent_stem(stem):
            if not stem_has_required_external_tangent_givens(stem):
                issues.append("slot4_external_tangent_missing_givens")
            elif not stem_has_valid_external_tangent_givens(stem):
                issues.append("slot4_external_tangent_impossible_geometry")

    has_dup, dup_keys = paper_has_duplicate_signatures(questions)
    if has_dup:
        issues.append(f"canonical_signature_duplicates:{dup_keys}")

    for i, q in enumerate(questions):
        sig = build_canonical_signature(q)
        q["canonical_signature"] = sig.key()

    critical = (
        "forward_reference",
        "self_reference",
        "slot1_is_fusion",
        "slot_role_mismatch",
        "duplicate_stem",
        "q2_part_i_duplicates",
        "concentric_not_perfect_square",
        "canonical_signature_duplicates",
        "incomplete_paper",
        "slot4_external_tangent_missing_givens",
        "slot4_external_tangent_impossible_geometry",
    )
    ok = not any(any(c in x for c in critical) for x in issues)
    return {
        "paper_integrity_ok": ok,
        "paper_integrity_flags": issues,
        "paper_integrity_critical": ok,
    }


def should_reject_paper_integrity(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "circles",
    expected_count: int = 0,
    paper_template_id: str = "",
) -> bool:
    report = validate_paper_integrity(
        questions,
        chapter=chapter,
        expected_count=expected_count,
        paper_template_id=paper_template_id,
    )
    return not report.get("paper_integrity_ok", True)
