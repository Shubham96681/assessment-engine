"""5× LongAnswer, 100% hard — full QuestionGenerator pipeline + PDF export."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app.core.cbse_curriculum_doc import ensure_cbse_curriculum_document
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.demo_user import DEMO_USER_ID
from app.export.store_pdfs import store_assessment_pdf_exports
from app.generation.chapter_concept_classifier import resolve_locked_chapter
from app.generation.generator import QuestionGenerator
from app.generation.prior_question_bank import fetch_prior_stems_from_db
from app.generation.question_pipeline import prepare_questions_for_storage
from app.models import Assessment, Document, Question
from app.schemas import GenerationConfig, QuestionType


async def main() -> None:
    print(
        "config: RAG=%s GROQ=%s oversample=%s math_val=%s model=%s"
        % (
            settings.RAG_FILE_AGENT_ENABLED,
            bool(settings.GROQ_API_KEY),
            settings.GENERATION_OVERSAMPLE_ENABLED,
            settings.ENABLE_MATH_STEM_VALIDATION,
            settings.GROQ_MODEL,
        )
    )
    doc_id = await ensure_cbse_curriculum_document()
    config = GenerationConfig(
        document_id=doc_id,
        locked_chapter="trigonometry",
        title="Full Hard LongAnswer — Trigonometry (5Q)",
        total_questions=5,
        question_types=[QuestionType.LONG_ANSWER],
        difficulty_distribution={"easy": 0, "medium": 0, "hard": 100},
        bloom_levels=["Analyze", "Evaluate"],
        topic_focus="Trigonometry",
        subject="Mathematics",
        class_level="10",
        instructions="Exam level: full_hard — LongAnswer only, 100% hard",
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
            title=config.title,
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
    try:
        async with AsyncSessionLocal() as db:
            doc_r = await db.execute(select(Document).where(Document.id == doc_id))
            doc_row = doc_r.scalar_one_or_none()
            document_meta = {
                "filename": (doc_row.original_filename or doc_row.filename) if doc_row else "",
                "subject": "Mathematics",
                "class_level": "10",
                "topic_focus": "Trigonometry",
                "instructions": config.instructions,
            }
            db_prior = await fetch_prior_stems_from_db(db, doc_id, exclude_assessment_id=aid)
            questions_data, generation_log = await generator.generate(
                config,
                DEMO_USER_ID,
                gen_num,
                document_meta=document_meta,
                supplement_prior_stems=db_prior,
            )
    except Exception as e:
        print("GENERATION FAILED:", type(e).__name__, e)
        async with AsyncSessionLocal() as db:
            a = (
                await db.execute(select(Assessment).where(Assessment.id == aid))
            ).scalar_one()
            a.status = "failed"
            cfg = dict(a.config or {})
            cfg["failure_detail"] = str(e)
            a.config = cfg
            await db.commit()
        print("DASHBOARD_URL=http://localhost:3000/assessments/" + aid)
        return 1

    locked_ch, _, _ = resolve_locked_chapter(
        filename=document_meta.get("filename", ""),
        topic_focus=config.topic_focus or "",
        context=(questions_data[0].get("content") if questions_data else "") or "",
    )
    questions_data = prepare_questions_for_storage(questions_data, chapter=locked_ch)

    async with AsyncSessionLocal() as db:
        a = (await db.execute(select(Assessment).where(Assessment.id == aid))).scalar_one()
        qids, total = [], 0.0
        for qd in questions_data:
            q = Question(
                document_id=doc_id,
                assessment_id=aid,
                content=qd["content"],
                question_type=qd.get("question_type") or "LongAnswer",
                difficulty=qd.get("difficulty") or "hard",
                bloom_level=qd.get("bloom_level"),
                options=qd.get("options"),
                correct_answer=qd.get("correct_answer", ""),
                explanation=qd.get("explanation", ""),
                marks=qd.get("marks", 6.0),
                figure_url=qd.get("figure_url"),
                figure_type=qd.get("figure_type"),
                figure_spec=qd.get("figure_spec"),
                source_chunks=qd.get("source_chunks"),
                content_hash=qd.get("content_hash"),
                quality_score=qd.get("quality_score", 0.0),
            )
            db.add(q)
            await db.flush()
            qids.append(q.id)
            total += float(q.marks or 6.0)
        a.question_ids = qids
        a.total_marks = total
        a.status = "ready" if len(qids) >= 5 else ("failed" if not qids else "ready")
        a.generation_log = generation_log
        if len(qids) < 5:
            cfg = dict(a.config or {})
            cfg["failure_detail"] = f"Only {len(qids)} questions passed validation (need 5)."
            a.config = cfg
        await db.commit()

    if len(qids) >= 1:
        async with AsyncSessionLocal() as db:
            urls = await store_assessment_pdf_exports(db, aid)
            print("pdf", urls.get("pdf_url"))
            print("answer_key", urls.get("answer_key_url"))

    print("status", a.status, "questions", len(qids), "marks", total)
    print("DASHBOARD_URL=http://localhost:3000/assessments/" + aid)
    return 0 if len(qids) >= 5 else 1


if __name__ == "__main__":
    os.environ.setdefault("RAG_FILE_AGENT_ENABLED", "false")
    os.environ.setdefault("RAG_FILE_AGENT_ONLY", "false")
    os.environ.setdefault("GENERATION_OVERSAMPLE_ENABLED", "false")
    os.environ.setdefault("ENABLE_MATH_STEM_VALIDATION", "true")
    os.environ.setdefault("GROQ_MODEL", "llama-3.1-8b-instant")
    os.environ.setdefault("PRIMARY_LLM", "groq")
    raise SystemExit(asyncio.run(main()))
