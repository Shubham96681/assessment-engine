"""
Prepare question dicts for PDF export — sanitize LaTeX, validate figures.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.core.config import settings
from app.export.paper_validator import validate_questions_for_pdf
from app.generation.chapter_concept_classifier import resolve_locked_chapter
from app.generation.figure_label_validator import needs_figure_rebuild
from app.generation.question_pipeline import prepare_questions_for_export_payload
from app.export.pdf_fonts import register_pdf_unicode_font
from app.generation.question_text import ensure_plain_text, has_raw_latex

logger = logging.getLogger(__name__)


def prepare_questions_for_pdf(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "",
) -> List[Dict[str, Any]]:
    """Repair + sanitize stems, then reject export if validation still fails."""
    register_pdf_unicode_font()
    ch = (chapter or "").strip().lower()
    if not ch and questions:
        locked, _, _ = resolve_locked_chapter(
            filename="",
            topic_focus="",
            context=(questions[0].get("content") or questions[0].get("question") or ""),
        )
        ch = (locked or "circles").strip().lower()
    if not ch:
        ch = "circles"
    re_figures = settings.PDF_RE_ENRICH_FIGURES
    if not re_figures:
        for q in questions:
            if q.get("question_type") == "FigureBased" and not q.get("figure_url"):
                re_figures = True
                break
            spec = q.get("figure_spec")
            if q.get("question_type") == "FigureBased" and needs_figure_rebuild(
                q.get("content") or "", spec if isinstance(spec, dict) else None
            ):
                re_figures = True
                break

    from app.generation.question_type_resolver import coerce_exportable_question_types

    questions = coerce_exportable_question_types(questions, ch)
    out = prepare_questions_for_export_payload(
        questions, chapter=ch, re_enrich_figures=re_figures
    )
    for q in out:
        for field in ("content", "question", "correct_answer", "explanation"):
            if isinstance(q.get(field), str) and q[field]:
                q[field] = ensure_plain_text(q[field])
        if q.get("content"):
            q["question"] = q["content"]
        content = q.get("content") or ""
        if has_raw_latex(content):
            slot = q.get("slot_number") or q.get("order_index")
            msg = f"Q{slot}: raw LaTeX remains after PDF sanitize"
            logger.error("PDF prep: %s", msg)
            raise ValueError(f"PDF export blocked — {msg}")

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
