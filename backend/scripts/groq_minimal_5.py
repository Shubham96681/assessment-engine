"""Minimal Groq call → 5 questions → assessment ready on dashboard."""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AsyncOpenAI
from sqlalchemy import func, select

from app.core.cbse_curriculum_doc import ensure_cbse_curriculum_document
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.demo_user import DEMO_USER_ID
from app.generation.generator import QuestionGenerator
from app.models import Assessment, Question
from app.schemas import GenerationConfig, QuestionType

PROMPT = """You are a CBSE Class 10 Mathematics examiner.
Write exactly 5 NEW trigonometry questions (no circles/geometry).
Return ONLY a JSON array with objects:
id (1-5), type (MCQ|ShortAnswer|LongAnswer), question, marks, correct_answer.
For MCQ include options as {{"A":"...","B":"...","C":"...","D":"..."}} and correct_answer as the letter.
Mix: 2 MCQ, 2 ShortAnswer, 1 LongAnswer. Use approved angles (30,45,60,75,105,120,135,150).
No LaTeX. Unicode math only. Each stem under 50 words.
"""


async def groq_json() -> str:
    model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    client = AsyncOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        max_tokens=3500,
    )
    return response.choices[0].message.content or ""


async def main() -> None:
    if not settings.GROQ_API_KEY:
        print("GROQ_API_KEY missing in backend/.env")
        return
    print("model", os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"))
    raw = await groq_json()
    print("raw_len", len(raw))
    config = GenerationConfig(
        document_id=await ensure_cbse_curriculum_document(),
        locked_chapter="trigonometry",
        title="Groq Demo - 5 Trigonometry Questions",
        total_questions=5,
        question_types=["MCQ", "ShortAnswer", "LongAnswer"],
        topic_focus="Trigonometry",
        subject="Mathematics",
        class_level="10",
    )
    task = {
        "type": QuestionType.LONG_ANSWER,
        "difficulty": "medium",
        "bloom_level": "Apply",
        "count": 5,
    }
    gen = QuestionGenerator()
    parsed = gen._parse_llm_output(raw, task, config, [])
    if len(parsed) < 5:
        print("parsed only", len(parsed), "items")
    parsed = parsed[:5]

    async with AsyncSessionLocal() as db:
        doc_id = config.document_id
        count_r = await db.execute(
            select(func.count(Assessment.id)).where(
                Assessment.user_id == DEMO_USER_ID,
                Assessment.document_id == doc_id,
            )
        )
        gen_num = (count_r.scalar() or 0) + 1
        a = Assessment(
            user_id=DEMO_USER_ID,
            document_id=doc_id,
            title=config.title,
            config=config.model_dump(mode="json"),
            question_ids=[],
            generation_num=gen_num,
            status="ready",
            total_marks=0.0,
            generation_log=[{"step": 1, "llm_mode": "groq_minimal", "llm_response": raw[:5000]}],
        )
        db.add(a)
        await db.flush()
        aid = a.id
        total = 0.0
        qids = []
        for i, qd in enumerate(parsed, 1):
            qd["slot_number"] = i
            qd["order_index"] = i - 1
            if not qd.get("content"):
                qd["content"] = qd.get("question", "")
            q = Question(
                document_id=doc_id,
                assessment_id=aid,
                content=qd["content"],
                question_type=qd.get("question_type"),
                difficulty=qd.get("difficulty", "medium"),
                bloom_level=qd.get("bloom_level"),
                options=qd.get("options"),
                correct_answer=qd.get("correct_answer", ""),
                explanation=qd.get("explanation", ""),
                marks=qd.get("marks", 2.0),
                quality_score=qd.get("quality_score", 0.8),
            )
            db.add(q)
            await db.flush()
            qids.append(q.id)
            total += float(q.marks or 2)
        a.question_ids = qids
        a.total_marks = total
        await db.commit()
        print("status ready questions", len(qids), "marks", total)
        print("DASHBOARD_URL=http://localhost:3000/assessments/" + aid)
        for j, qd in enumerate(parsed, 1):
            print(f"Q{j}:", (qd.get("content") or "")[:100])


if __name__ == "__main__":
    asyncio.run(main())
