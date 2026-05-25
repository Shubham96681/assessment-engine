"""Tests for generation oversample pool sizing and selection."""
from app.generation.generation_oversample import (
    pool_question_count,
    select_best_questions,
)


def test_pool_doubles_delivery():
    assert pool_question_count(10) == 20
    assert pool_question_count(5) == 10


def test_select_best_keeps_top_by_score():
    questions = [
        {"id": "1", "content": "low", "quality_score": 0.2, "slot_number": 1},
        {"id": "2", "content": "high", "quality_score": 0.9, "slot_number": 2},
        {"id": "3", "content": "mid", "quality_score": 0.5, "slot_number": 3},
        {"id": "4", "content": "top", "quality_score": 0.95, "slot_number": 4},
    ]
    selected, meta = select_best_questions(questions, 2)
    assert len(selected) == 2
    assert meta["delivered"] == 2
    stems = [q["content"] for q in selected]
    assert "top" in stems
    assert "high" in stems
    assert selected[0]["slot_number"] == 1
    assert selected[1]["slot_number"] == 2
