"""Paper 10 — LaTeX regression fragments and export validation."""
from app.export.pdf_content_prep import prepare_questions_for_pdf
from app.generation.question_text import ensure_plain_text, has_raw_latex


def test_paper10_mathsf_fragments_stripped():
    samples = [
        r"\mathsf{P Q}=\mathsf{9}",
        r"\mathbf{A}.",
        r"\mathsf{G H}^{\wedge}2\\ {\sf G J}\times\mathsf{G K}.",
        r"\mathsf{G J}=\mathsf{}9\mathsf",
        r"\\mathsf{P Q}=\\mathsf{9}",
    ]
    for raw in samples:
        out = ensure_plain_text(raw)
        assert not has_raw_latex(out), f"LaTeX leaked: {raw!r} -> {out!r}"
        assert "mathsf" not in out.lower()
        assert "mathbf" not in out.lower()


def test_paper10_gh_equals_and_2touching():
    assert "GH = 17" in ensure_plain_text("If GH 17cm")
    assert "2 touching" in ensure_plain_text("from Question 2touching")


def test_prepare_blocks_raw_latex_in_export():
    qs = prepare_questions_for_pdf(
        [{"content": r"\mathsf{PQ}=\mathsf{9}", "question_type": "MCQ"}]
    )
    assert "mathsf" not in qs[0]["content"]
