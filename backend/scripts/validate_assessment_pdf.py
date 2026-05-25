#!/usr/bin/env python3
"""Validate assessment questions + exported PDF text layer."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.export.paper_validator import validate_pdf_text, validate_questions_for_pdf
from app.generation.paper_repair import sanitize_question_fields
from app.models import Assessment, Question


async def main(assessment_id: str) -> int:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        a = r.scalar_one_or_none()
        if not a:
            print("Not found:", assessment_id)
            return 1
        qr = await db.execute(select(Question).where(Question.assessment_id == assessment_id))
        questions = list(qr.scalars().all())
        by_id = {q.id: q for q in questions}
        ordered = [by_id[qid] for qid in (a.question_ids or []) if qid in by_id]

        payload = []
        for i, q in enumerate(ordered):
            payload.append(
                sanitize_question_fields(
                    {
                        "content": q.content,
                        "question_type": q.question_type,
                        "figure_url": q.figure_url,
                        "slot_number": i + 1,
                    }
                )
            )

        report = validate_questions_for_pdf(payload, paper_id=assessment_id)
        print("=== Question validation ===")
        print("OK:", report["ok"])
        for e in report["errors"]:
            print(" ERROR:", e)
        for w in report.get("warnings", []):
            print(" WARN:", w)

        pdf_path = os.path.join(
            "uploads", "exports", f"assessment_{assessment_id}.pdf"
        )
        if os.path.isfile(pdf_path):
            from PyPDF2 import PdfReader

            text = "\n".join(
                (p.extract_text() or "") for p in PdfReader(pdf_path).pages
            )
            pdf_report = validate_pdf_text(text, paper_id=assessment_id)
            print("\n=== PDF text validation ===")
            print("OK:", pdf_report["ok"])
            for e in pdf_report["errors"]:
                print(" ERROR:", e)
            return 0 if report["ok"] and pdf_report["ok"] else 1
        print("\n(No PDF at", pdf_path, ")")
        return 0 if report["ok"] else 1


if __name__ == "__main__":
    aid = sys.argv[1] if len(sys.argv) > 1 else "98df9728-ae3e-4f27-bf67-23ee5b4e75da"
    raise SystemExit(asyncio.run(main(aid)))
