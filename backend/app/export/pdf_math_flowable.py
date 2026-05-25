"""
ReportLab flowables for exam stems with matplotlib-rendered LaTeX math.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any, List

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image as RLImage, Paragraph, Spacer, Table, TableStyle

from app.core.config import settings
from app.export.pdf_math_latex import (
    MAX_DISPLAY_LATEX,
    MathSegment,
    latex_to_png_bytes,
    segment_with_bold,
)
from app.generation.answer_format import ensure_answer_text, split_answer_subparts
from app.generation.question_text import ensure_plain_text, to_reportlab_markup

logger = logging.getLogger(__name__)


def _latex_is_renderable(latex: str) -> bool:
    """Skip Python-list garbage and oversized blobs."""
    if not latex or len(latex) > MAX_DISPLAY_LATEX:
        return False
    if re.search(r"^\s*\[|'\s*,\s*'|```|Step\s*1\s*:", latex, re.I):
        return False
    if latex.count("$") > 2:
        return False
    return True


def _latex_image_flowable(
    latex: str,
    max_width: float,
    *,
    display: bool = False,
    fontsize: float = 11.0,
) -> RLImage:
    png = latex_to_png_bytes(latex, fontsize=fontsize, display=display)
    img = RLImage(io.BytesIO(png))
    iw, ih = float(img.imageWidth), float(img.imageHeight)
    if iw <= 0 or ih <= 0:
        img.drawWidth = max_width
        img.drawHeight = 12
        return img
    scale = min(1.0, max_width / iw)
    img.drawWidth = iw * scale
    img.drawHeight = ih * scale
    img.hAlign = "CENTER" if display else "LEFT"
    return img


def build_exam_text_flowable(
    raw_text: str,
    style: ParagraphStyle,
    max_width: float,
    *,
    use_latex: bool | None = None,
    is_answer: bool = False,
) -> Any:
    """
    Single flowable: Paragraph (plain) or stacked Table (prose + LaTeX images).
    """
    plain = (
        ensure_answer_text(raw_text or "")
        if is_answer
        else ensure_plain_text(raw_text or "")
    )
    if not plain:
        return Paragraph("", style)

    enabled = settings.PDF_MATH_LATEX if use_latex is None else use_latex
    if not enabled:
        return Paragraph(to_reportlab_markup(plain), style)

    parts = segment_with_bold(plain)
    has_math = any(s.kind == "math" for _b, segs in parts for s in segs)
    if not has_math:
        return Paragraph(to_reportlab_markup(plain), style)

    rows: List[List[Any]] = []
    for bold, segments in parts:
        for seg in segments:
            if seg.kind == "text":
                val = seg.value.strip()
                if not val:
                    continue
                pstyle = style
                if bold:
                    pstyle = ParagraphStyle(
                        name=f"{style.name}_bold",
                        parent=style,
                        fontName="Helvetica-Bold",
                    )
                rows.append([Paragraph(to_reportlab_markup(val), pstyle)])
            elif isinstance(seg, MathSegment):
                if not _latex_is_renderable(seg.latex):
                    rows.append(
                        [Paragraph(to_reportlab_markup(seg.latex), style)]
                    )
                    continue
                try:
                    img = _latex_image_flowable(
                        seg.latex,
                        max_width,
                        display=seg.display,
                        fontsize=float(settings.PDF_FONT_QUESTION_PT),
                    )
                    rows.append([img])
                except Exception as exc:
                    logger.warning("PDF math image fallback: %s", exc)
                    rows.append(
                        [
                            Paragraph(
                                to_reportlab_markup(seg.latex.replace("\\", "")),
                                style,
                            )
                        ]
                    )

    if not rows:
        return Paragraph(to_reportlab_markup(plain), style)
    if len(rows) == 1:
        return rows[0][0]

    tbl = Table(rows, colWidths=[max_width])
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    for i, row in enumerate(rows):
        if isinstance(row[0], RLImage) and getattr(row[0], "hAlign", "") == "CENTER":
            cmds.append(("ALIGN", (0, i), (0, i), "CENTER"))
        else:
            cmds.append(("ALIGN", (0, i), (0, i), "LEFT"))
    tbl.setStyle(TableStyle(cmds))
    return tbl


def build_answer_block_flowables(
    prefix: str,
    raw_text: str,
    style: ParagraphStyle,
    max_width: float,
) -> List[Any]:
    """Prefix line + content flowable (Answer / Explanation)."""
    if not raw_text:
        return []
    out: List[Any] = []
    if prefix:
        out.append(Paragraph(f"<b>{prefix}</b>", style))
        out.append(Spacer(1, 2))

    subparts = split_answer_subparts(raw_text)
    if subparts:
        for label, body in subparts:
            if label:
                out.append(Paragraph(f"<b>{label}</b>", style))
                out.append(Spacer(1, 1))
            out.append(
                build_exam_text_flowable(body, style, max_width, is_answer=True)
            )
            out.append(Spacer(1, 5))
        return out

    out.append(build_exam_text_flowable(raw_text, style, max_width, is_answer=True))
    return out
