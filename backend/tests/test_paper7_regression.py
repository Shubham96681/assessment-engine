"""Paper 7 regressions — LaTeX, Fig.4 separate circles, Fig.5 label G."""
from app.generation.figure_spec_builder import enrich_figure_spec
from app.generation.figure_label_validator import (
    figure_matches_stem,
    labels_in_figure_spec,
    needs_figure_rebuild,
)
from app.generation.question_text import has_raw_latex, sanitize_latex_for_reportlab


def test_latex_mathsf_spaced_and_sum():
    raw = r"Before \sum after \mathsf{G J}=\mathsf{9} and \mathbf{A},"
    out = sanitize_latex_for_reportlab(raw)
    assert not has_raw_latex(out)
    assert r"\sum" not in out
    assert "GJ=9" in out.replace(" ", "") or "G J=9" not in out


def test_fusion_figure_uses_g_not_p():
    stem = (
        "In the configuration of Question 1, with PA = 15 cm from Question 2. "
        "(i) Find OP. (ii) Hence point G is 34 cm from O; tangent GH touches at H. "
        "Secant GJK meets the circle at J (nearer G) with GJ = 9 cm. Find GK."
    )
    stale = enrich_figure_spec(
        "From external point P tangent PA = 15 cm secant PQR.",
        {
            "elements": [
                {"shape": "point", "label": "P", "position": "outside"},
                {"shape": "point", "label": "A", "position": "on_circle"},
            ]
        },
    )
    assert needs_figure_rebuild(stem, stale)
    spec = enrich_figure_spec(stem, None)
    labels = labels_in_figure_spec(spec)
    assert "G" in labels
    assert "P" not in labels or "G" in labels
    ok, flags = figure_matches_stem(stem, spec)
    assert ok, flags


def test_q4_two_circle_layout():
    stem = (
        "Circles with centres G and H have radii 2 cm and 10 cm respectively. "
        "If GH = 17 cm, find the direct common external tangent EF."
    )
    spec = enrich_figure_spec(stem, None)
    assert spec.get("layout") == "two_circle_external_tangent"
