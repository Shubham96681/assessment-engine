"""Q2 and Q5 must not share the same diagram topology."""
from app.generation.figure_spec_builder import enrich_figure_spec

Q2 = (
    "Using the configuration in Question 1, from external point P tangent PA = 15 cm "
    "touches the outer circle at A; secant PQR meets the circle at Q (nearer P) and R "
    "with PQ = 9 cm. Find PR."
)
Q5 = (
    "In the configuration of Question 1, with PA = 15 cm from Question 2 touching the "
    "outer circle at A. (i) Find OP. (ii) Hence point G is 34 cm from O; tangent GH "
    "touches the outer circle at H. Secant GJK meets the circle at J (nearer G) with "
    "GJ = 9 cm. Find GK."
)


def _point_labels(spec: dict) -> set[str]:
    return {
        (e.get("label") or "").upper()
        for e in spec.get("elements", [])
        if e.get("shape") == "point"
    }


def test_q2_has_concentric_and_p_not_g():
    spec = enrich_figure_spec(Q2, None)
    circles = [e for e in spec["elements"] if e.get("shape") == "circle"]
    assert len(circles) >= 2
    pts = _point_labels(spec)
    assert "P" in pts and "Q" in pts and "R" in pts
    assert "G" not in pts
    assert spec.get("layout") == "secant_tangent_concentric"


def test_q5_fusion_has_g_and_p_distinct_layout():
    spec = enrich_figure_spec(Q5, None)
    pts = _point_labels(spec)
    assert "G" in pts and "H" in pts and "J" in pts and "K" in pts
    assert "P" in pts and "A" in pts
    assert spec.get("layout") == "fusion_q5"
