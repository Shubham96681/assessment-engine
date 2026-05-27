"""
Quadratic Equations — L5 paper quality monitor (stem + whole-paper).

Encodes audit rules from production failures:
- Broken Hence / dead-weight sub-parts
- Unbalanced or malformed OR branches
- Constraint phrase fatigue across a paper
- Trivial verification (circular reciprocal checks)
- Discriminant nature imprecision (perfect square D ⇒ rational roots)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.generation.quadratic_hard_stem_gate import (
    evaluate_quadratic_full_hard_stem,
    fusion_signals,
)

# Phrases counted for whole-paper fatigue (max 1 per paper)
_CONSTRAINT_PHRASES: Tuple[Tuple[str, str], ...] = (
    (r"without\s+solv(?:ing)?\s+(?:by\s+)?(?:the\s+)?quadratic\s+formula", "without_quadratic_formula"),
    (r"quadratic\s+formula\s+only", "quadratic_formula_only"),
    (r"by\s+factoris(?:ation|ing)\s+only", "factorisation_only"),
)

# Minimum words per OR branch (heuristic split)
_OR_BRANCH_MIN_WORDS = 28
_OR_TRIVIAL_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"reciprocal", "trivial_reciprocal_product"),
    (r"product\s*=\s*1|product\s+is\s+1", "trivial_product_one"),
    (r"^find\s+q\b.*reciprocal", "trivial_find_q_reciprocal"),
)


def _stem(q_or_stem: Any) -> str:
    if isinstance(q_or_stem, str):
        return (q_or_stem or "").strip()
    if isinstance(q_or_stem, dict):
        return (
            (q_or_stem.get("content") or q_or_stem.get("question") or "")
        ).strip()
    return ""


def detect_dead_subpart(stem: str) -> List[str]:
    """(i) that only restates the equation or labels OR — not a task."""
    flags: List[str] = []
    low = stem.lower()
    if re.search(r"\(i\)\s*answer\s+one", low):
        flags.append("dead_subpart_or_label")
    if re.search(
        r"\(i\)\s*(?:for\s+)?\d*\s*x²[^.]{0,40}\s*=\s*0\s*[,;]?\s*(?:\(ii\)|$)",
        low,
    ) and not re.search(r"\(i\).*\b(find|compute|state|show|prove|form)\b", low):
        flags.append("dead_subpart_equation_only")
    if re.search(r"\(i\)\s*for\s+.*=\s*0\s*[,;]?\s*\(ii\)", low) and not re.search(
        r"\(i\).*\b(find|compute|state|show|prove|form|determine)\b", low
    ):
        flags.append("dead_subpart_equation_only")
    return flags


def detect_malformed_or(stem: str) -> List[str]:
    flags: List[str] = []
    low = stem.lower()
    if re.search(r"\(i\)\s*answer\s+one", low):
        flags.append("malformed_or_i_answer_one")
    if re.search(r"answer\s+one\.\s*or\s*\(ii\)", low):
        flags.append("malformed_or_ii_branch")
    if " or " in low and not re.search(
        r"answer\s+one\s+of\s+the\s+following|\(a\)|\(b\)", low
    ):
        if re.search(r"\bor\s*\(ii\)|\bor\s*\(i\)", low):
            flags.append("malformed_or_use_a_b_labels")
    return flags


def _split_or_branches(stem: str) -> Tuple[str, str]:
    """Return (branch_a, branch_b) text or empty."""
    low = stem
    # (a) ... OR (b)
    m = re.search(
        r"\(a\)\s*(.+?)\s*(?:\.\s*)?(?:or\s+)?\(b\)\s*(.+)$",
        low,
        re.I | re.S,
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # Answer ONE ... (i) ... OR (ii) ...
    m = re.search(
        r"answer\s+one[^.]*\.\s*(?:or\s+)?\(i\)\s*(.+?)\s+or\s+\(ii\)\s*(.+)$",
        low,
        re.I | re.S,
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()
    parts = re.split(r"\s+or\s+(?=\(ii\)|\(b\))", low, maxsplit=1, flags=re.I)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "", ""


def detect_unbalanced_or(stem: str) -> List[str]:
    flags: List[str] = []
    if not re.search(r"\banswer\s+one\b|\(a\)|\(b\)|\bor\s+\(ii\)", stem, re.I):
        return flags
    a, b = _split_or_branches(stem)
    if not a or not b:
        if re.search(r"\banswer\s+one\b", stem, re.I):
            flags.append("or_branches_not_parseable")
        return flags
    wa, wb = len(a.split()), len(b.split())
    if wa < _OR_BRANCH_MIN_WORDS:
        flags.append(f"or_branch_a_too_short:{wa}")
    if wb < _OR_BRANCH_MIN_WORDS:
        flags.append(f"or_branch_b_too_short:{wb}")
    for branch, label in ((a, "a"), (b, "b")):
        bl = branch.lower()
        for pat, tag in _OR_TRIVIAL_PATTERNS:
            if re.search(pat, bl):
                flags.append(f"or_branch_{label}_{tag}")
    if abs(wa - wb) > 25:
        flags.append(f"or_branch_length_imbalance:{wa}_vs_{wb}")
    return flags


def detect_subpart_reference_hallucination(stem: str) -> List[str]:
    """References (iii)/(iv) that were never introduced as sub-parts."""
    flags: List[str] = []
    low = stem.lower()
    for roman in ("iii", "iv", "v"):
        if re.search(rf"from\s+\({roman}\)", low) and not re.search(
            rf"\({roman}\)\s+(?:find|compute|state|show|prove|form|obtain|determine|hence)",
            low,
        ):
            flags.append(f"subpart_reference_hallucination:{roman}")
    return flags


def detect_incoherent_discriminant_factorisation(stem: str) -> List[str]:
    """Factorisation does not use the discriminant — only predicts nature."""
    flags: List[str] = []
    low = stem.lower()
    if re.search(r"discriminant", low) and re.search(r"factoris", low):
        if re.search(
            r"factoris\w*\s+using\s+(?:the\s+)?discriminant|"
            r"using\s+the\s+discriminant\s+from\s+\([ivx]+\)",
            low,
        ):
            flags.append("incoherent_discriminant_factorisation")
    return flags


def detect_broken_hence_discriminant_factor(stem: str) -> List[str]:
    """
    Discriminant in (i) + Hence factorisation in (ii) without requiring D result.
    """
    flags: List[str] = []
    low = stem.lower()
    flags.extend(detect_incoherent_discriminant_factorisation(stem))
    flags.extend(detect_subpart_reference_hallucination(stem))
    if not re.search(r"\bhence\b", low):
        return flags
    has_d = re.search(r"discriminant", low)
    has_factor = re.search(r"factoris", low)
    if has_d and has_factor:
        if re.search(
            r"hence\s+.*factoris",
            low,
        ) and not re.search(
            r"hence\s+.*(?:using|from|since|as)\s+(?:the\s+)?(?:nature|discriminant|d\s*[><=]|perfect[\s-]square)",
            low,
        ):
            if re.search(r"\(i\).*\(ii\).*hence", low, re.S):
                flags.append("hence_factorisation_independent_of_discriminant")
    return flags


def detect_circular_verification(stem: str) -> List[str]:
    flags: List[str] = []
    low = stem.lower()
    if re.search(r"reciprocal", low) and re.search(
        r"verify\s+(?:the\s+)?reciprocal\s+product", low
    ):
        flags.append("circular_reciprocal_verification")
    if re.search(r"verify\s+.*product\s*=\s*1", low) and re.search(
        r"reciprocal", low
    ):
        flags.append("circular_reciprocal_verification")
    return flags


def detect_discriminant_nature_gap(stem: str) -> List[str]:
    """Mentions discriminant but not rational/irrational when perfect-square D likely intended."""
    flags: List[str] = []
    low = stem.lower()
    if "discriminant" not in low:
        return flags
    if re.search(r"precise\s+nature|nature\s+of\s+the\s+roots", low):
        if not re.search(r"rational|irrational", low):
            if re.search(r"justify|state\s+the\s+nature", low):
                flags.append("nature_missing_rational_irrational_precision")
    return flags


def constraint_phrases_in_stem(stem: str) -> List[str]:
    low = stem.lower()
    found: List[str] = []
    for pat, tag in _CONSTRAINT_PHRASES:
        if re.search(pat, low):
            found.append(tag)
    return found


def evaluate_quadratic_stem_quality(
    stem: str,
    *,
    sparse_hard: bool = False,
) -> Dict[str, Any]:
    """Per-stem L5 audit — extends fusion gate."""
    content = _stem(stem)
    mtech = False
    try:
        from app.generation.topic_isolation import get_current_topic_state

        ts = get_current_topic_state() or {}
        mtech = bool(ts.get("mtech_quadratic"))
    except Exception:
        pass
    base = evaluate_quadratic_full_hard_stem(
        content, sparse_hard=sparse_hard, mtech=mtech
    )
    flags: List[str] = list(base.get("quadratic_hard_stem_flags") or [])
    flags.extend(detect_dead_subpart(content))
    flags.extend(detect_malformed_or(content))
    flags.extend(detect_unbalanced_or(content))
    flags.extend(detect_broken_hence_discriminant_factor(content))
    flags.extend(detect_circular_verification(content))
    flags.extend(detect_discriminant_nature_gap(content))
    constraint_tags = constraint_phrases_in_stem(content)
    ok = not flags
    return {
        **base,
        "stem_quality_ok": ok,
        "stem_quality_flags": flags,
        "constraint_phrases": constraint_tags,
        "fusion_signals": fusion_signals(content),
    }


def should_reject_quadratic_stem_quality(
    stem: str,
    *,
    sparse_hard: bool = False,
) -> bool:
    return not evaluate_quadratic_stem_quality(stem, sparse_hard=sparse_hard).get(
        "stem_quality_ok", True
    )


def evaluate_quadratic_question_quality(
    question: Dict[str, Any],
    *,
    sparse_hard: bool = False,
    math_verify: bool = True,
) -> Dict[str, Any]:
    """Stem L5 audit plus optional model-answer computational verification."""
    stem = _stem(question)
    ev = evaluate_quadratic_stem_quality(stem, sparse_hard=sparse_hard)
    flags: List[str] = list(ev.get("stem_quality_flags") or [])
    math: Dict[str, Any] = {"math_verification_ok": True, "math_verification_flags": []}
    if math_verify:
        from app.core.config import settings
        from app.generation.quadratic_math_verify import verify_quadratic_question_math

        if settings.ENABLE_QUADRATIC_MATH_VERIFY:
            math = verify_quadratic_question_math(question)
            flags.extend(math.get("math_verification_flags") or [])
    ok = not flags
    return {
        **ev,
        **math,
        "stem_quality_ok": ok,
        "stem_quality_flags": flags,
    }


def should_reject_quadratic_question_quality(
    question: Dict[str, Any],
    *,
    sparse_hard: bool = False,
) -> bool:
    return not evaluate_quadratic_question_quality(question, sparse_hard=sparse_hard).get(
        "stem_quality_ok", True
    )


def evaluate_quadratic_paper_quality(
    questions: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Whole-paper checks after parse / before delivery."""
    stems: List[str] = []
    per_slot: List[Dict[str, Any]] = []
    constraint_counts: Dict[str, int] = {}

    for i, q in enumerate(questions):
        stem = _stem(q)
        stems.append(stem)
        ev = evaluate_quadratic_question_quality(q)
        per_slot.append(
            {
                "slot": i + 1,
                "id": str(q.get("id") or i + 1),
                "stem_quality_ok": ev.get("stem_quality_ok"),
                "math_verification_ok": ev.get("math_verification_ok"),
                "flags": ev.get("stem_quality_flags"),
                "fusion_score": ev.get("quadratic_fusion_score"),
            }
        )
        for tag in ev.get("constraint_phrases") or []:
            constraint_counts[tag] = constraint_counts.get(tag, 0) + 1

    paper_flags: List[str] = []
    for tag, count in constraint_counts.items():
        if tag == "without_quadratic_formula" and count > 1:
            paper_flags.append(f"constraint_fatigue:{tag}:{count}>1")
        elif count > 2:
            paper_flags.append(f"constraint_fatigue:{tag}:{count}>2")

    verify_count = sum(
        1
        for s in stems
        if re.search(r"\bverify\b|\bverification\b", s, re.I)
    )
    if verify_count > 3:
        paper_flags.append(f"verification_fatigue:{verify_count}>3")

    factorisation_only = constraint_counts.get("factorisation_only", 0)
    if factorisation_only > 2:
        paper_flags.append(f"constraint_fatigue:factorisation_only:{factorisation_only}>2")

    failed = sum(1 for p in per_slot if not p.get("stem_quality_ok"))
    ok = failed == 0 and not paper_flags
    return {
        "paper_quality_ok": ok,
        "paper_quality_flags": paper_flags,
        "slots_failed": failed,
        "slots_total": len(questions),
        "per_slot": per_slot,
        "constraint_counts": constraint_counts,
    }


