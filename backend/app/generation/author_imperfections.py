"""
Author imperfection profiles — controlled human habits (not bugs).

RD Sharma: proof-heavy closures, repeated RHS congruence patterns.
RS Aggarwal: short algebraic endings, sharper numeric tricks.
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
    """
    Slot-level exercise memory — earlier pattern returns disguised later.
    teach_idx / reuse_idx are 0-based order_index.
    """
    if question_count < 4:
        return []
    teach = 1  # Q2 teaches
    reuse = min(question_count - 1, 4)  # Q5 or last
    ch = (locked_chapter or "").strip().lower()
    if ch == "quadratic":
        pattern = "discriminant / factorisation chain"
        note = (
            f"Q{teach + 1} teaches a quadratic move; Q{reuse + 1} reuses it disguised "
            "(new numbers, same inference — e.g. parameter k after area model)."
        )
    elif ch == "quadrilaterals":
        pattern = "diagonal / midpoint proof chain"
        note = f"Q{teach + 1} teaches; Q{reuse + 1} reuses disguised quadrilateral proof."
    else:
        pattern = "tangent length / right triangle from radius"
        note = (
            f"Q{teach + 1} teaches; Q{reuse + 1} reuses disguised "
            "(different labels, same inference)."
        )
    return [
        {
            "teach_index": teach,
            "reuse_index": reuse,
            "pattern": pattern,
            "note": note,
        }
    ]


QUADRATIC_IMPERFECTIONS = AuthorImperfectionProfile(
    author_id="quadratic_chapter",
    proof_structure_habit="Hence chains after forming ax²+bx+c=0; verify roots by substitution.",
    closing_style="Numeric roots with units on word problems; reject extraneous lengths.",
    theorem_repeat_bias=["discriminant nature", "equal roots parameter k"],
    imperfect_compression_rate=0.25,
    sparse_hard_slot=3,
    sparse_hard_hint=(
        "Sparse hard: minimal stem naming only k or 'the equation' — but equation MUST appear; "
        "answer needs discriminant + root relation (6+ steps)."
    ),
    visual=VisualStyleMemory(
        radius_style="N/A — no circle radii",
        tangent_placement="N/A",
        chord_naming="rectangle ABCD or segment A–B for speed",
        symmetry="label breadth x, length expression in terms of x",
        figure_spec_hints=[
            "rectangle with length/breadth labels",
            "table: equation | D | nature of roots",
            "line segment A–B for distance/speed",
        ],
    ),
    exercise_memory_template=(
        "EXERCISE MEMORY: Q{teach} area/speed model; Q{reuse} disguised parameter or discriminant trap."
    ),
)

QUADRILATERAL_IMPERFECTIONS = AuthorImperfectionProfile(
    author_id="quadrilaterals_chapter",
    proof_structure_habit="Prove … Hence find — diagonal and midpoint steps.",
    closing_style="Hence length or angle in cm/degrees.",
    theorem_repeat_bias=["opposite sides equal", "diagonals bisect"],
    imperfect_compression_rate=0.22,
    sparse_hard_slot=3,
    sparse_hard_hint="Sparse hard: one-line prove with full givens in answer only.",
    visual=VisualStyleMemory(
        radius_style="N/A",
        tangent_placement="N/A",
        chord_naming="vertices A–D on parallelogram",
        symmetry="mark parallel sides with arrows",
        figure_spec_hints=["diagonals AC, BD intersecting at O"],
    ),
    exercise_memory_template="EXERCISE MEMORY: Q{teach} proof; Q{reuse} Hence find variant.",
)

CHAPTER_IMPERFECTIONS: Dict[str, AuthorImperfectionProfile] = {
    "quadratic": QUADRATIC_IMPERFECTIONS,
    "quadrilaterals": QUADRILATERAL_IMPERFECTIONS,
    "circles": RD_IMPERFECTIONS,
}


def get_chapter_imperfection_profile(locked_chapter: str, author: AuthorStyle) -> AuthorImperfectionProfile:
    ch = (locked_chapter or "").strip().lower()
    return CHAPTER_IMPERFECTIONS.get(ch, get_imperfection_profile(author))


def imperfection_prompt_block(
    author: AuthorStyle,
    question_count: int,
    *,
    locked_chapter: str = "",
) -> str:
    ch = (locked_chapter or "").strip().lower()
    profile = get_chapter_imperfection_profile(ch, author)
    memory = build_exercise_memory_plan(question_count, locked_chapter=ch)
    lines = [
        f"AUTHOR IMPERFECTION — {ch or 'chapter'} (controlled realism — not errors):",
        f"- Proof habit: {profile.proof_structure_habit}",
        f"- Closing: {profile.closing_style}",
        f"- May repeat patterns: {', '.join(profile.theorem_repeat_bias[:2])}",
        f"- Sparse hard at Q{profile.sparse_hard_slot}: {profile.sparse_hard_hint}",
        "- Imperfect compression: ~1 in 4 stems may keep slight redundancy (human, not AI-perfect).",
    ]
    if ch == "circles":
        lines.extend(
            [
                f"- Visual style: {profile.visual.radius_style}; {profile.visual.tangent_placement}",
                f"- Figure habits: {'; '.join(profile.visual.figure_spec_hints[:2])}",
            ]
        )
    elif ch == "quadratic":
        lines.extend(
            [
                f"- Figure habits (algebra only): {'; '.join(profile.visual.figure_spec_hints[:2])}",
                "- BAN circle/tangent vocabulary in stems and figure_spec.",
            ]
        )
    elif ch == "quadrilaterals":
        lines.append(
            f"- Figure habits: {'; '.join(profile.visual.figure_spec_hints[:2])}"
        )
    if memory:
        lines.append(f"- {memory[0]['note']}")
    return "\n".join(lines)


def chapter_imperfection_prompt_block(locked_chapter: str, question_count: int = 5) -> str:
    from app.generation.author_styles import RD_SHARMA

    return imperfection_prompt_block(
        RD_SHARMA, question_count, locked_chapter=locked_chapter
    )
