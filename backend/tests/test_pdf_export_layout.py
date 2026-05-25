"""PDF export — marks wording, LaTeX strip, table no-split."""
from xml.sax.saxutils import escape

from app.export.pdf_builder import PDFExporter
from app.export.pdf_content_prep import prepare_questions_for_pdf
from app.generation.question_text import (
    ensure_plain_text,
    has_raw_latex,
    normalize_stem_for_pdf,
    to_reportlab_markup,
)


def test_marks_paragraph_uses_marks_not_pt():
    exp = PDFExporter(storage_path=".")
    styles = exp._get_styles()
    para = exp._marks_paragraph(5.0, styles)
    text = para.text if hasattr(para, "text") else str(getattr(para, "text", ""))
    assert "pt" not in text.lower() or "marks" in text
    assert "marks" in text or "mark]" in text


def test_prepare_strips_mathsf():
    raw = r"Tangent \mathsf{P A}=15 cm and \mathbf{A},"
    qs = prepare_questions_for_pdf([{"content": raw}])
    assert not has_raw_latex(qs[0]["content"])
    assert "mathsf" not in qs[0]["content"]


def test_strip_dollar_sum():
    raw = r"Before \sum after \mathsf{G J}=9"
    out = ensure_plain_text(raw)
    assert not has_raw_latex(out)


def test_normalize_stem_glued_tokens():
    assert "2 touching" in normalize_stem_for_pdf("from Question 2touching")
    assert "= 15" in normalize_stem_for_pdf("PA=15cm")


def test_reportlab_markup_nbsp_on_measurement():
    out = to_reportlab_markup("PA=15cm from Question 2 touching")
    assert "\u00a0" in out
    assert "2touching" not in out
