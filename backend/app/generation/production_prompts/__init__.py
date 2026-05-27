"""Compact production prompts — replace verbose compiler output per chapter/mode."""
from __future__ import annotations

from typing import Optional

from app.generation.production_prompts.quadratic_full_hard import (
    QUADRATIC_FULL_HARD_PRODUCTION_PROMPT,
    build_quadratic_full_hard_prompt,
)
from app.generation.production_prompts.quadratic_mtech_full_hard import (
    build_quadratic_mtech_prompt,
)
from app.generation.semantic_generation_plan import SemanticGenerationPlan


def uses_quadratic_production_prompt(plan: SemanticGenerationPlan) -> bool:
    from app.core.config import settings
    from app.generation.full_hard_mode import is_full_hard_paper

    if not settings.QUADRATIC_PRODUCTION_PROMPT_ENABLED:
        return False
    ch = (plan.locked_chapter or "").strip().lower()
    if ch != "quadratic":
        return False
    fh = getattr(plan, "full_hard", False) or is_full_hard_paper(
        getattr(plan, "difficulty_distribution", None)
    )
    return bool(fh)


def resolve_production_prompt(plan: SemanticGenerationPlan) -> Optional[str]:
    """Return compact prompt text when this plan matches a production template."""
    if uses_quadratic_production_prompt(plan):
        return build_quadratic_full_hard_prompt(plan)
    return None


__all__ = [
    "QUADRATIC_FULL_HARD_PRODUCTION_PROMPT",
    "build_quadratic_full_hard_prompt",
    "build_quadratic_mtech_prompt",
    "resolve_production_prompt",
    "uses_quadratic_production_prompt",
]
