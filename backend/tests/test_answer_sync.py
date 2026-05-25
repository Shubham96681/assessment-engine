"""Answer key must match question stem values."""
from app.generation.answer_sync import (
    answer_stem_value_mismatches,
    build_tangent_secant_answer,
    sync_paper_answers,
)
from app.generation.paper_repair import repair_paper_questions


def test_tangent_secant_answer_uses_pq9():
    ans = build_tangent_secant_answer(15, 9, outer_r=29)
    assert "PQ = 9" in ans or "9 × PR" in ans
    assert "37.5" not in ans
    assert "PR = 25" in ans


def test_mismatch_detector():
    stem = "PA = 15 cm and PQ = 9 cm"
    bad = "PA = 15 cm and PQ = 6 cm, PR = 37.5"
    issues = answer_stem_value_mismatches(stem, bad)
    assert any("PQ" in x for x in issues)


def test_sync_after_repair_q2():
    qs = [
        {
            "slot_number": 1,
            "content": "Two concentric circles have centre O and radii 29 cm and 21 cm. Find DE.",
            "correct_answer": "old",
            "question_type": "FigureBased",
        },
        {
            "slot_number": 2,
            "content": (
                "Using Question 1, tangent PA = 15 cm; secant PQR with PQ = 9 cm. Find PR."
            ),
            "correct_answer": "With PQ = 6 cm, PR = 37.5 cm.",
            "question_type": "FigureBased",
        },
    ]
    synced = sync_paper_answers(qs, chapter="circles")
    assert not answer_stem_value_mismatches(
        synced[1]["content"], synced[1]["correct_answer"]
    )
    assert "25" in synced[1]["correct_answer"]
