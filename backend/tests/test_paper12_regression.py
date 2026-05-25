"""Paper 12 — Q5 phrase integrity, fro GH detection, fusion validation."""
from app.export.paper_validator import validate_questions_for_pdf
from app.generation.question_text import ensure_plain_text, to_reportlab_markup


def test_q5_from_o_preserved():
    stem = (
        "In the configuration of Question 1, with PA = 15 cm from Question 2. "
        "(ii) Hence point G is 34 cm from O; tangent GH touches the outer circle at H."
    )
    out = ensure_plain_text(stem)
    assert "from O" in out
    assert "tangent GH" in out
    assert "fro GH" not in out


def test_markup_protects_from_o_tangent():
    raw = "Hence point G is 34 cm from O; tangent GH touches"
    m = to_reportlab_markup(raw)
    assert "from\u00a0O" in m
    assert "tangent\u00a0GH" in m


def test_validator_rejects_fro_gh():
    bad = [
        {
            "slot_number": 5,
            "content": (
                "In the configuration of Question 1. Hence point G is 34cm fro GH touches."
            ),
            "question_type": "FigureBased",
            "figure_url": "/x.png",
        }
    ]
    r = validate_questions_for_pdf(bad)
    assert not r["ok"]
    assert any("fro" in e.lower() or "from O" in e for e in r["errors"])


def test_validator_accepts_good_fusion():
    good = [
        {
            "slot_number": 5,
            "content": (
                "In the configuration of Question 1, with PA = 15 cm. "
                "(ii) Hence point G is 34 cm from O; tangent GH touches at H. GJ = 9 cm."
            ),
            "question_type": "FigureBased",
            "figure_url": "/x.png",
        }
    ]
    r = validate_questions_for_pdf(good)
    assert r["ok"], r["errors"]


def test_validator_accepts_fusion_tangent_lm():
    good = [
        {
            "slot_number": 5,
            "content": (
                "In the configuration of Question 1, with NE = 15 cm from Question 2 "
                "touching at E. (i) Find ON. (ii) Hence point L is 37 cm from O; "
                "tangent LM touches at M. Secant LJK with LJ = 17 cm."
            ),
            "question_type": "FigureBased",
            "figure_url": "/x.png",
        }
    ]
    r = validate_questions_for_pdf(good)
    assert r["ok"], r["errors"]
