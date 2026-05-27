"""
PDF export factory — ReportLab (default fallback) or LaTeX (Jinja2 .tex → PDF).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFExporterProtocol(Protocol):
    def export_assessment(
        self,
        questions: List[Dict[str, Any]],
        config: Dict[str, Any],
        assessment_id: str,
        teacher_name: str = "Teacher",
        institution: str = "Institution",
        include_answer_key: bool = True,
    ) -> Dict[str, Optional[str]]: ...


def get_pdf_exporter(storage_path: str) -> PDFExporterProtocol:
    backend = (settings.PDF_BACKEND or "reportlab").strip().lower()
    if backend == "latex":
        from app.export.pdf_latex.compiler import latex_engine_available
        from app.export.pdf_latex.exporter import LatexPDFExporter

        if latex_engine_available():
            return LatexPDFExporter(storage_path)
        logger.warning(
            "PDF_BACKEND=latex but %s not found — falling back to ReportLab",
            settings.PDF_LATEX_ENGINE,
        )
    from app.export.pdf_builder import PDFExporter

    return PDFExporter(storage_path)
