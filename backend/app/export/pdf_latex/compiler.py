"""
Compile .tex → .pdf via xelatex or pdflatex.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class LatexCompileError(RuntimeError):
    pass


def latex_engine_available(engine: str | None = None) -> bool:
    eng = (engine or settings.PDF_LATEX_ENGINE or "xelatex").strip()
    return shutil.which(eng) is not None


def compile_tex_to_pdf(
    tex_content: str,
    out_pdf: Path,
    *,
    engine: str | None = None,
    runs: int = 2,
) -> Path:
    """Write tex_content to a temp dir, compile, copy PDF to out_pdf."""
    eng = (engine or settings.PDF_LATEX_ENGINE or "xelatex").strip()
    if not shutil.which(eng):
        raise LatexCompileError(
            f"LaTeX engine '{eng}' not found on PATH. "
            "Install TeX Live / MiKTeX or set PDF_BACKEND=reportlab."
        )

    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="exam_latex_") as tmp:
        work = Path(tmp)
        tex_path = work / "paper.tex"
        tex_path.write_text(tex_content, encoding="utf-8")
        cmd = [
            eng,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory",
            str(work),
            str(tex_path.name),
        ]
        log_parts: list[str] = []
        for run in range(max(1, runs)):
            proc = subprocess.run(
                cmd,
                cwd=work,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=settings.PDF_LATEX_TIMEOUT_SECONDS,
            )
            log_parts.append(proc.stdout or "")
            log_parts.append(proc.stderr or "")
            if proc.returncode != 0 and run == runs - 1:
                tail = "\n".join(log_parts)[-4000:]
                raise LatexCompileError(
                    f"{eng} failed (exit {proc.returncode}). Log tail:\n{tail}"
                )

        built = work / "paper.pdf"
        if not built.is_file():
            raise LatexCompileError(f"{eng} did not produce paper.pdf")
        out_pdf.write_bytes(built.read_bytes())
    return out_pdf
