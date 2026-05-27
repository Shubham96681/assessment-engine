"""M.Tech L8–L9 stem gate for quadratic 100% hard."""
from app.generation.quadratic_mtech_stem_gate import (
    evaluate_quadratic_mtech_stem,
    should_reject_quadratic_mtech_stem,
)


def test_rejects_board_drill():
    stem = "Solve 2x² + 5x − 3 = 0 by factorisation."
    assert should_reject_quadratic_mtech_stem(stem)


def test_accepts_existence_proof():
    stem = (
        "Prove that there exists no quadratic equation ax² + bx + c = 0 with "
        "positive integer coefficients such that the discriminant is a prime number "
        "and the sum of the roots equals the product of the roots. "
        "If you believe such an equation exists, construct one and verify all conditions; "
        "otherwise, prove impossibility by contradiction."
    )
    r = evaluate_quadratic_mtech_stem(stem)
    assert r.get("mtech_stem_ok") is True
    sigs = r.get("quadratic_fusion_signals") or []
    assert "existence_proof" in sigs
