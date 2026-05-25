"""Paper 13 — LaTeX → Unicode display math."""
from app.generation.question_text import ensure_plain_text, has_raw_latex, to_reportlab_markup


def test_mathrm_and_mathsf_to_unicode():
    raw = r"verify with \mathrm{A}, and \mathsf{G H}^{\wedge}2\\={\mathsf{G J}}\times{\mathsf{G K}}"
    out = ensure_plain_text(raw)
    assert not has_raw_latex(out)
    assert "mathrm" not in out
    assert "mathsf" not in out
    assert "GH²" in out
    assert "×" in out
    assert "GJ" in out


def test_pa2_gh2_become_superscript():
    assert "PA²" in ensure_plain_text("verify PA2 = PQ x PR")
    assert "GH²" in ensure_plain_text("verify GH2 = GJ x GK")
    assert "21 cm" in ensure_plain_text("radii 29 cm and 21 cm")


def test_two_touching_and_pa_spacing():
    out = ensure_plain_text("from Question 2touching; tangent PA =15 cm")
    assert "2 touching" in out
    assert "2touching" not in out
    assert "PA = 15" in out


def test_markup_no_backslash_commands():
    m = to_reportlab_markup(r"\mathsf{PQ}=\mathsf{9} cm")
    assert "\\mathsf" not in m
    assert "PQ" in m
