"""Full-hard (100% hard slider) enforcement."""
from app.generation.chapter_paper_quality import expand_sequence_slots
from app.generation.full_hard_mode import is_full_hard_paper
from app.generation.hard_mode_calibration import classify_stem, should_reject_hard_mode
from app.generation.rd_archetypes import get_slot_bands


def test_is_full_hard_paper_at_100_percent():
    assert is_full_hard_paper({"easy": 0, "medium": 0, "hard": 100}) is True
    assert is_full_hard_paper({"easy": 10, "medium": 30, "hard": 60}) is False


def test_expand_sequence_slots_all_l5_when_full_hard():
    slots = expand_sequence_slots(
        "trigonometry",
        10,
        ui_difficulty="hard",
        full_hard=True,
    )
    assert len(slots) == 10
    assert all(s["band"] == "L5" for s in slots)
    assert not any(s.get("one_line_ok") for s in slots)
    assert slots[0]["archetype_id"] == "identity_prove"
    assert slots[9]["marks"] == 8


def test_get_slot_bands_all_l5_full_hard():
    bands = get_slot_bands(10, ui_difficulty="hard", full_hard=True)
    assert len(bands) == 10
    assert all(b == "L5" for b in bands)


def test_trigonometry_benchmark_slots_and_marks():
    from app.generation.trigonometry_hard_benchmark import (
        benchmark_slots,
        suggested_paper_totals,
        target_marks_for_slot,
    )

    slots = benchmark_slots(10)
    assert len(slots) == 10
    assert all(s["band"] == "L5" for s in slots)
    assert target_marks_for_slot(10, 10) == 8
    assert target_marks_for_slot(5, 10) == 6
    totals = suggested_paper_totals(10)
    assert totals["total_marks"] == 62  # 9×6 + 8


def test_reject_bare_trig_find_on_full_hard():
    stem = "Find cos 255° exactly."
    tags = classify_stem(stem)
    assert "trivial_trig_value_find" in tags
    q = {"content": stem, "correct_answer": "Step 1: Hence cos 255° = -(√6-√2)/4."}
    assert should_reject_hard_mode(
        q,
        slot_band="L5",
        ui_difficulty="hard",
        slot_meta={"full_hard": True},
        locked_chapter="trigonometry",
        full_hard=True,
    )
