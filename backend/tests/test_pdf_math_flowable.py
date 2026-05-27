from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Table

from app.export.pdf_math_flowable import build_exam_text_flowable


def test_question_stem_uses_flowing_paragraph_not_stacked_images():
    styles = getSampleStyleSheet()
    stem = (
        "Let α and β be the roots of the monic quadratic x² − sx + t = 0. "
        "Define p_{n} = α^{n} + β^{n} for positive integers n. "
        "(i) Prove that p_{n} = s·p_{n-1} − t·p_{n-2} for all n ≥ 2."
    )
    flow = build_exam_text_flowable(
        stem, styles["Normal"], 400.0, is_answer=False
    )
    assert isinstance(flow, Paragraph)
    assert "<sub" in flow.text
    assert "s·p" in flow.text or "·p" in flow.text
    assert not isinstance(flow, Table)


def test_spurious_x_multiplication_fixed():
    from app.generation.question_text import ensure_plain_text

    out = ensure_plain_text("Prove p_{n} = s x p_{n-1} − t x p_{n-2}.")
    assert "s x p" not in out
    assert "·p_" in out or "p_{n-1}" in out
