"""PDF LaTeX math — fractions, trig, prose spacing."""
from app.export.pdf_math_latex import (
    exam_plain_to_latex,
    normalize_prose_glued,
    segment_exam_math,
)
from app.export.pdf_math_flowable import build_exam_text_flowable
from app.export.pdf_builder import PDFExporter


def test_paren_fraction_to_frac():
    out = exam_plain_to_latex("(tan A + tan B)/(1 - tan A tan B)")
    assert r"\frac" in out
    assert r"\tan" in out


def test_tan_identity_line():
    out = exam_plain_to_latex("tan(A + B) = (tan A + tan B)/(1 - tan A tan B)")
    assert r"\tan" in out
    assert r"\frac" in out


def test_prose_glued_fix():
    out = normalize_prose_glued("IftanA = 2andtanB = 3, findthevaluesofcos(A + B)")
    assert "If " in out or out.startswith("If")
    assert " and " in out
    assert "values of" in out


def test_segment_keeps_prose_spaces():
    stem = (
        "If tan θ = 1/3 and θ lies in quadrant II, find the value of sin θ cos θ. "
        "Also, prove that tan(A + B) = (tan A + tan B)/(1 - tan A tan B)."
    )
    segs = segment_exam_math(stem)
    text = "".join(s.value for s in segs if s.kind == "text")
    assert "find the value" in text or "find the" in text
    assert "Iftan" not in text
    math = [s for s in segs if s.kind == "math"]
    assert math
    assert any(r"\frac" in m.latex for m in math)


def test_build_exam_flowable():
    exp = PDFExporter(storage_path=".")
    styles = exp._get_styles()
    flow = build_exam_text_flowable(
        "Prove tan(5θ) = (tan 2θ + tan 3θ)/(1 - tan 2θ tan 3θ).",
        styles["question"],
        400,
    )
    assert flow is not None
