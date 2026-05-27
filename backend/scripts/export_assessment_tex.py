"""Write LaTeX source for an assessment (compile locally with xelatex/pdflatex)."""
from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.export.pdf_latex.exporter import LatexPDFExporter
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
        from app.api.assessments import _questions_for_export

        payload = _questions_for_export(a, qs, polish=True)
        cfg = dict(a.config or {})
        cfg["title"] = a.title or cfg.get("title") or "Assessment"
        exp = LatexPDFExporter(settings.LOCAL_STORAGE_PATH)
        prepared = exp._prepare_questions(payload, cfg)
        rows = exp._build_rows(prepared)
        ctx = exp._header_context(cfg, prepared, "Teacher", "Assessment Engine")
        env = exp._jinja_env() if hasattr(exp, "_jinja_env") else None
        from app.export.pdf_latex.exporter import _jinja_env

        tex = _jinja_env().get_template("latex/assessment.tex.j2").render(
            questions=rows, **ctx
        )
        out = os.path.join(
            settings.LOCAL_STORAGE_PATH,
            "exports",
            f"assessment_{assessment_id}.tex",
        )
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(tex)
        print(out)
        print("Compile: pdflatex", os.path.basename(out))


if __name__ == "__main__":
    aid = sys.argv[1] if len(sys.argv) > 1 else "c28fd25c-04b0-41f3-b829-ecf18cf8a3c4"
    asyncio.run(main(aid))
