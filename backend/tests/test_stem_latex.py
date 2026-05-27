from app.export.pdf_latex.stem_latex import stem_to_latex_body


def test_recurrence_uses_display_and_thin_space():
    stem = "Prove p_{n} = s·p_{n-1} − t·p_{n-2} for x² − sx + t = 0."
    out = stem_to_latex_body(stem)
    assert r"\[" in out
    assert r"\," in out or "p_{n-1}" in out
    assert "p_{n}" in out


def test_subparts_rendered():
    stem = "For k real. (i) Find D. (ii) Hence find roots."
    out = stem_to_latex_body(stem)
    assert r"\textbf{(i)}" in out
    assert r"\textbf{(ii)}" in out
