"""One-off: repair questions + re-render figures + PDF for an assessment id."""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.export.pdf_builder import PDFExporter
from app.generation.chapter_concept_classifier import resolve_locked_chapter
from app.generation.figures import FigureGenerator
from app.generation.paper_repair import repair_paper_questions
from app.generation.figure_spec_builder import enrich_figure_spec
from app.generation.figure_label_validator import needs_figure_rebuild
from app.generation.idiomatic_geometry_patterns import apply_idiomatic_fix
from app.generation.question_pipeline import (
    finalize_question_dict,
    finalize_questions_list,
)
from app.models import Assessment, Document, Question


async def main(assessment_id: str) -> None:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        a = r.scalar_one_or_none()
        if not a:
            print("Assessment not found:", assessment_id)
            return
        qr = await db.execute(select(Question).where(Question.assessment_id == assessment_id))
        questions = list(qr.scalars().all())
        by_id = {q.id: q for q in questions}
        ordered = [by_id[qid] for qid in (a.question_ids or []) if qid in by_id]

        doc_r = await db.execute(select(Document).where(Document.id == a.document_id))
        doc_row = doc_r.scalar_one_or_none()

        payload = []
        for i, q in enumerate(ordered):
            content = finalize_question_dict({"content": q.content or ""})["content"]
            fixed, _ = apply_idiomatic_fix(content)
            fixed = finalize_question_dict({"content": fixed})["content"]
            spec = q.figure_spec
            if q.question_type == "FigureBased":
                if needs_figure_rebuild(fixed, spec):
                    spec = enrich_figure_spec(fixed, None)
                else:
                    spec = enrich_figure_spec(fixed, spec)
            payload.append(
                {
                    "content": fixed,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "bloom_level": q.bloom_level,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "marks": q.marks or 1.0,
                    "figure_url": q.figure_url,
                    "figure_type": q.figure_type or "labeled_diagram",
                    "figure_spec": spec,
                    "order_index": i,
                    "slot_number": i + 1,
                }
            )

        locked, _, _ = resolve_locked_chapter(
            filename=doc_row.filename if doc_row else "",
            topic_focus=(a.config or {}).get("topic_focus") or "",
            context=(payload[0].get("content") or "") if payload else "",
        )
        payload = repair_paper_questions(
            payload, chapter=locked or "circles", re_enrich_figures=True
        )
        payload = finalize_questions_list(payload)

        fig_gen = FigureGenerator()
        for q_row, qd in zip(ordered, payload):
            finalized = finalize_question_dict(
                {
                    "content": qd["content"],
                    "correct_answer": qd.get("correct_answer") or q_row.correct_answer or "",
                    "explanation": qd.get("explanation") or q_row.explanation or "",
                }
            )
            q_row.content = finalized["content"]
            q_row.correct_answer = finalized.get("correct_answer") or q_row.correct_answer
            q_row.explanation = finalized.get("explanation") or q_row.explanation
            qd["content"] = finalized["content"]
            qd["correct_answer"] = q_row.correct_answer
            qd["explanation"] = q_row.explanation
            if qd.get("figure_spec"):
                q_row.figure_spec = qd["figure_spec"]
            if q_row.question_type != "FigureBased":
                continue
            spec = qd.get("figure_spec")
            if not spec:
                continue
            url = await fig_gen.generate(spec, qd.get("figure_type") or "labeled_diagram")
            if url:
                q_row.figure_url = url
                qd["figure_url"] = url
            print(f"Q{qd['slot_number']}: {qd['content'][:90]}...")
            print(f"   fig -> {url}")

        cfg = dict(a.config or {})
        cfg["title"] = cfg.get("title") or a.title or "Circles — Hard Paper"
        if cfg.get("title") == "assess":
            cfg["title"] = "Circles — Hard Assessment"
            a.title = cfg["title"]
        cfg.setdefault("subject", "Mathematics")
        cfg.setdefault("class_level", "10")

        exporter = PDFExporter(settings.LOCAL_STORAGE_PATH)
        urls = exporter.export_assessment(
            questions=payload,
            config=cfg,
            assessment_id=assessment_id,
            teacher_name="Teacher",
            institution="Assessment Engine",
        )
        a.pdf_url = urls["pdf_url"]
        a.answer_key_url = urls["answer_key_url"]
        await db.commit()
        print("PDF:", a.pdf_url)


if __name__ == "__main__":
    aid = sys.argv[1] if len(sys.argv) > 1 else "98df9728-ae3e-4f27-bf67-23ee5b4e75da"
    asyncio.run(main(aid))
