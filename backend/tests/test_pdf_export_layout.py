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


def test_angle_symbol_preserved():
    out = ensure_plain_text("In \u0394ABC, \u2220C = 90\u00b0 and \u2220A = \u03c0/2.")
    assert "\u2220" in out
    assert "\u0394" in out


def test_strip_hr_markup():
    out = ensure_plain_text("Prove sin 5\u03b8 = x for 0\u00b0 \u2264 \u03b8 \u2264 90\u00b0. <hr/>Hence, find sin \u03b8.")
    assert "hr/" not in out.lower()
    assert "Hence" in out
    assert "<" not in out


def test_strip_partial_hr_artifact():
    out = ensure_plain_text("90\u00b0.,hr/Hence, find sin \u03b8.")
    assert "hr/" not in out.lower()
    assert "Hence" in out


def test_angle_word_to_symbol():
    out = ensure_plain_text("In triangle ABC, angle A = \u03c0/2. If angle ATB = 60\u00b0, find angle AOB.")
    assert "\u2220A" in out
    assert "\u2220ATB" in out
    assert "\u2220AOB" in out
    assert "angle A =" not in out


def test_angle_between_phrase_unchanged():
    out = ensure_plain_text("Find the angle between the tangents when each tangent is 12 cm.")
    assert "angle between" in out


def test_normalize_stem_glued_tokens():
    assert "2 touching" in normalize_stem_for_pdf("from Question 2touching")
    assert "= 15" in normalize_stem_for_pdf("PA=15cm")


def test_reportlab_markup_nbsp_on_measurement():
    out = to_reportlab_markup("PA=15cm from Question 2 touching")
    assert "\u00a0" in out
    assert "2touching" not in out


def test_normalize_fro_gh_truncation():
    out = normalize_stem_for_pdf("fro GH = 21 cm tangent from O")
    assert "from GH" in out
    assert "fro GH" not in out


def test_markup_protects_gh_label():
    out = to_reportlab_markup("tangent GH from O")
    assert "GH" in out
    assert "fro" not in out.lower() or "from" in out.lower()
