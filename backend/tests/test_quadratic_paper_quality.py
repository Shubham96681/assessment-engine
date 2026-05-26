"""Quadratic L5 paper quality monitor."""
from app.generation.quadratic_paper_quality import (
    detect_dead_subpart,
    detect_malformed_or,
    detect_unbalanced_or,
    evaluate_quadratic_paper_quality,
    evaluate_quadratic_stem_quality,
    should_reject_quadratic_stem_quality,
)


def test_rejects_dead_subpart_equation_only():
    bad = "For 5x² − 22x + 8 = 0, (i) For 5x² − 22x + 8 = 0, (ii) Hence factorise."
    assert "dead_subpart_equation_only" in detect_dead_subpart(bad)


def test_flags_malformed_or():
    stem = "Answer ONE. OR (i) Solve x². OR (ii) Find q for reciprocals."
    assert detect_malformed_or(stem)


def test_flags_trivial_reciprocal_or_branch():
    stem = (
        "Answer ONE of the following. (a) Solve 11x² + 13x − 6 = 0 using the quadratic formula. "
        "(b) Find q if the roots of x² − 7x + (q − 2) = 0 are reciprocals and verify the reciprocal product."
    )
    flags = detect_unbalanced_or(stem)
    assert any("trivial_reciprocal" in f or "too_short" in f for f in flags)


def test_passes_revised_q2_integrated():
    stem = (
        "Without solving explicitly for x first, find the discriminant of 5x² − 22x + 8 = 0, "
        "state the precise nature of the roots (distinct real and rational, equal, or non-real), "
        "and justify that nature by obtaining the roots through factorisation. "
        "Hence verify α + β and αβ against −b/a and c/a using those roots."
    )
    assert not should_reject_quadratic_stem_quality(stem)


def test_flags_subpart_reference_hallucination():
    stem = (
        "For 7x² − 26x + 15 = 0, (i) find the discriminant. "
        "(ii) Hence obtain roots by factorisation using the discriminant from (iv)."
    )
    ev = evaluate_quadratic_stem_quality(stem)
    assert any("subpart_reference" in f or "incoherent" in f for f in ev.get("stem_quality_flags", []))


def test_flags_incoherent_discriminant_factorisation():
    stem = "Find roots by factorisation using the discriminant from (i) for 5x² − 3x + 1 = 0."
    ev = evaluate_quadratic_stem_quality(stem)
    assert "incoherent_discriminant_factorisation" in (ev.get("stem_quality_flags") or [])


def test_paper_constraint_fatigue():
    q1 = {
        "question": "Without solving by the quadratic formula, factorise 8x² − 26x + 15 = 0. "
        "Hence obtain α + β from coefficients and verify against factor pairs; state whether both roots are positive."
    }
    q2 = {
        "question": "Without solving by the quadratic formula, find p if 7x² − 42x + (p + 20) = 0 has equal roots. "
        "Hence find the repeated root and verify by forming 7(x − r)²."
    }
    report = evaluate_quadratic_paper_quality([q1, q2])
    assert any("constraint_fatigue" in f for f in report.get("paper_quality_flags", []))
