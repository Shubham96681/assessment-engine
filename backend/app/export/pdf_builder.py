"""
PDF Export Engine — Professional assessment PDF generation using ReportLab
"""
import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage, KeepTogether, Flowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape

from app.core.config import settings
from app.export.pdf_fonts import pdf_body_font

logger = logging.getLogger(__name__)

# Color palette
PRIMARY = colors.HexColor("#4f46e5")
SECONDARY = colors.HexColor("#7c3aed")
ACCENT = colors.HexColor("#ec4899")
DARK = colors.HexColor("#0f172a")
LIGHT_BG = colors.HexColor("#f8fafc")
BORDER = colors.HexColor("#e2e8f0")
TEXT = colors.HexColor("#1e293b")
MUTED = colors.HexColor("#64748b")
SUCCESS = colors.HexColor("#10b981")
WARNING = colors.HexColor("#f59e0b")


class _FigCaptionFlowable(Flowable):
    """Draw Fig.N as one string — avoids Paragraph kerning/extract as 'F i g.1'."""

    def __init__(self, fig_num: int, width: float, font_size: float = 9):
        super().__init__()
        self.fig_num = fig_num
        self.width = width
        self.font_size = font_size
        self.height = font_size + 4

    def draw(self) -> None:
        label = f"Fig.{self.fig_num}"
        self.canv.setFont("Helvetica-Bold", self.font_size)
        self.canv.setFillColor(TEXT)
        tw = self.canv.stringWidth(label, "Helvetica-Bold", self.font_size)
        self.canv.drawString((self.width - tw) / 2.0, 2, label)


