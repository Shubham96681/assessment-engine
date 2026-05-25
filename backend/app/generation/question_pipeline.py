"""
Global question finalization — every chapter/book must pass through here.

Use before DB save, after LLM parse, after chapter repair, and before PDF export.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.generation.paper_repair import repair_paper_questions, sanitize_question_fields

logger = logging.getLogger(__name__)

_TEXT_FIELDS = ("content", "question", "correct_answer", "explanation", "options")


def finalize_question_dict(q: Dict[str, Any]) -> Dict[str, Any]:
    """LaTeX strip, Unicode math, spacing — safe for UI and PDF."""
    out = sanitize_question_fields(q)
    opts = out.get("options")
    if isinstance(opts, list):
        out["options"] = [
            sanitize_question_fields({"content": o})["content"]
            if isinstance(o, str) and o
            else o
            for o in opts
        ]
    elif isinstance(opts, dict):
        out["options"] = {
            k: sanitize_question_fields({"content": v})["content"]
            if isinstance(v, str) and v
            else v
            for k, v in opts.items()
        }
    return out


def finalize_questions_list(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize every question dict (all chapters, all question types)."""
    return [finalize_question_dict(dict(q)) for q in questions]


def prepare_questions_after_generation(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "generic",
    repair: bool = True,
    re_enrich_figures: bool = False,
) -> List[Dict[str, Any]]:
    """
    Post-generation pipeline: sanitize → optional chapter repair → sanitize again.
    Chapter-specific geometry repair runs only when repair=True (circles hard papers, etc.).
    """
    if not questions:
        return []
    ch = (chapter or "generic").strip().lower() or "generic"
    qs = finalize_questions_list(questions)
    if repair:
        qs = repair_paper_questions(
            qs,
            chapter=ch,
            re_enrich_figures=re_enrich_figures,
        )
        qs = finalize_questions_list(qs)
    from app.core.config import settings

    if settings.ENABLE_CHAPTER_PAPER_QUALITY:
        from app.generation.chapter_paper_quality import (
            normalize_chapter_paper_marks,
            validate_chapter_paper_quality,
        )

        normalize_chapter_paper_marks(qs, chapter=ch)
        report = validate_chapter_paper_quality(qs, chapter=ch)
        if not report.get("chapter_quality_ok"):
            logger.warning(
                "Chapter paper quality flags (%s): %s",
                ch,
                (report.get("chapter_quality_critical") or report.get("chapter_quality_flags"))[:8],
            )
    return qs


def prepare_questions_for_storage(
    questions: List[Dict[str, Any]],
    *,
    chapter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Before writing Question rows to the database."""
    return prepare_questions_after_generation(
        questions,
        chapter=chapter or "generic",
        repair=False,
    )


def prepare_questions_for_export_payload(
    questions: List[Dict[str, Any]],
    *,
    chapter: str = "generic",
    re_enrich_figures: bool = True,
) -> List[Dict[str, Any]]:
    """Before PDF build: sanitize only for non-geometry chapters (avoid stem swaps)."""
    ch = (chapter or "generic").strip().lower() or "generic"
    repair = ch == "circles"
    return prepare_questions_after_generation(
        questions,
        chapter=ch,
        repair=repair,
        re_enrich_figures=re_enrich_figures,
    )
