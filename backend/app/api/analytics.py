"""Analytics — No Auth"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Document, Assessment, Question

router = APIRouter()


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    assessments = (await db.execute(select(func.count(Assessment.id)))).scalar() or 0

    total_q = (await db.execute(select(func.count(Question.id)))).scalar() or 0
    avg_q = round(
        (await db.execute(select(func.avg(Question.quality_score)))).scalar() or 0,
        3,
    )

    bloom, diff, qtype = {}, {}, {}
    for col, target in (
        (Question.bloom_level, bloom),
        (Question.difficulty, diff),
        (Question.question_type, qtype),
    ):
        r = await db.execute(select(col, func.count()).group_by(col))
        for key, count in r.all():
            target[key or "Unknown"] = count

    recent_r = await db.execute(
        select(Assessment).order_by(Assessment.created_at.desc()).limit(5)
    )
    recent = recent_r.scalars().all()

    recent_out = []
    for a in recent:
        q_preview = []
        qr = await db.execute(
            select(Question).where(Question.assessment_id == a.id)
        )
        by_id = {q.id: q for q in qr.scalars().all()}
        ordered = []
        for qid in a.question_ids or []:
            if qid in by_id:
                ordered.append(by_id[qid])
        if not ordered:
            ordered = list(by_id.values())
        for q in ordered[:5]:
            q_preview.append({
                "id": q.id,
                "content": (q.content or "")[:200],
                "question_type": q.question_type,
                "marks": q.marks,
                "figure_url": q.figure_url,
            })
        recent_out.append({
            "id": a.id,
            "title": a.title,
            "status": a.status,
            "total_marks": a.total_marks,
            "question_count": len(a.question_ids or []),
            "generation_steps": len(a.generation_log or []),
            "pdf_url": a.pdf_url,
            "answer_key_url": a.answer_key_url,
            "created_at": a.created_at.isoformat(),
            "sample_questions": q_preview,
        })

    return {
        "total_documents": docs,
        "total_assessments": assessments,
        "total_questions_generated": total_q,
        "avg_quality_score": avg_q,
        "bloom_distribution": bloom,
        "difficulty_distribution": diff,
        "question_type_distribution": qtype,
        "recent_assessments": recent_out,
    }


@router.get("/quality-trend")
async def quality_trend(document_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Assessment.generation_num, func.avg(Question.quality_score))
        .join(Question, Question.assessment_id == Assessment.id)
        .where(Assessment.document_id == document_id)
        .group_by(Assessment.generation_num)
        .order_by(Assessment.generation_num)
    )
    return [{"generation": row[0], "avg_quality": round(row[1] or 0, 3)} for row in r.all()]