class PDFExporter:
    """A4 export with 20mm side margins — all tables use _page_content_width()."""

    SIDE_MARGIN_MM = 20
    FIGURE_COL_MM = 58  # figure column width (right-aligned below stem)
    FIGURE_PANEL_MAX_HEIGHT_MM = 40  # compact — keeps Q1+Q2 on page 1 with text

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.exports_dir = os.path.join(storage_path, "exports")
        os.makedirs(self.exports_dir, exist_ok=True)

    @classmethod
    def _page_content_width(cls) -> float:
        return A4[0] - 2 * cls.SIDE_MARGIN_MM * mm

    def _resolve_figure_path(self, fig_url: Optional[str]) -> Optional[str]:
        """Map /uploads/figures/... URL to filesystem path."""
        if not fig_url:
            return None
        if fig_url.startswith("/uploads/"):
            path = fig_url.replace("/uploads", self.storage_path, 1)
            path = path.replace("/", os.sep)
        elif os.path.isabs(fig_url):
            path = fig_url
        else:
            path = os.path.join(self.storage_path, fig_url.lstrip("/"))
        return path if os.path.isfile(path) else None

    def _figure_flowable(self, img_path: str, *, max_width: Optional[float] = None) -> RLImage:
        """Embed figure at print-friendly size, preserving aspect ratio from PNG pixels."""
        from PIL import Image as PILImage

        cap_mm = min(
            settings.PDF_FIGURE_WIDTH_MM,
            (max_width / mm) if max_width else settings.PDF_FIGURE_WIDTH_MM,
        )
        max_w = cap_mm * mm
        max_h = min(settings.PDF_FIGURE_HEIGHT_MM, self.FIGURE_PANEL_MAX_HEIGHT_MM) * mm
        with PILImage.open(img_path) as pil:
            w_px, h_px = pil.size
        if w_px < 1 or h_px < 1:
            return RLImage(img_path, width=max_w, height=max_h)

        aspect = w_px / h_px
        draw_w, draw_h = max_w, max_w / aspect
        if draw_h > max_h:
            draw_h = max_h
            draw_w = draw_h * aspect
        return RLImage(img_path, width=draw_w, height=draw_h, kind="proportional")

    def _marks_paragraph(self, marks: float, styles: dict) -> Paragraph:
        """Plain escaped marks — never use XML 'marks' inside tags (ReportLab splits it)."""
        m_val = float(marks)
        m_disp = int(m_val) if m_val == int(m_val) else round(m_val, 1)
        word = "mark" if m_disp == 1 else "marks"
        return Paragraph(
            escape(f"[{m_disp} {word}]"),
            ParagraphStyle(
                "marks_plain",
                parent=styles["question"],
                fontSize=9,
                fontName="Helvetica-Bold",
                textColor=PRIMARY,
                alignment=TA_RIGHT,
            ),
        )

    def _question_header_table(
        self,
        num: int,
        q_text: str,
        marks_para: Paragraph,
        styles: dict,
        *,
        total_width: float,
    ) -> Table:
        """Q number | wrapped stem | marks — widths sum exactly to total_width."""
        num_w = 12 * mm
        marks_w = 22 * mm
        body_w = total_width - num_w - marks_w
        data = [[
            Paragraph(f"<b>Q{num}.</b>", styles["question_num"]),
            Paragraph(q_text, styles["question"]),
            marks_para,
        ]]
        tbl = Table(data, colWidths=[num_w, body_w, marks_w])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return tbl

    def _figure_panel_table(
        self,
        img_path: str,
        fig_num: int,
        col_width: float,
    ) -> Table:
        """Figure + caption boxed to fit the right column width."""
        img = self._figure_flowable(img_path, max_width=col_width - 8 * mm)
        # Plain "Fig.1" — no nbsp/bold markup (PDF extractors misread nbsp as "\\")
        cap = _FigCaptionFlowable(fig_num, col_width - 6 * mm)
        inner = Table([[img], [cap]], colWidths=[col_width - 6 * mm])
        inner.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ]))
        outer = Table([[inner]], colWidths=[col_width])
        outer.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return outer

    def export_assessment(
        self,
        questions: List[Dict[str, Any]],
        config: Dict[str, Any],
        assessment_id: str,
        teacher_name: str = "Teacher",
        institution: str = "Institution",
        include_answer_key: bool = True,
    ) -> Dict[str, str]:
        """Generate assessment PDF + answer key PDF. Returns URLs."""
        q_path = os.path.join(self.exports_dir, f"assessment_{assessment_id}.pdf")
        ak_path = os.path.join(self.exports_dir, f"answerkey_{assessment_id}.pdf")

        from app.export.pdf_content_prep import prepare_questions_for_pdf

        questions = prepare_questions_for_pdf(questions)
        self._build_question_paper(questions, config, q_path, teacher_name, institution)
        if include_answer_key:
            self._build_answer_key(questions, config, ak_path, teacher_name, institution)

        return {
            "pdf_url": f"/uploads/exports/assessment_{assessment_id}.pdf",
            "answer_key_url": f"/uploads/exports/answerkey_{assessment_id}.pdf" if include_answer_key else None,
        }

    def _get_styles(self):
        styles = getSampleStyleSheet()
        body = pdf_body_font()
        body_bold = f"{body}-Bold" if f"{body}-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
        body_italic = (
            f"{body}-Oblique"
            if f"{body}-Oblique" in pdfmetrics.getRegisteredFontNames()
            else "Helvetica-Oblique"
        )
        custom = {
            "title": ParagraphStyle("title", parent=styles["Normal"],
                fontSize=20, fontName="Helvetica-Bold",
                textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=4),
            "subtitle": ParagraphStyle("subtitle", parent=styles["Normal"],
                fontSize=11, fontName=body,
                textColor=MUTED, alignment=TA_CENTER, spaceAfter=2),
            "section_header": ParagraphStyle("section_header", parent=styles["Normal"],
                fontSize=12, fontName="Helvetica-Bold",
                textColor=colors.white, backColor=PRIMARY,
                leftIndent=6, rightIndent=6, spaceAfter=4, spaceBefore=10,
                borderPad=6),
            "question": ParagraphStyle("question", parent=styles["Normal"],
                fontSize=settings.PDF_FONT_QUESTION_PT, fontName=body,
                textColor=TEXT, spaceBefore=4, spaceAfter=2,
                leading=settings.PDF_FONT_QUESTION_PT + 6,
                alignment=TA_JUSTIFY, wordWrap="CJK"),
            "question_num": ParagraphStyle("question_num", parent=styles["Normal"],
                fontSize=settings.PDF_FONT_QUESTION_PT, fontName=body_bold,
                textColor=PRIMARY),
            "option": ParagraphStyle("option", parent=styles["Normal"],
                fontSize=10, fontName=body,
                textColor=TEXT, leftIndent=20, spaceAfter=1),
            "answer": ParagraphStyle("answer", parent=styles["Normal"],
                fontSize=10, fontName=body,
                textColor=SUCCESS, leftIndent=10),
            "explanation": ParagraphStyle("explanation", parent=styles["Normal"],
                fontSize=9, fontName=body_italic,
                textColor=MUTED, leftIndent=10, spaceAfter=6),
            "meta_tag": ParagraphStyle("meta_tag", parent=styles["Normal"],
                fontSize=8, fontName=body,
                textColor=MUTED),
            "body": ParagraphStyle("body", parent=styles["Normal"],
                fontSize=settings.PDF_FONT_BODY_PT, fontName=body,
                textColor=TEXT, leading=settings.PDF_FONT_BODY_PT + 5),
        }
        return custom

    def _build_question_paper(
        self, questions, config, out_path, teacher_name, institution
    ):
        doc = SimpleDocTemplate(
            out_path, pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm,
            topMargin=25*mm, bottomMargin=20*mm,
        )
        styles = self._get_styles()
        story = []

        # ─── Header ────────────────────────────────────────────────────────────
        total_marks = sum(q.get("marks", 1.0) for q in questions)
        title = config.get("title", "Assessment Paper")
        subject = (
            (config.get("subject") or "").strip()
            or "Mathematics"
        )
        class_level = (
            (config.get("class_level") or "").strip()
            or "10"
        )
        date_str = datetime.now().strftime("%d %B %Y")

        board_line = f"CBSE Board Pattern — Class {class_level} — {subject}"
        story.append(Paragraph(institution, styles["subtitle"]))
        if board_line:
            story.append(Paragraph(board_line, styles["subtitle"]))
        story.append(Paragraph(title, styles["title"]))

        header_data = [
            [f"Subject: {subject}", f"Class: {class_level}", f"Date: {date_str}"],
            [f"Time: 3 Hours", f"Total Marks: {int(total_marks)}", f"Examiner: {teacher_name}"],
        ]
        cw = self._page_content_width()
        third = cw / 3
        header_table = Table(header_data, colWidths=[third, third, third])
        header_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
            ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 5*mm))

        # Instructions box
        instructions = config.get("instructions") or (
            "1. All questions are compulsory.  "
            "2. Write your answers clearly.  "
            "3. Figure-based questions: text on the left, diagram on the right.  "
            "4. Write name and roll number on the answer sheet."
        )
        inst_data = [[Paragraph(f"<b>Instructions:</b> {instructions}", styles["body"])]]
        inst_table = Table(inst_data, colWidths=[cw])
        inst_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, PRIMARY),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ede9fe")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(inst_table)
        story.append(Spacer(1, 4 * mm))

        # ─── Questions in slot order (do not group-by-type — keeps figures with stems) ─
        ordered = sorted(
            questions,
            key=lambda x: (
                int(x.get("slot_number") or 0),
                x.get("order_index", 0),
            ),
        )
        if ordered and all(
            (q.get("question_type") == "FigureBased") for q in ordered
        ):
            marks_list = [float(q.get("marks", 1.0)) for q in ordered]
            section_marks = sum(marks_list)
            parts = [str(int(m) if m == int(m) else m) for m in marks_list]
            marks_note = " + ".join(parts) + f" = {int(section_marks) if section_marks == int(section_marks) else section_marks}"
            label_full = (
                f"Figure-Based Questions    [{marks_note} total]"
            )
            section_data = [[Paragraph(
                escape(label_full),
                ParagraphStyle(
                    "sh", fontSize=10, fontName="Helvetica-Bold", textColor=colors.white
                ),
            )]]
            st = Table(section_data, colWidths=[cw])
            st.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(st)
            story.append(Spacer(1, 3 * mm))

        for i, q in enumerate(ordered):
            story.extend(self._render_question(q, i + 1, styles, show_answer=False))

        doc.build(story, onFirstPage=self._page_header_footer,
                  onLaterPages=self._page_header_footer)
        logger.info(f"Assessment PDF saved: {out_path}")

    def _answer_line_flowables(
        self, qtype: str, difficulty: str | None, line_w: float
    ) -> list:
        written_types = (
            "ShortAnswer",
            "LongAnswer",
            "FillBlank",
            "MatchColumn",
            "CaseStudy",
            "FigureBased",
        )
        if qtype not in written_types:
            return []
        hard = (difficulty or "").lower() == "hard"
        if qtype == "FigureBased" and hard:
            lines = 2
        elif qtype in ("LongAnswer", "CaseStudy"):
            lines = 4
        else:
            lines = 2
        return [
            HRFlowable(
                width=line_w,
                thickness=0.5,
                color=BORDER,
                spaceAfter=4,
                spaceBefore=2,
            )
            for _ in range(lines)
        ]

    def _render_question(self, q, num, styles, show_answer=False):
        elements = []
        qtype = q.get("question_type", "")
        diff = q.get("difficulty", "")
        bloom = q.get("bloom_level", "")
        marks = q.get("marks", 1.0)

        diff_colors = {"easy": "#10b981", "medium": "#f59e0b", "hard": "#ef4444"}
        diff_color = diff_colors.get(diff, "#64748b")

        # Question row
        from app.generation.question_text import to_reportlab_markup

        q_text = to_reportlab_markup(q.get("content", ""))
        marks_para = self._marks_paragraph(marks, styles)

        fig_num = num
        img_path = self._resolve_figure_path(q.get("figure_url"))
        content_w = self._page_content_width()
        fig_row_embedded = False

        if qtype == "FigureBased" and img_path:
            fig_col_w = self.FIGURE_COL_MM * mm
            try:
                # Two-row table (stem, then figure right) — splitByRow=0 keeps both on one page
                q_table = self._question_header_table(
                    num, q_text, marks_para, styles, total_width=content_w
                )
                fig_table = self._figure_panel_table(img_path, fig_num, fig_col_w)
                fig_row = Table(
                    [["", fig_table]],
                    colWidths=[content_w - fig_col_w, fig_col_w],
                )
                fig_row.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                q_block = Table(
                    [[q_table], [fig_row]],
                    colWidths=[content_w],
                    splitByRow=0,
                )
                q_block.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                block: list = [q_block]
                block.extend(
                    self._answer_line_flowables(qtype, q.get("difficulty"), content_w)
                )
                elements.append(KeepTogether(block))
                fig_row_embedded = True
            except Exception as e:
                logger.warning(f"PDF figure embed failed: {e}")
                elements.append(
                    self._question_header_table(
                        num, q_text, marks_para, styles, total_width=content_w
                    )
                )
                elements.append(Paragraph("<i>[Figure unavailable]</i>", styles["body"]))
        else:
            elements.append(
                self._question_header_table(
                    num, q_text, marks_para, styles, total_width=content_w
                )
            )
            if qtype == "FigureBased" and not img_path:
                elements.append(Paragraph(
                    "<i>[Figure missing — regenerate assessment]</i>",
                    styles["body"],
                ))
            elements.extend(
                self._answer_line_flowables(qtype, q.get("difficulty"), content_w)
            )

        # MCQ Options
        if qtype == "MCQ" or qtype == "AssertionReason":
            options = q.get("options", [])
            if options:
                opt_rows = [[
                    Paragraph(f"<b>({o['label']})</b> {o['text']}", styles["option"])
                ] for o in options]
                pairs = [opt_rows[i:i+2] for i in range(0, len(opt_rows), 2)]
                for pair in pairs:
                    row_data = pair + [[Paragraph("")]] * (2 - len(pair))
                    row_flat = [item[0] for item in row_data]
                    opt_table = Table([row_flat], colWidths=[82.5*mm, 82.5*mm])
                    opt_table.setStyle(TableStyle([
                        ("LEFTPADDING", (0, 0), (-1, -1), 20),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ]))
                    elements.append(opt_table)

        if not show_answer and not fig_row_embedded:
            elements.extend(
                self._answer_line_flowables(qtype, q.get("difficulty"), content_w)
            )

        # Show answer (for answer key)
        if show_answer:
            ans = to_reportlab_markup(q.get("correct_answer", "") or "")
            exp = to_reportlab_markup(q.get("explanation", "") or "")
            if ans:
                elements.append(Paragraph(f"<b>Answer:</b> {ans}", styles["answer"]))
            if exp:
                elements.append(Paragraph(f"<i>Explanation:</i> {exp}", styles["explanation"]))

        elements.append(Spacer(1, 3*mm))
        return elements

    def _render_answer_key_entry(self, q: Dict[str, Any], num: int, styles) -> list:
        """Compact answer-key row — no figures, no student answer lines."""
        from app.generation.question_text import to_reportlab_markup

        elements: list = []
        stem = to_reportlab_markup(q.get("content", "") or "")
        marks = q.get("marks", 1.0)
        elements.append(
            Paragraph(
                f"<b>Q{num}.</b> [{int(marks) if marks == int(marks) else marks} marks]",
                styles["question_num"],
            )
        )
        if stem:
            elements.append(Paragraph(stem, styles["body"]))
        ans = to_reportlab_markup(q.get("correct_answer", "") or "")
        exp = to_reportlab_markup(q.get("explanation", "") or "")
        if ans:
            elements.append(Paragraph(f"<b>Answer:</b> {ans}", styles["answer"]))
        if exp and len(exp) < 400:
            elements.append(Paragraph(f"<i>Note:</i> {exp}", styles["explanation"]))
        elements.append(Spacer(1, 4 * mm))
        return elements

    def _build_answer_key(self, questions, config, out_path, teacher_name, institution):
        doc = SimpleDocTemplate(out_path, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=25*mm, bottomMargin=20*mm)
        styles = self._get_styles()
        story = []
        story.append(Paragraph(institution, styles["subtitle"]))
        story.append(Paragraph(f"ANSWER KEY — {config.get('title', 'Assessment')}", styles["title"]))
        story.append(Spacer(1, 5*mm))

        ordered = sorted(
            questions,
            key=lambda x: (
                int(x.get("slot_number") or 0),
                x.get("order_index", 0),
            ),
        )
        for i, q in enumerate(ordered, 1):
            story.extend(self._render_answer_key_entry(q, i, styles))

        doc.build(story, onFirstPage=self._page_header_footer,
                  onLaterPages=self._page_header_footer)
        logger.info(f"Answer key PDF saved: {out_path}")

    @staticmethod
    def _page_header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        date_s = datetime.now().strftime("%d %b %Y")
        footer = f"{date_s}  |  Assessment Engine — Powered by AI  |  Page {doc.page}"
        canvas.drawCentredString(A4[0] / 2, 12 * mm, footer)
        # Top line
        canvas.setStrokeColor(PRIMARY)
        canvas.setLineWidth(1.5)
        canvas.line(20*mm, A4[1] - 15*mm, A4[0] - 20*mm, A4[1] - 15*mm)
        canvas.restoreState()
