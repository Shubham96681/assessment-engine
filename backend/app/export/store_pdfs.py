"""Persist question-paper + answer-key PDF URLs on an assessment."""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.export.pdf_builder import PDFExporter
from app.models import Assessment, Question


async def store_assessment_pdf_exports(
    db: AsyncSession,
    assessment_id: str,
) -> Dict[str, str]:
    from app.api.assessments import _ordered_questions, _questions_for_export

    r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = r.scalar_one_or_none()
    if not a:
        raise ValueError(f"Assessment not found: {assessment_id}")
    qr = await db.execute(select(Question).where(Question.assessment_id == assessment_id))
    questions = qr.scalars().all()
    if not questions:
        raise ValueError("No questions to export")

    cfg_dict = dict(a.config or {})
    cfg_dict["title"] = a.title or cfg_dict.get("title") or "Assessment"
    cfg_dict.setdefault("subject", "Mathematics")
    cfg_dict.setdefault("class_level", "10")

    payload = _questions_for_export(a, questions, polish=True)
    for i, qd in enumerate(payload):
        qd["order_index"] = i
        qd["slot_number"] = i + 1

    exporter = PDFExporter(settings.LOCAL_STORAGE_PATH)
    urls = exporter.export_assessment(
        questions=payload,
        config=cfg_dict,
        assessment_id=assessment_id,
        teacher_name="Teacher",
        institution="Assessment Engine",
    )
    a.pdf_url = urls["pdf_url"]
    a.answer_key_url = urls["answer_key_url"]
    await db.commit()
    return urls
