"""
Prepare question dicts for PDF export — sanitize LaTeX, validate figures.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.export.paper_validator import validate_questions_for_pdf
from app.generation.question_pipeline import finalize_questions_list
from app.generation.question_text import has_raw_latex

logger = logging.getLogger(__name__)


def prepare_questions_for_pdf(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize stems and reject export if LaTeX or glue bugs remain."""
    out = finalize_questions_list(questions)
    for q in out:
        content = q.get("content") or ""
        if has_raw_latex(content):
            logger.error(
                "PDF prep: raw LaTeX remains in Q%s after finalize",
                q.get("slot_number") or q.get("order_index"),
            )

    report = validate_questions_for_pdf(out)
    for w in report.get("warnings", []):
        logger.warning("PDF prep: %s", w)
    if not report["ok"]:
        logger.error("PDF prep validation failed: %s", report["errors"][:8])
        raise ValueError(
            "PDF export blocked — fix question text: "
            + "; ".join(report["errors"][:4])
        )
    return out
