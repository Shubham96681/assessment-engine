"""Groq: 100% hard, LongAnswer-only paper → dashboard-ready assessment."""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AsyncOpenAI
from sqlalchemy import func, select

from app.core.cbse_curriculum_doc import ensure_cbse_curriculum_document
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.demo_user import DEMO_USER_ID
from app.generation.generator import QuestionGenerator
from app.generation.math_stem_validator import should_reject_math_stem
from app.generation.answer_format import ensure_answer_text
from app.generation.question_text import ensure_plain_text
from app.models import Assessment, Question
from app.schemas import GenerationConfig, QuestionType

N = int(os.environ.get("TOTAL_QUESTIONS", "5"))
CHAPTER = os.environ.get("LOCKED_CHAPTER", "trigonometry")

def _prompt_batch(count: int, id_start: int) -> str:
    id_end = id_start + count - 1
    return f"""CBSE Class 10 FULL HARD {CHAPTER} — LongAnswer only.
Write exactly {count} questions, ids {id_start} to {id_end}.
Each: (i)(ii)(iii); prove+Hence; quadrant traps; exact surds; 35-50 words/stem.
MANDATORY CORRECT FORMULAS:
- tan(A+B) = (tan A + tan B) / (1 - tan A tan B) — NEVER use minus tan A tan B in numerator or 1+tan A tan B in denominator.
- No calculus: no integrals, no dx, no ∫.
- No triangles with angle 3π/2 or 270°.
Answers: Given → Step 1 → Step 2 → Hence with real numeric work. marks 5-6.
Each answer sub-part on its OWN LINE: (i) ... newline (ii) ... newline (iii) ...
Use (numerator)/(denominator) for fractions. NO Python lists/dicts in correct_answer.
Output: plain Unicode math (θ, π, √, ≤, ∠, Δ) — server reformats via SymPy. NO LaTeX (no \\mathsf, \\sum). NO HTML tags (<hr/>, <br/>). NO raw codes like 0394.
Return valid JSON only — escape newlines in strings as \\n (no raw line breaks inside JSON strings).
JSON array only: id, type "LongAnswer", question, marks, correct_answer.
"""


async def groq_json_batch(count: int, id_start: int) -> str:
    model = os.environ.get("GROQ_MODEL", settings.GROQ_MODEL or "llama-3.1-8b-instant")
    client = AsyncOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _prompt_batch(count, id_start)}],
        temperature=0.75,
        max_tokens=2800,
    )
    return response.choices[0].message.content or ""


async def groq_json_all(n: int) -> str:
    """Split into batches of 2 to stay under Groq TPM (6000 on 8b-instant)."""
    parts: list[str] = []
    start = 1
    while start <= n:
        batch = min(2, n - start + 1)
        parts.append(await groq_json_batch(batch, start))
        start += batch
        if start <= n:
            await asyncio.sleep(3)
    return "\n---\n".join(parts)


def _extract_items(raw: str) -> list:
    items: list = []
    start = raw.find("[")
    end = raw.rfind("]")
    if start >= 0 and end > start:
        try:
            block = json.loads(raw[start : end + 1])
            if isinstance(block, list):
                items.extend(x for x in block if isinstance(x, dict))
        except json.JSONDecodeError:
            pass
    return items


async def main() -> None:
    if not settings.GROQ_API_KEY:
        print("GROQ_API_KEY missing in backend/.env")
        return
    print("model", os.environ.get("GROQ_MODEL", settings.GROQ_MODEL), "n", N, "chapter", CHAPTER)
    gen = QuestionGenerator()
    doc_id = await ensure_cbse_curriculum_document()
    task = {
        "type": QuestionType.LONG_ANSWER,
        "difficulty": "hard",
        "bloom_level": "Analyze",
        "count": N,
    }
    config = GenerationConfig(
        document_id=doc_id,
        locked_chapter=CHAPTER,
        title=f"Full Hard LongAnswer — {CHAPTER.title()} ({N}Q)",
        total_questions=N,
        question_types=[QuestionType.LONG_ANSWER],
        difficulty_distribution={"easy": 0, "medium": 0, "hard": 100},
        bloom_levels=["Analyze", "Evaluate"],
        topic_focus=CHAPTER.title(),
        subject="Mathematics",
        class_level="10",
        instructions="Exam level: full_hard — 100% hard LongAnswer only",
        use_chapter_pdf=False,
    )
    unique: list = []
    seen: set = set()
    start_id = 1
    attempts = 0
    raw_parts: list[str] = []
    while len(unique) < N and attempts < 14:
        need = min(2, N - len(unique))
        part = await groq_json_batch(need, start_id)
        raw_parts.append(part)
        items = _extract_items(part)
        batch_parsed = (
            gen._parse_llm_output(json.dumps(items), task, config, [])
            if items
            else gen._parse_llm_output(part, task, config, [])
        )
        for q in batch_parsed:
            for key in ("content", "question", "explanation"):
                if isinstance(q.get(key), str):
                    q[key] = ensure_plain_text(q[key])
            if isinstance(q.get("correct_answer"), str):
                q["correct_answer"] = ensure_answer_text(q["correct_answer"])
            if q.get("content"):
                q["question"] = q["content"]
            stem = (q.get("content") or q.get("question") or "").strip()
            if not stem or stem in seen or should_reject_math_stem(
                q, locked_chapter=CHAPTER
            ):
                continue
            seen.add(stem)
            unique.append(q)
        start_id = len(unique) + 1
        attempts += 1
        if len(unique) < N:
            await asyncio.sleep(4)
    raw = "\n---\n".join(raw_parts)
    parsed = unique[:N]
    if len(parsed) < N:
        print(f"warning: parsed {len(parsed)}/{N} questions")
    aid = ""
    qids: list = []
    total = 0.0
    async with AsyncSessionLocal() as db:
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
            generation_log=[
                {
                    "step": 1,
                    "llm_mode": "groq_full_hard_long",
                    "difficulty": "hard",
                    "llm_response": raw[:8000],
                }
            ],
        )
        db.add(a)
        await db.flush()
        aid = a.id
        total = 0.0
        qids = []
        for i, qd in enumerate(parsed, 1):
            qd["slot_number"] = i
            qd["order_index"] = i - 1
            qd["question_type"] = "LongAnswer"
            qd["difficulty"] = "hard"
            if not qd.get("content"):
                qd["content"] = qd.get("question", "")
            marks = float(qd.get("marks") or 6.0)
            q = Question(
                document_id=doc_id,
                assessment_id=aid,
                content=qd["content"],
                question_type="LongAnswer",
                difficulty="hard",
                bloom_level=qd.get("bloom_level") or "Analyze",
                correct_answer=qd.get("correct_answer", ""),
                explanation=qd.get("explanation", ""),
                marks=marks,
                quality_score=float(qd.get("quality_score") or 0.85),
            )
            db.add(q)
            await db.flush()
            qids.append(q.id)
            total += marks
        a.question_ids = qids
        a.total_marks = total
        await db.commit()

    from app.export.store_pdfs import store_assessment_pdf_exports

    async with AsyncSessionLocal() as db:
        urls = await store_assessment_pdf_exports(db, aid)
        print("pdf", urls.get("pdf_url"))
        print("answer_key", urls.get("answer_key_url"))

    print("status ready questions", len(qids), "marks", total)
    print("DASHBOARD_URL=http://localhost:3000/assessments/" + aid)


if __name__ == "__main__":
    asyncio.run(main())
