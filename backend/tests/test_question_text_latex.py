"""PDF-safe text — LaTeX braces must not corrupt ReportLab."""
from app.generation.question_text import sanitize_latex_for_reportlab, to_reportlab_markup


def test_sin_inverse_braces_sanitized():
    raw = "angle θ = sin^{-1}(5/13) and \\sqrt{144}"
    out = sanitize_latex_for_reportlab(raw)
    assert "{" not in out
    assert "}" not in out
    assert "sin inverse" in out.lower() or "sin" in out


def test_reportlab_markup_no_raw_braces():
    raw = "Verify PQ^2 = PR \\times PT with sin^{-1}(7/25)"
    markup = to_reportlab_markup(raw)
    assert "{{" not in markup
    assert "^{" not in markup


def test_mathsf_stripped():
    raw = r"\mathsf{GJ}=6 cm and \mathbf{O},"
    out = sanitize_latex_for_reportlab(raw)
    assert "mathsf" not in out
    assert "mathbf" not in out
    assert "GJ" in out
