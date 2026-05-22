"""
Author profiles — RD Sharma vs RS Aggarwal exercise DNA.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AuthorStyle:
    id: str
    display_name: str
    stem_length: str  # short | medium
    hidden_theorem: str  # high | medium | low
    algebra_mix: str  # high | medium | low
    hots_density: str  # high | medium | low
    compression: str  # aggressive | standard
    subparts_frequency: str  # uneven | frequent | rare
    one_line_allowed: bool
    prompt_notes: str


RD_SHARMA = AuthorStyle(
    id="rd_sharma",
    display_name="RD Sharma",
    stem_length="short",
    hidden_theorem="high",
    algebra_mix="medium",
    hots_density="high",
    compression="aggressive",
    subparts_frequency="uneven",
    one_line_allowed=True,
    prompt_notes=(
        "RD Sharma: progressive difficulty with occasional spikes; algebra inside geometry; "
        "longer solution paths in answers only; mix one-line conceptual with multi-step HOTS; "
        "stems aggressively compressed (12–40 words typical)."
    ),
)

RS_AGGARWAL = AuthorStyle(
    id="rs_aggarwal",
    display_name="RS Aggarwal",
    stem_length="short",
    hidden_theorem="medium",
    algebra_mix="low",
    hots_density="medium",
    compression="aggressive",
    subparts_frequency="rare",
    one_line_allowed=True,
    prompt_notes=(
        "RS Aggarwal: sharper, more direct trick questions; shorter stems; fewer sub-parts; "
        "frequent numeric traps without naming them; less proof-heavy than RD Sharma."
    ),
)

STYLES: Dict[str, AuthorStyle] = {
    RD_SHARMA.id: RD_SHARMA,
    RS_AGGARWAL.id: RS_AGGARWAL,
}


def resolve_author_style(
    explicit: str | None = None,
    instructions: str | None = None,
) -> AuthorStyle:
    """Pick author profile from config, instructions, or default RD Sharma."""
    if explicit:
        key = explicit.lower().replace(" ", "_").replace("-", "_")
        if "rs" in key or "aggarwal" in key:
            return RS_AGGARWAL
        if "rd" in key or "sharma" in key:
            return RD_SHARMA
        if key in STYLES:
            return STYLES[key]
    if instructions:
        low = instructions.lower()
        if "rs aggarwal" in low or "rs_aggarwal" in low:
            return RS_AGGARWAL
        if "rd sharma" in low or "rd_sharma" in low:
            return RD_SHARMA
    return RD_SHARMA


def author_style_prompt_block(
    style: AuthorStyle,
    question_count: int = 5,
    *,
    locked_chapter: str = "",
) -> str:
    from app.generation.author_imperfections import imperfection_prompt_block

    ch = (locked_chapter or "").strip().lower()
    algebra_line = (
        "- Algebra in geometry: high\n"
        if ch in ("circles", "generic", "")
        else "- Algebra mix: chapter-native (word models, discriminant chains).\n"
    )
    base = (
        f"AUTHOR PROFILE: {style.display_name}\n"
        f"- Stem length: {style.stem_length} ({style.compression} compression)\n"
        f"- Hidden theorem: {style.hidden_theorem}\n"
        f"{algebra_line}"
        f"- HOTS density: {style.hots_density}\n"
        f"- Sub-parts: {style.subparts_frequency} (not every question)\n"
        f"- One-line questions: {'allowed' if style.one_line_allowed else 'discouraged'} for conceptual items\n"
        f"{style.prompt_notes}\n"
    )
    if question_count >= 3 and ch == "circles":
        base += "\n" + imperfection_prompt_block(
            style, question_count, locked_chapter=ch
        )
    return base
