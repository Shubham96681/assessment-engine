"""
Idiomatic geometry phrasing — RD Sharma / RS Aggarwal sentence templates.

Compression must not produce syntactically awkward or non-standard theorem wording.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional

# Phrases that sound AI-generated despite being short
AWKWARD_PATTERNS: List[Tuple[str, str]] = [
    (r"passes through the perpendicular", "awkward_perpendicular_wording"),
    (
        r"perpendicular from .+ to (?:the )?tangent .+ at .+ passes through",
        "tautological_perp_at_contact",
    ),
    (
        r"perpendicular from .+ to tangent .+ at .+ passes through",
        "tautological_perp_at_contact",
    ),
    (r"perpendicular to the perpendicular", "double_perpendicular"),
    (r"through the foot of the perpendicular", "over_abstract_perpendicular"),
    (r"mechanical-geometric", "ai_phrase"),
    (r"configuration", "ai_phrase"),
    (r"find angle\s*\.", "incomplete_angle_target"),
    (r"find angle\s*$", "incomplete_angle_target"),
    (r"find angle\s+(?!of|between|[A-Z]{2,})", "vague_angle_find"),
]

# Standard textbook idiom (use in prompts; auto-fix where safe)
IDIOMATIC_TEMPLATES: Dict[str, List[str]] = {
    "tangent_perpendicular_radius": [
        "Prove that the tangent at any point of a circle is perpendicular to the radius through the point of contact.",
        "At P on a circle with centre O, tangent PQ is drawn. Prove that OP ⟂ PQ.",
        "Prove that OT is perpendicular to tangent TR at T.",
    ],
    "equal_tangents": [
        "Prove that tangents drawn from an external point to a circle are equal in length.",
        "From T, tangents TP and TQ touch a circle with centre O. Prove that TP = TQ.",
    ],
    "tangent_length": [
        "PQ is a tangent at P to a circle with centre O. OP = {r} cm, OQ = {d} cm. Find PQ.",
        "From Q, the length of the tangent to a circle is {t} cm and OQ = {d} cm. Find the radius.",
    ],
    "angle_between_tangents": [
        "From T, tangents TP and TQ are drawn to a circle with centre O. If angle POQ = {a}°, find angle PTQ.",
        "Tangents TA and TB from T. If angle ATB = {a}°, find angle AOB.",
    ],
    "concentric_chord": [
        "Two concentric circles have centre O and radii {R} cm and {r} cm. Find the length of a chord of the larger circle that touches the smaller.",
    ],
    "interior_tangent": [
        "Can a tangent be drawn to a circle through a point inside the circle?",
    ],
}

# Auto-fix awkward → idiomatic (safe substitutions only)
_STEM_FIXES: List[Tuple[str, str]] = [
    (
        r"Prove that the perpendicular from O to (?:the )?tangent ([A-Z]{2}) at ([A-Z]) passes through \2\.?",
        r"Prove that O\2 is perpendicular to tangent \1 at \2.",
    ),
    (
        r"Prove that the perpendicular from O to tangent ([A-Z]{2}) at ([A-Z]) passes through \2\.?",
        r"Prove that O\2 is perpendicular to tangent \1 at \2.",
    ),
    (
        r"Prove that OT passes through the perpendicular to TR at T\.?",
        "Prove that OT is perpendicular to tangent TR at T.",
    ),
    (
        r"Prove that OT passes through the perpendicular to the tangent TR at T\.?",
        "Prove that OT is perpendicular to tangent TR at T.",
    ),
    (
        r"the perpendicular at the point of contact to the tangent passes through the centre",
        "the tangent at any point is perpendicular to the radius through the point of contact",
    ),
]


def detect_awkward_idiom(stem: str) -> List[str]:
    low = stem.lower()
    flags = []
    for pattern, flag in AWKWARD_PATTERNS:
        if re.search(pattern, low, re.I):
            flags.append(flag)
    return flags


def remove_scaffolded_chord_length(stem: str) -> Tuple[str, bool]:
    """Drop pre-derived chord length when radii are already in a concentric+secant stem."""
    if not stem or "concentric" not in stem.lower():
        return stem, False
    if not re.search(r"\b(?:outer|inner)\s+radius\b|\bradii\b", stem, re.I):
        return stem, False
    new, n = re.subn(
        r";\s*a chord of the outer circle touching the inner circle has length[^.;]+(?:cm)?\.?\s*",
        "; ",
        stem,
        flags=re.I,
    )
    if not n:
        new, n = re.subn(
            r",\s*a chord[^,]+touching the inner circle has length[^,]+,\s*",
            ", ",
            stem,
            flags=re.I,
        )
    if n:
        new = re.sub(r";\s*From\b", ". From", new)
        new = re.sub(r";\s+", ". ", new)
    return (new.strip(), n > 0)


def apply_idiomatic_fix(stem: str) -> Tuple[str, bool]:
    """Return (possibly fixed stem, was_changed)."""
    if not stem:
        return stem, False
    out = stem.strip()
    changed = False
    for pattern, repl in _STEM_FIXES:
        new_out, n = re.subn(pattern, repl, out, flags=re.IGNORECASE)
        if n:
            out = new_out
            changed = True
    out2, sc = remove_scaffolded_chord_length(out)
    if sc:
        out = out2
        changed = True
    cleaned = re.sub(r";\s*From\b", ". From", out)
    cleaned = re.sub(r";\s+(?=[A-Z])", ". ", cleaned)
    if cleaned != out:
        out = cleaned
        changed = True
    return out.strip(), changed


def idiomatic_prompt_block(chapter: str = "generic") -> str:
    from app.generation.chapter_prompt_isolation import idiomatic_prompt_block as _chapter_block

    ch = (chapter or "generic").strip().lower()
    block = _chapter_block(ch)
    if block:
        return block
    if ch == "quadratic":
        return _chapter_block("quadratic")
    lines = [
        "IDIOMATIC GEOMETRY (mandatory — sound like RD Sharma, not AI syntax):",
        "- Tangent ⟂ radius: 'Prove that OT is perpendicular to tangent TR at T' OR standard theorem sentence.",
        "- BAN: 'passes through the perpendicular', 'foot of the perpendicular', vague 'find angle.'",
        "- Angle find: name full angle (PTQ, AOB) AND give at least one angle or length in the stem.",
        "",
        "Templates (adapt numbers; do not copy verbatim):",
    ]
    for key, templates in list(IDIOMATIC_TEMPLATES.items())[:6]:
        lines.append(f"  [{key}] {templates[0]}")
    return "\n".join(lines)
