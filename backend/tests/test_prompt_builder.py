"""PromptBuilder calibration and plan integration."""
from app.generation.prompt_builder import PromptBuilder


def test_ui_difficulty_to_level_full_hard():
    assert PromptBuilder.ui_difficulty_to_level("hard", full_hard=True, slot_band="L5") == 9
    assert PromptBuilder.ui_difficulty_to_level("medium", full_hard=False, slot_band="L3") == 4


def test_few_shot_trigonometry_present():
    block = PromptBuilder.few_shot_section("trigonometry", full_hard=True)
    assert "TRIGONOMETRY" in block
    assert "FULL HARD" in block or "6 marks" in block


def test_build_generation_prompt_returns_tuple():
    sys_p, user_p = PromptBuilder.build_generation_prompt(
        "Trigonometry",
        8,
        [{"text": "sample excerpt", "source": "CBSE", "score": 0.8}],
        chapter="trigonometry",
        count=10,
        full_hard=True,
    )
    assert "assessment architect" in sys_p.lower()
    assert "DIFFICULTY: 8/9" in user_p
    assert "trigonometry" in user_p.lower()
    assert "ASSESSMENT ARCHITECT" in user_p


def test_architect_section_in_build_from_plan():
    from app.generation.semantic_generation_plan import build_semantic_plan
    from app.generation.content_profile import ContentProfile

    profile = ContentProfile(
        chapter_key="trigonometry",
        subject="Mathematics",
        class_label="10",
        filename="",
        chapter_title="Trigonometry",
        exam_track="CBSE",
    )
    plan = build_semantic_plan(
        locked_chapter="trigonometry",
        question_count=10,
        question_types=["LongAnswer"],
        difficulty="hard",
        bloom_level="apply",
        profile=profile,
        context="",
        difficulty_distribution={"easy": 0, "medium": 0, "hard": 100},
    )
    plan.full_hard = True
    _, user = PromptBuilder.build_from_plan(plan)
    assert "SKILL CATEGORY VARIANCE MATRIX" in user
