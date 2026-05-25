"""Create assessment with 5 Groq-generated questions (direct DB, no HTTP)."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app.core.cbse_curriculum_doc import ensure_cbse_curriculum_document
from app.core.database import AsyncSessionLocal
from app.core.demo_user import DEMO_USER_ID
from app.export.pdf_builder import PDFExporter
from app.core.config import settings
from app.generation.chapter_concept_classifier import resolve_locked_chapter
from app.generation.generator import QuestionGenerator
from app.generation.prior_question_bank import fetch_prior_stems_from_db
from app.generation.question_pipeline import prepare_questions_for_storage
from app.models import Assessment, Document, Question
from app.schemas import GenerationConfig


async def main() -> None:
    print(
        "LLM config:",
        f"RAG={settings.RAG_FILE_AGENT_ENABLED}",
        f"RAG_ONLY={settings.RAG_FILE_AGENT_ONLY}",
        f"GROQ={bool(settings.GROQ_API_KEY)}",
        f"PRIMARY={settings.PRIMARY_LLM}",
    )
    doc_id = await ensure_cbse_curriculum_document()
    config = GenerationConfig(
        document_id=doc_id,
        locked_chapter="trigonometry",
        title="Groq Demo - 5 Trigonometry Questions",
        total_questions=5,
        question_types=["MCQ", "ShortAnswer", "LongAnswer"],
        difficulty_distribution={"easy": 1, "medium": 2, "hard": 2},
        bloom_levels=["Remember", "Understand", "Apply"],
        topic_focus="Trigonometry",
        subject="Mathematics",
        class_level="10",
        instructions="Exam level: board_medium",
        use_chapter_pdf=False,
    )

    async with AsyncSessionLocal() as db:
        count_r = await db.execute(
            select(func.count(Assessment.id)).where(
                Assessment.user_id == DEMO_USER_ID,
                Assessment.document_id == doc_id,
            )
        )
        gen_num = (count_r.scalar() or 0) + 1
        assessment = Assessment(
            user_id=DEMO_USER_ID,
            document_id=doc_id,
            title=config.title or "Assessment",
            config=config.model_dump(mode="json"),
            question_ids=[],
            generation_num=gen_num,
            status="generating",
            total_marks=0.0,
        )
        db.add(assessment)
        await db.flush()
        aid = assessment.id
        await db.commit()
        print("created", aid)

    generator = QuestionGenerator()
    async with AsyncSessionLocal() as db:
        doc_r = await db.execute(select(Document).where(Document.id == doc_id))
        doc_row = doc_r.scalar_one_or_none()
        document_meta = {
            "filename": (doc_row.original_filename or doc_row.filename) if doc_row else "",
            "subject": doc_row.subject if doc_row else "Mathematics",
            "class_level": doc_row.class_level if doc_row else "10",
        }
        db_prior = await fetch_prior_stems_from_db(db, doc_id, exclude_assessment_id=aid)
        try:
            questions_data, generation_log = await generator.generate(
                config,
                DEMO_USER_ID,
                gen_num,
                document_meta=document_meta,
                supplement_prior_stems=db_prior,
            )
        except Exception as e:
            print("GENERATION ERROR:", type(e).__name__, e)
            async with AsyncSessionLocal() as db2:
                a = (
                    await db2.execute(select(Assessment).where(Assessment.id == aid))
                ).scalar_one()
                a.status = "failed"
                cfg = dict(a.config or {})
                cfg["failure_detail"] = str(e)
                a.config = cfg
                await db2.commit()
            print("DASHBOARD_URL=http://localhost:3000/assessments/" + aid)
            return

        locked_ch, _, _ = resolve_locked_chapter(
            filename=document_meta.get("filename", ""),
            topic_focus=config.topic_focus or "",
            context=(questions_data[0].get("content") if questions_data else "") or "",
        )
        questions_data = prepare_questions_for_storage(questions_data, chapter=locked_ch)

        a = (await db.execute(select(Assessment).where(Assessment.id == aid))).scalar_one()
        question_ids, total_marks = [], 0.0
        for qd in questions_data:
            q = Question(
                document_id=doc_id,
                assessment_id=aid,
                content=qd["content"],
                question_type=qd.get("question_type"),
                difficulty=qd.get("difficulty"),
                bloom_level=qd.get("bloom_level"),
                options=qd.get("options"),
                correct_answer=qd.get("correct_answer"),
                explanation=qd.get("explanation"),
                marks=qd.get("marks", 1.0),
                figure_url=qd.get("figure_url"),
                figure_type=qd.get("figure_type"),
                figure_spec=qd.get("figure_spec"),
                source_chunks=qd.get("source_chunks"),
                content_hash=qd.get("content_hash"),
                quality_score=qd.get("quality_score", 0.0),
            )
            db.add(q)
            await db.flush()
            question_ids.append(q.id)
            total_marks += float(q.marks or 1.0)

        exporter = PDFExporter(settings.LOCAL_STORAGE_PATH)
        try:
            pdf_path, key_path = await exporter.export_assessment(
                a.title,
                questions_data,
                assessment_id=aid,
            )
            a.pdf_url = pdf_path
            a.answer_key_url = key_path
        except Exception as ex:
            print("PDF export skipped:", ex)

        a.question_ids = question_ids
        a.total_marks = total_marks
        a.status = "ready" if question_ids else "failed"
        a.generation_log = generation_log
        await db.commit()

        print("status", a.status, "questions", len(question_ids), "marks", total_marks)
        print("DASHBOARD_URL=http://localhost:3000/assessments/" + aid)
        for i, qd in enumerate(questions_data, 1):
            stem = (qd.get("content") or "")[:90].replace("\n", " ")
            print(f"  Q{i}: [{qd.get('question_type')}] {stem}")


if __name__ == "__main__":
    asyncio.run(main())
