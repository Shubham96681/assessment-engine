"""Quadratic full-hard stem fusion gate."""
from app.generation.quadratic_hard_stem_gate import (
    evaluate_quadratic_full_hard_stem,
    should_reject_quadratic_full_hard_stem,
)
from app.generation.hard_mode_calibration import should_reject_hard_mode


def test_rejects_bare_equal_roots():
    stem = "Find p if 9x² − 24x + (p + 7) = 0 has equal real roots."
    assert should_reject_quadratic_full_hard_stem(stem)


def test_accepts_fusion_without_solving():
    stem = (
        "Without solving 4x² − 7x − 2 = 0, (i) find the discriminant and state the nature "
        "of the roots, (ii) obtain α² + β² using coefficients only, (iii) decide which root "
        "is negative from the sign of the sum and product."
    )
    r = evaluate_quadratic_full_hard_stem(stem)
    assert r["quadratic_hard_stem_ok"] is True
    assert r["quadratic_fusion_score"] >= 2


def test_hard_mode_rejects_thin_quad_on_full_hard():
    q = {
        "content": "Solve x² − 5x + 6 = 0 by factorisation.",
        "correct_answer": "Step 1: (x-2)(x-3)=0. Step 2: x=2,3.",
    }
    assert should_reject_hard_mode(
        q,
        slot_band="L5",
        ui_difficulty="hard",
        slot_meta={"full_hard": True},
        locked_chapter="quadratic",
        full_hard=True,
    )
