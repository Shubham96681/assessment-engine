"""PDF prep must repair fusion Q5 missing 'from O' before validation."""
from app.export.pdf_content_prep import prepare_questions_for_pdf


def test_pdf_prep_injects_from_o_on_fusion_q5():
    questions = [
        {
            "slot_number": 1,
            "content": (
                "Two concentric circles have centre O and radii 17 cm and 8 cm. "
                "A chord AB of the larger circle touches the smaller circle at T. Find AB."
            ),
            "question_type": "FigureBased",
            "figure_url": "/f1.png",
        },
        {
            "slot_number": 5,
            "content": (
                "In the configuration of Question 1, with PQ = 12 cm from Question 2. "
                "(i) Find OP. (ii) Hence tangent GH at H; secant GJK with GJ = 6 cm. Find GK."
            ),
            "question_type": "FigureBased",
            "figure_url": "/f5.png",
        },
    ]
    import re

    out = prepare_questions_for_pdf(questions)
    stem = out[1].get("content") or ""
    assert re.search(r"from\s+O", stem, re.I)
    assert re.search(r"tangent\s+GH", stem, re.I)
