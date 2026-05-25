"""Re-sanitize question text in DB and rebuild PDFs (fixes <hr/>, restores ∠)."""
from __future__ import annotations

import asyncio
import sys

import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.export.store_pdfs import store_assessment_pdf_exports
from app.generation.answer_format import ensure_answer_text
from app.generation.question_text import ensure_plain_text
from app.models import Assessment, Question


async def main(assessment_id: str) -> None:
    async with AsyncSessionLocal() as db:
        a = (
            await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        ).scalar_one_or_none()
        if not a:
            print("not found", assessment_id)
            return
        qs = (
            await db.execute(select(Question).where(Question.assessment_id == assessment_id))
        ).scalars().all()
        for q in qs:
            if q.content:
                q.content = ensure_plain_text(q.content)
            if q.correct_answer:
                q.correct_answer = ensure_answer_text(q.correct_answer)
            if q.explanation:
                q.explanation = ensure_plain_text(q.explanation)
        await db.commit()
        urls = await store_assessment_pdf_exports(db, assessment_id)
        print("sanitized", len(qs), "questions")
        print(urls.get("pdf_url"))
        print("http://localhost:3000/assessments/" + assessment_id)


if __name__ == "__main__":
    aid = sys.argv[1] if len(sys.argv) > 1 else "4967f185-29d6-47ff-ad41-b42d11c5932d"
    asyncio.run(main(aid))
