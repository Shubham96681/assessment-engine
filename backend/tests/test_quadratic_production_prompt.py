"""Production prompt routing for quadratic full-hard papers."""
from app.core.config import settings
from app.generation.content_profile import ContentProfile
from app.generation.production_prompts import (
    resolve_production_prompt,
    uses_quadratic_production_prompt,
)
from app.generation.semantic_generation_plan import build_semantic_plan


def _quadratic_plan(*, full_hard: bool = True):
    profile = ContentProfile(
        chapter_key="quadratic",
        subject="Mathematics",
        class_label="10",
        filename="",
        chapter_title="Quadratic Equations",
        exam_track="board",
    )
    plan = build_semantic_plan(
        locked_chapter="quadratic",
        question_count=10,
        question_types=["LongAnswer"],
        difficulty="hard",
        bloom_level="apply",
        profile=profile,
        context="",
        difficulty_distribution={"easy": 0, "medium": 0, "hard": 100},
    )
    plan.full_hard = full_hard
    return plan


def test_uses_production_prompt_quadratic_full_hard():
    plan = _quadratic_plan(full_hard=True)
    assert uses_quadratic_production_prompt(plan) is True


def test_skips_production_prompt_when_not_full_hard():
    plan = _quadratic_plan(full_hard=False)
    assert uses_quadratic_production_prompt(plan) is False


def test_resolve_production_prompt_has_blueprint():
    plan = _quadratic_plan()
    text = resolve_production_prompt(plan)
    assert text is not None
    assert "Begin response immediately with `[`" in text
    assert "ASSESSMENT ARCHITECT PROTOCOL" not in text
    assert len(text) < 12000


def test_resolve_mtech_prompt_at_full_hard():
    plan = _quadratic_plan(full_hard=True)
    text = resolve_production_prompt(plan)
    assert text is not None
    if settings.QUADRATIC_MTECH_AT_FULL_HARD:
        assert "M.TECH" in text
        assert "existence_proof" in text
    else:
        assert "QUESTION ARCHETYPE BLUEPRINT" in text


def test_resolve_disabled_by_setting(monkeypatch):
    monkeypatch.setattr(settings, "QUADRATIC_PRODUCTION_PROMPT_ENABLED", False)
    plan = _quadratic_plan()
    assert resolve_production_prompt(plan) is None