def should_reject_quadratic_paper(
    questions: Sequence[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    report = evaluate_quadratic_paper_quality(questions)
    reasons: List[str] = []
    if report.get("paper_quality_flags"):
        reasons.extend(report["paper_quality_flags"])
    for p in report.get("per_slot") or []:
        if not p.get("stem_quality_ok"):
            reasons.append(
                f"Q{p.get('slot')}:"
                + ";".join((p.get("flags") or [])[:3])
            )
    return (not report.get("paper_quality_ok", True)), reasons


def audit_pipeline_stage(
    stage: str,
    questions: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Structured log payload for generation_log — one entry per pipeline stage.
    """
    out: Dict[str, Any] = {"pipeline_stage": stage, "chapter": "quadratic"}
    if extra:
        out.update(extra)
    if questions is not None:
        paper = evaluate_quadratic_paper_quality(questions)
        out["paper_quality_ok"] = paper.get("paper_quality_ok")
        out["paper_quality_flags"] = paper.get("paper_quality_flags")
        out["slots_failed"] = paper.get("slots_failed")
        out["per_slot_preview"] = [
            {
                "slot": p.get("slot"),
                "ok": p.get("stem_quality_ok"),
                "flags": (p.get("flags") or [])[:4],
            }
            for p in (paper.get("per_slot") or [])[:12]
        ]
    return out


def regen_feedback_from_flags(flags: Sequence[str]) -> str:
    """Human-readable fix line for slot regen prompts."""
    mapping = {
        "dead_subpart_equation_only": "Remove dead-weight (i); integrate into one stem or make (i) a real task.",
        "dead_subpart_or_label": "Do not use (i) Answer ONE; use 'Answer ONE of the following. (a) ... OR (b) ...'.",
        "malformed_or_use_a_b_labels": "Use (a)/(b) OR branches of equal depth (4+ steps each).",
        "or_branch_b_trivial_reciprocal_product": "OR branch B must not be reciprocal-product only; use root-difference or parameter fusion.",
        "hence_factorisation_independent_of_discriminant": "Hence must use discriminant/nature from part (i), not independent factorisation.",
        "circular_reciprocal_verification": "Verification must be independent (e.g. substitute roots), not restate product=1.",
        "constraint_fatigue": "Vary constraint phrasing; at most one 'without quadratic formula' per paper.",
        "quad_insufficient_fusion": "Need 2+ fusion signals (Hence chain, word model+reject, OR, parameter range).",
        "nature_missing_rational_irrational_precision": "State rational vs irrational when discussing discriminant nature.",
    }
    parts: List[str] = []
    for f in flags:
        for key, msg in mapping.items():
            if key in f:
                parts.append(msg)
                break
        else:
            parts.append(f)
    return " ".join(dict.fromkeys(parts))[:500]
