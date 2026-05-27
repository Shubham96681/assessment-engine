from app.export.paper_header import resolve_exam_duration, sanitize_paper_title
from app.generation.quadratic_duplicate_registry import (
    build_banned_registry_block,
    filter_questions_matching_prior_registry,
    signature_area,
    signatures_from_stem,
)


def test_area_signature_matches_iteration6():
    stem = "A rectangle has length (3x + 11) m and breadth (2x + 5) m. Its area is 153 m²."
    assert signature_area(stem) == "area:3x+11|2x+5|153"


def test_filter_drops_exact_area_reuse():
    prior = [
        "A rectangle has length (3x + 11) m and breadth (2x + 5) m. Its area is 153 m²."
    ]
    q = {
        "question": "A rectangle has length (3x + 11) m and breadth (2x + 5) m. Its area is 153 m²."
    }
    kept, rej = filter_questions_matching_prior_registry([q], prior)
    assert len(kept) == 0
    assert rej


def test_banned_block_lists_area():
    prior = [
        "A rectangle has length (3x + 11) m and breadth (2x + 5) m. Its area is 153 m²."
    ]
    block = build_banned_registry_block(prior)
    assert "153" in block
    assert "BANNED" in block


def test_exam_duration_internal_paper():
    assert resolve_exam_duration(29, 5) == "1 Hour"
    assert resolve_exam_duration(80, 10) == "3 Hours"


def test_sanitize_garbage_title():
    assert "Quadratic" in sanitize_paper_title(
        "test 222", topic_focus="Quadratic Equations"
    )
