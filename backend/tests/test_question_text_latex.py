"""PDF-safe text — LaTeX braces must not corrupt ReportLab."""
from app.generation.question_text import (
    normalize_paper_math_notation,
    sanitize_latex_for_reportlab,
    to_reportlab_markup,
)


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


def test_p_n_ascii_becomes_subscript_markup():
    raw = "Prove p_n = s·p_{n-1} − t·p_{n-2} and α^n + β^n."
    norm = normalize_paper_math_notation(raw)
    assert "p_{n}" in norm
    assert "αⁿ" in norm
    markup = to_reportlab_markup(raw)
    assert ">n</sub>" in markup
    assert "p_n" not in markup


def test_missing_underscore_p_indices_normalized():
    raw = "State p0 and p1. Also write pn-1 and p n-2."
    norm = normalize_paper_math_notation(raw)
    assert "p_{0}" in norm
    assert "p_{1}" in norm
    assert "p_{n-1}" in norm
    assert "p_{n-2}" in norm


def test_standard_super_sub_in_reportlab_markup():
    raw = "Define p_{n} = α² + β². Prove p_{n} = s·p_{n-1} − t·p_{n-2} and x^4."
    markup = to_reportlab_markup(raw)
    assert ">n</sub>" in markup
    assert ">n-1</sub>" in markup
    assert "α²" in markup
    assert "x⁴" in markup
    assert "p <sub" not in markup
    assert "^" not in markup
    assert "_{n}" not in markup
    assert "<sup>2</sup>" not in markup

    raw2 = "Define pₙ = αⁿ. Prove pₙ = s·pₙ₋₁."
    markup2 = to_reportlab_markup(raw2)
    assert ">n</sub>" in markup2
    assert "ₙ" not in markup2
