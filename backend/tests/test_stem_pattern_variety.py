"""Stem pattern variety — not every question uses (i)(ii)(iii)."""
from app.generation.stem_pattern_variety import (
    assign_stem_patterns,
    validate_paper_stem_variety,
    validate_question_stem_pattern,
    PATTERN_DIRECT_FIND,
    PATTERN_PROVE_HENCE_III,
    PATTERN_PROVE_ONLY,
)


def test_trig_full_hard_patterns_diverse():
    pats = assign_stem_patterns(10, chapter="trigonometry", full_hard=True)
    assert pats.count(PATTERN_PROVE_HENCE_III) <= 4
    assert PATTERN_PROVE_ONLY in pats
    assert PATTERN_DIRECT_FIND in pats


def test_direct_find_rejects_subparts():
    ok, flags = validate_question_stem_pattern(
        "If tan A = 5/12 and A is acute, find sin A and cos A.",
        PATTERN_DIRECT_FIND,
    )
    assert ok
    ok2, flags2 = validate_question_stem_pattern(
        "(i) If tan A = 5/12 (ii) find sin A.",
        PATTERN_DIRECT_FIND,
    )
    assert not ok2
    assert "unexpected_subparts" in flags2


def test_paper_rejects_all_triple():
    qs = [
        {"content": f"(i) part (ii) part (iii) part {i}"}
        for i in range(6)
    ]
    rep = validate_paper_stem_variety(qs)
    assert not rep["stem_variety_ok"]
    assert "too_many_triple_subpart_stems" in rep["stem_variety_flags"]
