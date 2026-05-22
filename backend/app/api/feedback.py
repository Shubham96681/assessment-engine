"""Feedback — No Auth"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Question, QuestionFeedback
from app.schemas import FeedbackCreate, FeedbackOut

router = APIRouter()


@router.post("", response_model=FeedbackOut)
async def submit_feedback(data: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    fb = QuestionFeedback(
        question_id=data.question_id,
        assessment_id=data.assessment_id,
        rating=data.rating,
        tags=data.tags or [],
        comment=data.comment,
    )
    db.add(fb)
    r = await db.execute(select(Question).where(Question.id == data.question_id))
    q = r.scalar_one_or_none()
    if q:
        q.quality_score = q.quality_score * 0.7 + (data.rating / 5.0) * 0.3
    await db.flush()
    return fb


@router.get("/assessment/{assessment_id}/summary")
async def feedback_summary(assessment_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(QuestionFeedback).where(QuestionFeedback.assessment_id == assessment_id)
    )
    items = r.scalars().all()
    if not items:
        return {"total": 0, "avg_rating": 0, "tags": {}}
    avg = sum(i.rating for i in items) / len(items)
    tags: dict = {}
    for i in items:
        for t in (i.tags or []):
            tags[t] = tags.get(t, 0) + 1
    return {"total": len(items), "avg_rating": round(avg, 2), "tags": tags}
