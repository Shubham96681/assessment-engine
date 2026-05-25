"""
Author imperfection profiles — controlled human habits (not bugs).

Chapter-specific habits are derived from ChapterRulePack (chapter_rule_packs.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from app.generation.author_styles import AuthorStyle, RD_SHARMA, RS_AGGARWAL


@dataclass(frozen=True)
class VisualStyleMemory:
    """Recurring figure composition habits per author."""
    radius_style: str
    tangent_placement: str
    chord_naming: str
    symmetry: str
    figure_spec_hints: List[str]


@dataclass(frozen=True)
class AuthorImperfectionProfile:
    author_id: str
    proof_structure_habit: str
    closing_style: str
    theorem_repeat_bias: List[str]
    imperfect_compression_rate: float  # 0–1 slots that keep slight redundancy
    sparse_hard_slot: int  # 1-based index for disproportionately hard item
    sparse_hard_hint: str
    visual: VisualStyleMemory
    exercise_memory_template: str


RD_IMPERFECTIONS = AuthorImperfectionProfile(
    author_id="rd_sharma",
    proof_structure_habit="Often uses RHS congruence in tangent proofs; 'Hence' chains in answers.",
    closing_style="Algebra inside geometry; longer Hence chains than RS.",
    theorem_repeat_bias=["tangent perpendicular to radius", "equal tangents from external point"],
    imperfect_compression_rate=0.25,
    sparse_hard_slot=3,
    sparse_hard_hint=(
        "Sparse hard: minimal stem (e.g. 'Prove that PA = PB.') — answer needs 6+ steps "
        "via congruence / angles; no hints in stem."
    ),
    visual=VisualStyleMemory(
        radius_style="dashed OA, OB from centre O",
        tangent_placement="external point left or above circle",
        chord_naming="AB with midpoint M on inner circle for concentric",
        symmetry="prefer symmetric tangent pair TA, TB",
        figure_spec_hints=[
            "show_right_angle at point of contact",
            "dashed radii to contacts",
            "O at centre",
        ],
    ),
    exercise_memory_template=(
        "EXERCISE MEMORY: Q{teach} establishes {pattern}; Q{reuse} reuses same cognitive move "
        "disguised (different givens, same theorem chain)."
    ),
)

RS_IMPERFECTIONS = AuthorImperfectionProfile(
    author_id="rs_aggarwal",
    proof_structure_habit="Shorter proofs; numeric close preferred over long Hence chains.",
    closing_style="Direct 'Therefore AP = … cm' endings; fewer sub-parts.",
    theorem_repeat_bias=["Pythagoras in tangent length", "angle ATB → AOB"],
    imperfect_compression_rate=0.2,
    sparse_hard_slot=5,
    sparse_hard_hint=(
        "Sparse hard: one-line numeric trap with almost no setup — student must recall full chain."
    ),
    visual=VisualStyleMemory(
        radius_style="single dashed radius to contact",
        tangent_placement="compact external P with two equal tangents",
        chord_naming="chord AB, foot M",
        symmetry="less symmetry; offset external point",
        figure_spec_hints=[
            "minimal elements — do not over-draw",
            "solid tangents, dashed radius only",
        ],
    ),
    exercise_memory_template=(
        "EXERCISE MEMORY: Q{teach} numeric find; Q{reuse} same trick with different numbers."
    ),
)

PROFILES: Dict[str, AuthorImperfectionProfile] = {
    RD_SHARMA.id: RD_IMPERFECTIONS,
    RS_AGGARWAL.id: RS_IMPERFECTIONS,
}


def get_imperfection_profile(author: AuthorStyle) -> AuthorImperfectionProfile:
    return PROFILES.get(author.id, RD_IMPERFECTIONS)


def build_exercise_memory_plan(
    question_count: int,
    *,
    locked_chapter: str = "",
) -> List[Dict[str, Any]]:
    from app.generation.chapter_prompt_config import build_exercise_memory_plan as _plan

    return _plan(question_count, locked_chapter=locked_chapter)


def get_chapter_imperfection_profile(
    locked_chapter: str, author: AuthorStyle
) -> AuthorImperfectionProfile:
    from app.generation.chapter_prompt_config import imperfection_profile_from_pack
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    pack = get_chapter_rule_pack(locked_chapter)
    return imperfection_profile_from_pack(pack, author)


def imperfection_prompt_block(
    author: AuthorStyle,
    question_count: int,
    *,
    locked_chapter: str = "",
) -> str:
    from app.generation.chapter_prompt_config import imperfection_prompt_lines
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    ch = (locked_chapter or "").strip().lower()
    pack = get_chapter_rule_pack(ch)
    memory = build_exercise_memory_plan(question_count, locked_chapter=ch)
    return "\n".join(imperfection_prompt_lines(pack, question_count, memory))


def chapter_imperfection_prompt_block(locked_chapter: str, question_count: int = 5) -> str:
    return imperfection_prompt_block(
        RD_SHARMA, question_count, locked_chapter=locked_chapter
    )
