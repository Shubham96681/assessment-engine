"""Global pipeline — all chapters get LaTeX strip and spacing fixes."""
from app.generation.question_pipeline import (
    finalize_question_dict,
    finalize_questions_list,
    prepare_questions_after_generation,
)
from app.generation.question_text import has_raw_latex


def test_finalize_quadratic_stem():
    raw = {
        "content": r"Solve \mathbf{x}^2 + \mathsf{P Q}=9 from Question 2touching.",
        "correct_answer": r"\mathrm{A}, verify PA2=PQ x PR",
        "question_type": "ShortAnswer",
    }
    out = finalize_question_dict(raw)
    assert not has_raw_latex(out["content"])
    assert not has_raw_latex(out["correct_answer"])
    assert "2 touching" in out["content"]
    assert "PA²" in out["correct_answer"]


def test_finalize_list_all_chapters():
    qs = finalize_questions_list(
        [
            {"content": r"\mathsf{AB}=5", "slot_number": 1},
            {"content": "Find x when 2x=4", "slot_number": 2},
        ]
    )
    assert len(qs) == 2
    assert "mathsf" not in qs[0]["content"]


def test_prepare_after_generation_generic_chapter():
    qs = prepare_questions_after_generation(
        [{"content": r"\mathsf{GH}=3", "question_type": "MCQ"}],
        chapter="quadratic",
        repair=True,
    )
    assert not has_raw_latex(qs[0]["content"])
