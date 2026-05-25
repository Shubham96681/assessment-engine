"""Paper 4 review fixes — Q4 givens, LaTeX, tangent–secant, figures."""
from app.generation.common_tangent_values import (
    is_valid_external_tangent_geometry,
    repair_external_tangent_stem,
    stem_has_required_external_tangent_givens,
    stem_has_valid_external_tangent_givens,
    validate_external_tangent_triple,
)
from app.generation.figure_spec_builder import enrich_figure_spec
from app.generation.paper_repair import repair_paper_questions
from app.generation.paper_integrity import validate_paper_integrity
from app.generation.question_text import sanitize_latex_for_reportlab
from app.generation.tangent_secant_values import repair_tangent_secant_stem


def test_repair_q4_missing_external_tangent_givens():
    stem = "Find the length of a direct common external tangent touching both circles."
    new, ch = repair_external_tangent_stem(stem, seed=4)
    assert ch
    assert stem_has_required_external_tangent_givens(new)
    assert "radii" in new.lower()
    assert "cm" in new


def test_repair_paper_slot4_integrity():
    qs = [
        {
            "slot_number": 4,
            "order_index": 3,
            "content": "Find the length of a direct common external tangent touching both circles.",
            "question_type": "FigureBased",
        },
    ]
    fixed = repair_paper_questions(qs, chapter="circles", re_enrich_figures=True)
    r = validate_paper_integrity(fixed, chapter="circles", expected_count=1)
    assert "slot4_external_tangent_missing_givens" not in r["paper_integrity_flags"]
    spec = fixed[0].get("figure_spec") or {}
    assert spec.get("layout") == "two_circle_external_tangent"


def test_sanitize_mathsf_mathbf():
    raw = r"Tangent \mathsf{PA}=15 cm and secant with \mathbf{A}, point P "
    out = sanitize_latex_for_reportlab(raw)
    assert "mathsf" not in out
    assert "mathbf" not in out
    assert "PA=15" in out.replace(" ", "") or "PA = 15" in out


def test_sanitize_mathsf_spaced_label():
    raw = r"tangent \mathsf{P A}=15 cm, \mathbf{A},"
    out = sanitize_latex_for_reportlab(raw)
    assert "mathsf" not in out
    assert "mathbf" not in out
    assert "PA=15" in out.replace(" ", "")


def test_external_tangent_3_7_5_invalid():
    ok, reason = validate_external_tangent_triple(3, 7, 5)
    assert not ok
    assert reason == "circles_intersect_no_external_tangent"
    assert not is_valid_external_tangent_geometry(3, 7, 5)


def test_repair_impossible_q4_values():
    stem = (
        "Circles with centres G and H have radii 3 cm and 7 cm respectively. "
        "If GH = 5 cm, find the length of the direct common external tangent EF."
    )
    assert stem_has_required_external_tangent_givens(stem)
    assert not stem_has_valid_external_tangent_givens(stem)
    new, ch = repair_external_tangent_stem(stem, seed=0)
    assert ch
    assert stem_has_valid_external_tangent_givens(new)
    assert "GH = 13" in new or "GH = 20" in new or "GH = 14" in new


def test_repair_tangent_secant_clean_pq():
    stem = (
        "Hence, from external point P, tangent PA = 15 cm touches at A, and secant PQR "
        "meets the circle at R (nearer P) and Q with PR = 4 cm. Find RQ."
    )
    new, ch = repair_tangent_secant_stem(stem)
    assert ch
    assert "PR = 4" not in new
    assert "PR = 9" in new or "PR = 5" in new or "PR = 15" in new


def test_converse_figure_spec_has_contact_point():
    stem = (
        "In a circle with centre O, a line through point S on the circle meets the circle only at S. "
        "Given that OS is perpendicular to this line at S, prove that the line is tangent to the circle at S."
    )
    spec = enrich_figure_spec(stem, {})
    labels = {
        (el.get("label") or "").upper()
        for el in spec.get("elements") or []
        if el.get("shape") == "point"
    }
    assert "S" in labels
    assert "O" in labels
