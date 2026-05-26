"""GATE paper-level calibration for hard / full-hard assessments."""
from app.generation.content_profile import build_content_profile
from app.generation.gate_benchmark import (
    gate_level_active,
    validate_paper_against_gate,
)
from app.schemas import DifficultyDistribution


def test_hard_ui_activates_gate_level():
    assert gate_level_active(ui_difficulty="hard", exam_track="board")


def test_full_hard_distribution_activates_gate():
    dd = DifficultyDistribution(easy=0, medium=0, hard=100)
    assert gate_level_active(difficulty_distribution=dd, exam_track="board")


def test_build_profile_sets_gate_track_on_full_hard():
    dd = DifficultyDistribution(easy=0, medium=0, hard=100)
    p = build_content_profile(
        topic_focus="Trigonometry",
        difficulty="hard",
        difficulty_distribution=dd,
    )
    assert p.exam_track == "gate"
    assert p.class_label == "GATE MA"


def test_validate_paper_rejects_shallow_stem():
    dd = DifficultyDistribution(easy=0, medium=0, hard=100)
    shallow = [
        {
            "content": "Find sin 30°.",
            "marks": 1,
            "correct_answer": "Step 1: 1/2. Hence 1/2.",
        }
    ]
    rep = validate_paper_against_gate(
        shallow,
        ui_difficulty="hard",
        difficulty_distribution=dd,
        full_hard=True,
        exam_track="gate",
    )
    assert rep.get("gate_level_active")
    assert not rep.get("gate_paper_ok")
    assert rep.get("gate_paper_flags")
