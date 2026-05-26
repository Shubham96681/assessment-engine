"""Trigonometry full-hard stem gate — Q19 series quality."""
from app.generation.trigonometry_hard_stem_gate import (
    evaluate_trigonometry_full_hard_stem,
    is_series_gold_stem,
    should_reject_trigonometry_full_hard_stem,
)


def test_q19_gold_stem_accepted():
    stem = (
        "Evaluate exactly: sin²(π/8)+sin²(3π/8)+sin²(5π/8)+sin²(7π/8). "
        "Hence find the exact value of Σ sin²(kπ/(2n+1)) from k=1 to n."
    )
    assert is_series_gold_stem(stem)
    ok, flags = should_reject_trigonometry_full_hard_stem(
        stem, slot_meta={"skill": "S-S", "ref_slot": 19, "section": "F"}
    )
    assert ok is False
    assert not flags


def test_thin_tan_sum_rejected_on_series_slot():
    stem = "If A+B+C=π, prove tan A+tan B+tan C=tan A tan B tan C. Evaluate tan 25°+tan 55°+tan 100°."
    ok, flags = should_reject_trigonometry_full_hard_stem(
        stem, slot_meta={"skill": "S-S", "ref_slot": 19}
    )
    assert ok is True
    assert any("series" in f or "fusion" in f for f in flags)


def test_sin2_without_general_sum_rejected():
    stem = "Evaluate exactly sin² 12°+sin² 36°+sin² 60°+sin² 84°."
    r = evaluate_trigonometry_full_hard_stem(stem, slot_meta={"ref_slot": 19})
    assert r["trig_hard_stem_ok"] is False
