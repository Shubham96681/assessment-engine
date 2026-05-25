"""
Examiner simulation — final filter before export (academic / pedagogical / professional).

Targets 98–99% perceived quality; not literal 100%.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.generation.canonical_question_signature import (
    annotate_canonical_signatures,
    paper_has_duplicate_signatures,
)
from app.generation.hardness_scorer import score_hardness
from app.generation.theorem_variety_engine import validate_paper_theorem_variety


def _stem(q: Dict[str, Any]) -> str:
    return (q.get("content") or q.get("question") or "").strip()


def _is_trivial_proof_visual(q: Dict[str, Any]) -> bool:
    """Proof already given by diagram markers."""
    stem = _stem(q).lower()
    spec = q.get("figure_spec") or {}
    if not re.search(r"\bprove\b", stem):
        return False
    if re.search(r"perpendicular|radius.*tangent|tangent.*radius", stem):
        if spec.get("show_right_angle") and spec.get("right_angle_at"):
            return True
    if re.search(r"\bprove\b.*\btangent\b", stem) and spec.get("tangent_marks"):
        return True
    return False


def _ambiguous_wording(stem: str) -> bool:
    low = stem.lower()
    if re.search(r"\bthis\s+angle\b|\bthat\s+line\b|\bit\s+follows\b(?!\s+that)", low):
        return True
    if re.search(r"<\s*[A-Z]{3}", stem):
        return True
    return False


def _excessive_scaffolding(stem: str) -> bool:
    parts = re.findall(r"\([ivx]+\)", stem, re.I)
    if len(parts) >= 3 and re.search(r"\d+\s*√|\d+\s*cm", stem):
        return True
    if re.search(r"step\s*1|first\s+find|then\s+find|finally\s+find", stem, re.I):
        return True
    return False


def academic_examiner_checks(
    q: Dict[str, Any],
    *,
    slot_band: str = "L3",
    ui_difficulty: str = "medium",
) -> List[str]:
    issues: List[str] = []
    stem = _stem(q)
    if not stem:
        issues.append("empty_stem")
    if _is_trivial_proof_visual(q):
        issues.append("trivial_proof_given_in_diagram")
    if _ambiguous_wording(stem):
        issues.append("ambiguous_wording")
    hard = score_hardness(q, slot_band=slot_band, ui_difficulty=ui_difficulty)
    if hard.get("hardness_reject"):
        issues.extend(hard.get("hardness_flags") or ["hardness_reject"])
    return issues


def pedagogical_examiner_checks(q: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    stem = _stem(q)
    if _excessive_scaffolding(stem):
        issues.append("excessive_scaffolding")
    low = stem.lower()
    if re.search(r"\bdefine\b|\bstate\s+the\s+theorem\b|\bwhat\s+is\s+a\s+tangent", low):
        issues.append("recall_not_understanding")
    return issues


def professional_examiner_checks(q: Dict[str, Any], index: int, total: int) -> List[str]:
    issues: List[str] = []
    stem = _stem(q)
    if len(stem) < 25 and q.get("type") == "FigureBased":
        issues.append("stem_too_sparse_for_figure")
    marks = float(q.get("marks") or 0)
    if total >= 5 and index == 0 and marks > 6:
        issues.append("Q1_marks_too_high")
    if total >= 5 and index == total - 1 and marks < 5:
        issues.append("final_slot_marks_too_low_for_hots")
    spec = q.get("figure_spec") or {}
    labels = spec.get("labels") or {}
    if isinstance(labels, dict) and len(labels) > 8:
        issues.append("figure_label_overload")
    return issues


def run_examiner_simulation(
    questions: List[Dict[str, Any]],
    *,
    locked_chapter: str = "circles",
    ui_difficulty: str = "hard",
    full_hard: bool = False,
    slot_bands: Optional[List[str]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Paper-level examiner pass. Returns (ok, report).
    """
    report: Dict[str, Any] = {
        "academic": [],
        "pedagogical": [],
        "professional": [],
        "paper": [],
    }
    if not questions:
        return False, {**report, "paper": ["empty_paper"]}

    annotate_canonical_signatures(questions)
    has_dup, dup_keys = paper_has_duplicate_signatures(questions)
    if has_dup:
        report["paper"].append(f"canonical_signature_duplicates:{dup_keys}")

    variety_ok, variety_issues = validate_paper_theorem_variety(
        questions,
        locked_chapter=locked_chapter,
        full_hard=full_hard,
        question_count=len(questions),
    )
    if not variety_ok:
        report["paper"].extend(variety_issues[:12])

    bands = slot_bands or ["L5"] * len(questions)
    for i, q in enumerate(questions):
        band = bands[i] if i < len(bands) else "L5"
        ac = academic_examiner_checks(q, slot_band=band, ui_difficulty=ui_difficulty)
        pe = pedagogical_examiner_checks(q)
        pr = professional_examiner_checks(q, i, len(questions))
        if ac:
            report["academic"].append({"slot": i + 1, "issues": ac})
        if pe:
            report["pedagogical"].append({"slot": i + 1, "issues": pe})
        if pr:
            report["professional"].append({"slot": i + 1, "issues": pr})

    ok = not report["paper"] and not report["academic"]
    report["examiner_ok"] = ok
    return ok, report


def should_reject_examiner(
    q: Dict[str, Any],
    *,
    index: int = 0,
    total: int = 5,
    slot_band: str = "L5",
    ui_difficulty: str = "hard",
) -> bool:
    ac = academic_examiner_checks(q, slot_band=slot_band, ui_difficulty=ui_difficulty)
    pe = pedagogical_examiner_checks(q)
    pr = professional_examiner_checks(q, index, total)
    return bool(ac or pe or pr)
