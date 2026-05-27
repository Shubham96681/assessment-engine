"""
LaTeX + Jinja2 → PDF export (xelatex / pdflatex).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.export.paper_header import header_row_for_config, sanitize_paper_title
from app.export.pdf_content_prep import prepare_questions_for_pdf
from app.export.pdf_latex.compiler import LatexCompileError, compile_tex_to_pdf, latex_engine_available
from app.export.pdf_latex.stem_latex import stem_to_latex_body
from app.generation.chapter_concept_classifier import resolve_locked_chapter

logger = logging.getLogger(__name__)

TEMPLATE_ROOT = Path(__file__).resolve().parents[3] / "templates"


def _latex_escape_filter(value: Any) -> str:
    if value is None:
        return ""
    s = str(value)
    for ch, repl in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ):
        s = s.replace(ch, repl)
    return s


def _jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["latex_escape"] = _latex_escape_filter
    return env


class LatexPDFExporter:
    """Build exam PDFs from Jinja2 LaTeX templates + external LaTeX engine."""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.exports_dir = os.path.join(storage_path, "exports")
        os.makedirs(self.exports_dir, exist_ok=True)

    def _prepare_questions(
        self, questions: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        locked, _, _ = resolve_locked_chapter(
            filename="",
            topic_focus=(config.get("topic_focus") or ""),
            context=(questions[0].get("content") or questions[0].get("question") or ""),
        )
        return prepare_questions_for_pdf(questions, chapter=locked or "generic")

    def _build_rows(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for i, q in enumerate(questions):
            num = int(q.get("slot_number") or q.get("order_index", i) + 1)
            content = (q.get("content") or q.get("question") or "").strip()
            answer = (q.get("correct_answer") or "").strip()
            expl = (q.get("explanation") or "").strip()
            rows.append(
                {
                    "number": num,
                    "marks": float(q.get("marks") or 1),
                    "latex_body": stem_to_latex_body(content),
                    "answer_latex": stem_to_latex_body(answer),
                    "explanation_latex": stem_to_latex_body(expl) if expl else "",
                }
            )
        return rows

    def _header_context(
        self, config: Dict[str, Any], questions: List[Dict[str, Any]], teacher_name: str, institution: str
    ) -> Dict[str, Any]:
        total_marks = sum(float(q.get("marks") or 1) for q in questions)
        title = sanitize_paper_title(
            config.get("title", "Assessment Paper"),
            subject=(config.get("subject") or "").strip() or "Mathematics",
            topic_focus=(config.get("topic_focus") or "").strip(),
        )
        header = header_row_for_config(config, total_marks, len(questions))
        use_xelatex = (settings.PDF_LATEX_ENGINE or "xelatex").startswith("xelatex")
        return {
            "title": title,
            "subject": (config.get("subject") or "Mathematics").strip(),
            "class_level": (config.get("class_level") or "10").strip(),
            "date_str": datetime.now().strftime("%d %B %Y"),
            "duration": header[1][0].replace("Time: ", ""),
            "total_marks": total_marks,
            "question_count": len(questions),
            "examiner": teacher_name,
            "institution": institution,
            "use_xelatex": use_xelatex,
        }

    def export_assessment(
        self,
        questions: List[Dict[str, Any]],
        config: Dict[str, Any],
        assessment_id: str,
        teacher_name: str = "Teacher",
        institution: str = "Institution",
        include_answer_key: bool = True,
    ) -> Dict[str, Optional[str]]:
        if not questions:
            raise ValueError("Cannot export PDF: no questions provided")
        if not latex_engine_available():
            raise LatexCompileError(
                f"LaTeX engine '{settings.PDF_LATEX_ENGINE}' not on PATH"
            )

        prepared = self._prepare_questions(questions, config)
        rows = self._build_rows(prepared)
        ctx = self._header_context(config, prepared, teacher_name, institution)
        env = _jinja_env()

        q_path = os.path.join(self.exports_dir, f"assessment_{assessment_id}.pdf")
        tex_path = os.path.join(self.exports_dir, f"assessment_{assessment_id}.tex")
        tex_q = env.get_template("latex/assessment.tex.j2").render(
            questions=rows,
            **ctx,
        )
        Path(tex_path).write_text(tex_q, encoding="utf-8")
        compile_tex_to_pdf(tex_q, Path(q_path))

        ak_url: Optional[str] = None
        if include_answer_key:
            ak_path = os.path.join(self.exports_dir, f"answerkey_{assessment_id}.pdf")
            ak_tex_path = os.path.join(
                self.exports_dir, f"answerkey_{assessment_id}.tex"
            )
            tex_ak = env.get_template("latex/answer_key.tex.j2").render(
                questions=rows,
                **ctx,
            )
            Path(ak_tex_path).write_text(tex_ak, encoding="utf-8")
            compile_tex_to_pdf(tex_ak, Path(ak_path))
            ak_url = f"/uploads/exports/answerkey_{assessment_id}.pdf"

        return {
            "pdf_url": f"/uploads/exports/assessment_{assessment_id}.pdf",
            "answer_key_url": ak_url,
        }
