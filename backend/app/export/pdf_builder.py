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
    HRFlowable, PageBreak, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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


class PDFExporter:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.exports_dir = os.path.join(storage_path, "exports")
        os.makedirs(self.exports_dir, exist_ok=True)

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

        self._build_question_paper(questions, config, q_path, teacher_name, institution)
        if include_answer_key:
            self._build_answer_key(questions, config, ak_path, teacher_name, institution)

        return {
            "pdf_url": f"/uploads/exports/assessment_{assessment_id}.pdf",
            "answer_key_url": f"/uploads/exports/answerkey_{assessment_id}.pdf" if include_answer_key else None,
        }

    def _get_styles(self):
        styles = getSampleStyleSheet()
        custom = {
            "title": ParagraphStyle("title", parent=styles["Normal"],
                fontSize=20, fontName="Helvetica-Bold",
                textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=4),
            "subtitle": ParagraphStyle("subtitle", parent=styles["Normal"],
                fontSize=11, fontName="Helvetica",
                textColor=MUTED, alignment=TA_CENTER, spaceAfter=2),
            "section_header": ParagraphStyle("section_header", parent=styles["Normal"],
                fontSize=12, fontName="Helvetica-Bold",
                textColor=colors.white, backColor=PRIMARY,
                leftIndent=6, rightIndent=6, spaceAfter=4, spaceBefore=10,
                borderPad=6),
            "question": ParagraphStyle("question", parent=styles["Normal"],
                fontSize=10.5, fontName="Helvetica",
                textColor=TEXT, spaceBefore=4, spaceAfter=2,
                leading=16),
            "question_num": ParagraphStyle("question_num", parent=styles["Normal"],
                fontSize=10.5, fontName="Helvetica-Bold",
                textColor=PRIMARY),
            "option": ParagraphStyle("option", parent=styles["Normal"],
                fontSize=10, fontName="Helvetica",
                textColor=TEXT, leftIndent=20, spaceAfter=1),
            "answer": ParagraphStyle("answer", parent=styles["Normal"],
                fontSize=10, fontName="Helvetica",
                textColor=SUCCESS, leftIndent=10),
            "explanation": ParagraphStyle("explanation", parent=styles["Normal"],
                fontSize=9, fontName="Helvetica-Oblique",
                textColor=MUTED, leftIndent=10, spaceAfter=6),
            "meta_tag": ParagraphStyle("meta_tag", parent=styles["Normal"],
                fontSize=8, fontName="Helvetica",
                textColor=MUTED),
            "body": ParagraphStyle("body", parent=styles["Normal"],
                fontSize=10, fontName="Helvetica",
                textColor=TEXT, leading=15),
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
        subject = config.get("subject", "")
        class_level = config.get("class_level", "")
        date_str = datetime.now().strftime("%d %B %Y")

        board_line = ""
        if class_level or subject:
            board_line = f"CBSE Board Pattern — Class {class_level or '—'} — {subject or 'General'}"
        story.append(Paragraph(institution, styles["subtitle"]))
        if board_line:
            story.append(Paragraph(board_line, styles["subtitle"]))
        story.append(Paragraph(title, styles["title"]))

        header_data = [
            [f"Subject: {subject}", f"Class: {class_level}", f"Date: {date_str}"],
            [f"Time: 3 Hours", f"Total Marks: {int(total_marks)}", f"Examiner: {teacher_name}"],
        ]
        header_table = Table(header_data, colWidths=[55*mm, 55*mm, 55*mm])
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
            "3. Figures are to the right unless stated.  "
            "4. Write name and roll number on the answer sheet."
        )
        inst_data = [[Paragraph(f"<b>Instructions:</b> {instructions}", styles["body"])]]
        inst_table = Table(inst_data, colWidths=[165*mm])
        inst_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, PRIMARY),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ede9fe")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(inst_table)
        story.append(Spacer(1, 6*mm))

        # ─── Questions by type (preserve generation order) ─────────────────────
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for q in sorted(questions, key=lambda x: x.get("order_index", 0)):
            t = q.get("question_type", "General")
            grouped.setdefault(t, []).append(q)

        type_labels = {
            "MCQ": "Section A — Multiple Choice Questions",
            "TrueFalse": "Section B — True / False",
            "FillBlank": "Section C — Fill in the Blanks",
            "ShortAnswer": "Section D — Short Answer Questions",
            "AssertionReason": "Section E — Assertion & Reason",
            "MatchColumn": "Section F — Match the Column",
            "FigureBased": "Section G — Figure-Based Questions",
            "LongAnswer": "Section H — Long Answer Questions",
            "CaseStudy": "Section I — Case Study",
        }

        global_qnum = 1
        for qtype, qs in grouped.items():
            per_q_marks = qs[0].get("marks", 1.0)
            section_marks = sum(q.get("marks", 1.0) for q in qs)
            label = type_labels.get(qtype, f"Section — {qtype}")
            label_full = f"{label}    [{len(qs)} × {per_q_marks} = {section_marks} marks]"

            # Section header banner
            section_data = [[Paragraph(label_full, ParagraphStyle(
                "sh", fontSize=10, fontName="Helvetica-Bold",
                textColor=colors.white))]]
            st = Table(section_data, colWidths=[165*mm])
            st.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(st)
            story.append(Spacer(1, 3*mm))

            for q in qs:
                story.extend(self._render_question(q, global_qnum, styles, show_answer=False))
                global_qnum += 1

            story.append(Spacer(1, 5*mm))

        doc.build(story, onFirstPage=self._page_header_footer,
                  onLaterPages=self._page_header_footer)
        logger.info(f"Assessment PDF saved: {out_path}")

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
        meta = f'<font color="{diff_color}"><b>[{diff.upper()}]</b></font>  <font color="#64748b">{bloom}</font>'
        mark_text = f'<font color="#4f46e5"><b>[{marks} mark{"s" if marks != 1 else ""}]</b></font>'

        q_data = [[
            Paragraph(f"<b>Q{num}.</b>", styles["question_num"]),
            Paragraph(q_text, styles["question"]),
            Paragraph(mark_text, ParagraphStyle("marks", fontSize=9,
                fontName="Helvetica-Bold", textColor=PRIMARY, alignment=TA_RIGHT)),
        ]]
        fig_num = q.get("figure_number") or num
        img_path = self._resolve_figure_path(q.get("figure_url"))

        if qtype == "FigureBased" and img_path:
            try:
                img = RLImage(img_path, width=62*mm, height=48*mm)
                cap = Paragraph(
                    f"<b>Fig. {fig_num}</b>",
                    ParagraphStyle("figcap", fontSize=9, fontName="Helvetica-Bold",
                                   textColor=TEXT, alignment=TA_CENTER),
                )
                fig_col = [[img], [cap]]
                fig_table = Table(fig_col, colWidths=[64*mm])
                fig_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ]))
            except Exception as e:
                logger.warning(f"PDF figure embed failed: {e}")
                fig_table = Paragraph("<i>[Figure unavailable]</i>", styles["body"])

            q_table = Table(q_data, colWidths=[10*mm, 88*mm, 15*mm])
            q_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            row = Table([[q_table, fig_table]], colWidths=[115*mm, 68*mm])
            row.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
            elements.append(row)
        else:
            q_table = Table(q_data, colWidths=[10*mm, 140*mm, 15*mm])
            q_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            elements.append(q_table)
            if qtype == "FigureBased" and not img_path:
                elements.append(Paragraph(
                    "<i>[Figure missing — regenerate assessment]</i>",
                    styles["body"],
                ))

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

        # Answer lines for written-response types (incl. hard figure-based)
        written_types = ("ShortAnswer", "LongAnswer", "FillBlank", "MatchColumn", "CaseStudy", "FigureBased")
        if qtype in written_types and not show_answer:
            hard = (q.get("difficulty") or "").lower() == "hard"
            if qtype == "FigureBased" and hard:
                lines = 5
            elif qtype in ("LongAnswer", "CaseStudy"):
                lines = 4
            else:
                lines = 2
            for _ in range(lines):
                elements.append(HRFlowable(width="100%", thickness=0.5,
                                           color=BORDER, spaceAfter=5, spaceBefore=3))

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

    def _build_answer_key(self, questions, config, out_path, teacher_name, institution):
        doc = SimpleDocTemplate(out_path, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=25*mm, bottomMargin=20*mm)
        styles = self._get_styles()
        story = []
        story.append(Paragraph(institution, styles["subtitle"]))
        story.append(Paragraph(f"ANSWER KEY — {config.get('title', 'Assessment')}", styles["title"]))
        story.append(Spacer(1, 5*mm))

        for i, q in enumerate(questions, 1):
            story.extend(self._render_question(q, i, styles, show_answer=True))

        doc.build(story, onFirstPage=self._page_header_footer,
                  onLaterPages=self._page_header_footer)
        logger.info(f"Answer key PDF saved: {out_path}")

    @staticmethod
    def _page_header_footer(canvas, doc):
        canvas.saveState()
        # Footer
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(20*mm, 12*mm, "Assessment Engine — Powered by AI")
        canvas.drawRightString(A4[0] - 20*mm, 12*mm, f"Page {doc.page}")
        canvas.drawCentredString(A4[0] / 2, 12*mm,
                                 datetime.now().strftime("%d %b %Y"))
        # Top line
        canvas.setStrokeColor(PRIMARY)
        canvas.setLineWidth(1.5)
        canvas.line(20*mm, A4[1] - 15*mm, A4[0] - 20*mm, A4[1] - 15*mm)
        canvas.restoreState()
