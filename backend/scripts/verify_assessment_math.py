"""Run SymPy/math validators on all questions in an assessment."""
from __future__ import annotations

import asyncio
import sys

import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.generation.math_stem_validator import evaluate_math_stem
from app.generation.trig_sympy_verifier import evaluate_trig_sympy
from app.models import Question


async def main(assessment_id: str) -> None:
    async with AsyncSessionLocal() as db:
        qs = (
            await db.execute(
                select(Question).where(Question.assessment_id == assessment_id)
            )
        ).scalars().all()
        for i, q in enumerate(qs, 1):
            d = {
                "content": q.content or "",
                "correct_answer": q.correct_answer or "",
            }
            m = evaluate_math_stem(d, locked_chapter="trigonometry")
            t = evaluate_trig_sympy(d, locked_chapter="trigonometry")
            ok = m["math_stem_ok"] and t["trig_sympy_ok"]
            print(f"Q{i} PASS={ok}")
            if not ok:
                print("  math:", m.get("math_stem_critical"))
                print("  trig:", t.get("trig_sympy_critical"))
            stem = (q.content or "")[:140].encode("ascii", "replace").decode()
            print("  stem:", stem)


if __name__ == "__main__":
    aid = sys.argv[1] if len(sys.argv) > 1 else "1dbb5380-6e8c-442a-a45c-a8bddbb71c74"
    asyncio.run(main(aid))
