"""Chapter paper quality — driven by ChapterRulePack + archetype metadata."""
from app.generation.chapter_paper_quality import (
    get_chapter_quality_spec,
    normalize_chapter_paper_marks,
    planned_archetype_ids,
    should_reject_chapter_paper_quality,
    spec_from_rule_pack,
    validate_chapter_paper_quality,
    validate_exact_angle_choice,
    validate_or_balance,
)
from app.generation.chapter_rule_packs import get_chapter_rule_pack


def test_spec_built_from_rule_pack_not_local_table():
    pack = get_chapter_rule_pack("trigonometry")
    spec = spec_from_rule_pack(pack)
    assert spec is not None
    assert spec.chapter_key == "trigonometry"
    assert "standard_angle" in spec.archetype_mark_bands
    assert spec.archetype_mark_bands["standard_angle"].max_marks == 3


def test_trig_planned_10_slots_from_pack():
    ids = planned_archetype_ids("trigonometry", 10)
    assert len(ids) == 10
    assert ids.count("standard_angle") == 1
    assert ids.count("quadrant_reduction") == 1


def test_reject_minute_exact_surd():
    spec = get_chapter_quality_spec("trigonometry")
    flags = validate_exact_angle_choice(
        "Convert 162 deg 30 min to exact sin in surd form.", spec
    )
    assert flags


def test_reject_unbalanced_or():
    spec = get_chapter_quality_spec("trigonometry")
    flags = validate_or_balance(
        "Prove sin(x-y). OR Find cos(-1710 deg).", spec
    )
    assert flags


def test_normalize_inflated_marks():
    qs = [
        {
            "id": "5",
            "content": "Find sin 765°.",
            "marks": 4,
            "archetype_id": "standard_angle",
        }
    ]
    normalize_chapter_paper_marks(qs, chapter="trigonometry")
    assert qs[0]["marks"] <= 3


def test_validate_paper_skill_cap():
    qs = [
        {"id": str(i), "content": f"Find sin {400 + i * 360}°.", "marks": 5}
        for i in range(4)
    ]
    report = validate_chapter_paper_quality(qs, chapter="trigonometry")
    assert not report["chapter_quality_ok"]


def test_should_reject_inflated_single():
    q = {
        "content": "Prove cos(π − x) = −cos x.",
        "marks": 5,
        "archetype_id": "identity_prove",
    }
    assert should_reject_chapter_paper_quality(q, chapter="trigonometry")


def test_generic_chapter_has_no_spec():
    assert get_chapter_quality_spec("polynomials") is None
