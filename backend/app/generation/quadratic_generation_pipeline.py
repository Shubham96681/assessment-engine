"""
Quadratic full-hard — shared pipeline guards for every generation path.

Used by: generator.py, assessments.apply-rag-response, scripts.
Prevents recurrence of:
- Pool collapse (structural dedup with delivery min_keep instead of pool)
- Broken Q2 / Hence / OR stems shipping
- Verification / constraint fatigue across papers
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def pool_min_keep(delivery_count: int) -> int:
    """Minimum stems to retain through structural dedup (pool size when oversampling)."""
    from app.generation.generation_oversample import (
        is_oversample_active,
        pool_question_count,
    )

    d = max(1, int(delivery_count))
    if is_oversample_active(d):
        return pool_question_count(d)
    return d


def structural_dedup_pool(
    questions: List[Dict[str, Any]],
    *,
    delivery_count: int,
) -> List[Dict[str, Any]]:
    from app.generation.structural_dedup import filter_structural_duplicates

    return filter_structural_duplicates(
        questions,
        min_keep=pool_min_keep(delivery_count),
    )


def filter_failed_quadratic_stems(
    questions: List[Dict[str, Any]],
    *,
    drop: bool = True,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Drop stems that fail L5 quadratic audits; annotate survivors."""
    from app.generation.quadratic_paper_quality import (
        evaluate_quadratic_question_quality,
        should_reject_quadratic_question_quality,
    )

    kept: List[Dict[str, Any]] = []
    rejected: List[str] = []
    for q in questions:
        stem = (q.get("content") or q.get("question") or "").strip()
        ev = evaluate_quadratic_question_quality(q)
        q["stem_quality_ok"] = ev.get("stem_quality_ok")
        q["stem_quality_flags"] = ev.get("stem_quality_flags")
        q["math_verification_ok"] = ev.get("math_verification_ok")
        q["math_verification_flags"] = ev.get("math_verification_flags")
        if should_reject_quadratic_question_quality(q):
            preview = (stem or "")[:80]
            math_flags = ev.get("math_verification_flags") or []
            if math_flags:
                preview += f" [{math_flags[0]}]"
            rejected.append(preview)
            if not drop:
                kept.append(q)
            continue
        kept.append(q)
    return (kept if drop else questions), rejected


def run_quadratic_pool_pipeline(
    questions: List[Dict[str, Any]],
    *,
    delivery_count: int,
    drop_failed_stems: bool = True,
    apply_structural_dedup: bool = True,
    prior_stems: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Standard post-parse pool processing for quadratic full-hard.
    Returns (questions, report dict for generation_log).
    """
    from app.generation.quadratic_paper_quality import (
        evaluate_quadratic_paper_quality,
        should_reject_quadratic_paper,
    )

    report: Dict[str, Any] = {"delivery_count": delivery_count}
    out = list(questions)

    if prior_stems:
        from app.generation.quadratic_duplicate_registry import (
            filter_questions_matching_prior_registry,
        )

        out, reg_rej = filter_questions_matching_prior_registry(out, prior_stems)
        report["registry_rejected_count"] = len(reg_rej)
        report["registry_rejected_previews"] = reg_rej[:8]
        if reg_rej:
            logger.warning(
                "Quadratic pool: dropped %d exact registry duplicate(s) vs prior papers",
                len(reg_rej),
            )

    from app.core.config import settings as _settings
    from app.generation.quadratic_math_gate import filter_quadratic_math_verified

    if _settings.ENABLE_QUADRATIC_MATH_VERIFY:
        out, math_rejected = filter_quadratic_math_verified(
            out, drop=_settings.QUADRATIC_MATH_VERIFY_BLOCK_DELIVERY
        )
        report["math_rejected_count"] = len(math_rejected)
        report["math_rejected_previews"] = [
            (q.get("content") or q.get("question") or "")[:80]
            + " "
            + ";".join((q.get("math_verification_flags") or [])[:2])
            for q in math_rejected[:8]
        ]
        if math_rejected:
            logger.warning(
                "Quadratic pool pipeline: dropped %d question(s) for math verification",
                len(math_rejected),
            )

    if drop_failed_stems:
        out, rejected = filter_failed_quadratic_stems(out, drop=True)
        report["stem_rejected_count"] = len(rejected)
        report["stem_rejected_previews"] = rejected[:8]
        if rejected:
            logger.warning(
                "Quadratic pool pipeline: dropped %d/%d stems",
                len(rejected),
                len(questions),
            )
        if not out and questions:
            logger.warning("Quadratic pool pipeline: all stems failed — keeping originals")
            out = list(questions)

    paper_q = evaluate_quadratic_paper_quality(out)
    report["paper_quality"] = paper_q

    from app.generation.quadratic_duplicate_registry import evaluate_archetype_coverage

    arch_ok, arch_flags = evaluate_archetype_coverage(out)
    report["archetype_coverage_ok"] = arch_ok
    report["archetype_coverage_flags"] = arch_flags
    if arch_flags:
        paper_q.setdefault("paper_quality_flags", []).extend(arch_flags)
        logger.warning("Quadratic archetype coverage: %s", arch_flags)
    block_paper, paper_reasons = should_reject_quadratic_paper(out)
    report["paper_block"] = block_paper
    report["paper_reasons"] = paper_reasons[:8]

    if apply_structural_dedup:
        before = len(out)
        out = structural_dedup_pool(out, delivery_count=delivery_count)
        report["structural_dedup"] = {"before": before, "after": len(out)}

    report["pool_count"] = len(out)
    return out, report


def resolve_quadratic_regen_prompt_body(plan: Any) -> str:
    """Compact production prompt for slot regen — avoids PromptContaminationError."""
    from app.generation.full_hard_mode import is_full_hard_paper
    from app.generation.production_prompts import resolve_production_prompt
    from app.generation.production_prompts.quadratic_full_hard import (
        build_quadratic_full_hard_prompt,
    )

    body = resolve_production_prompt(plan)
    ch = (getattr(plan, "locked_chapter", None) or "").strip().lower()
    fh = getattr(plan, "full_hard", False) or is_full_hard_paper(
        getattr(plan, "difficulty_distribution", None)
    )
    if not body and ch == "quadratic" and fh:
        body = build_quadratic_full_hard_prompt(plan)
    return body or ""
