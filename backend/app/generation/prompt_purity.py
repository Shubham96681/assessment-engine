"""
Strict prompt purity — detect and block foreign-chapter contamination before LLM.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from app.generation.chapter_rule_packs import CHAPTER_RULES, get_chapter_rule_pack

# Section headers / phrases that must never appear outside their chapter
_FOREIGN_SECTION_MARKERS: dict[str, Tuple[str, ...]] = {
    "quadratic": (
        "HARD MODE — Circles",
        "REASONING GRAPH DIVERSITY — Circles",
        "REASONING GRAPH DIVERSITY (mandatory for hard papers)",
        "NUMERIC CONSISTENCY — Circles",
        "IDIOMATIC GEOMETRY",
        "tangent ⟂ radius",
        "TA² = TC",
        "angle APB + angle AOB",
        "concentric chord",
        "tangent_pair",
        "Prove that PA = PB",
        "dashed radii",
        "point of contact",
        "secant–tangent power",
        "VISUAL STYLE (RD Sharma): dashed",
        "radius_style",
        "chord_naming",
        "[tangent",
        "[concentric",
        "[angle_between_tangents",
        "[secant_tangent",
        "Q1–Q2 medium+ with DISTINCT reasoning graphs",
        "Max ONE tangent-pair",
    ),
    "circles": (
        "HARD MODE — Quadratic",
        "REASONING DIVERSITY — Quadratic",
        "discriminant D = b²",
        "parameter k traps",
    ),
    "quadrilaterals": (
        "HARD MODE — Circles",
        "tangent–secant",
        "TA² = TC",
        "discriminant D = b²",
    ),
    "triangles": (
        "HARD MODE — Circles",
        "REASONING GRAPH DIVERSITY — Circles",
        "NUMERIC CONSISTENCY — Circles",
        "concentric chord",
        "tangent–secant power",
        "IDIOMATIC GEOMETRY",
    ),
    "trigonometry": (
        "HARD MODE — Circles",
        "REASONING GRAPH DIVERSITY — Circles",
        "NUMERIC CONSISTENCY — Circles",
        "concentric",
        "point of contact",
        "secant–tangent",
    ),
}

# Archetype ids from other chapters (high-signal)
_FOREIGN_ARCHETYPE_IDS: dict[str, Tuple[str, ...]] = {
    "quadratic": (
        "length_find",
        "angle_theorem",
        "hidden_theorem",
        "concentric",
        "chord_tangent",
        "secant_tangent",
        "tangent_similarity",
        "cyclic_angle",
        "common_tangent",
        "hots_mixed",
        "direct_theorem",
        "converse_identify",
    ),
    "circles": (
        "factorisation_roots",
        "nature_of_roots",
        "equal_roots_k",
        "word_problem_area",
        "formula_roots",
        "hots_quad",
    ),
}


class PromptContaminationError(Exception):
    """Raised when compiled prompt contains foreign-chapter content."""

    def __init__(self, chapter: str, hits: List[str]):
        self.chapter = chapter
        self.hits = hits
        super().__init__(
            f"Prompt contamination for chapter={chapter}: {', '.join(hits[:12])}"
            + (f" (+{len(hits) - 12} more)" if len(hits) > 12 else "")
        )


def _term_in_text(term: str, text: str) -> bool:
    t = term.strip().lower()
    if not t or len(t) < 2:
        return False
    # Word-boundary match — avoids "Circles" / "encircle" false positives for "circle"
    if t.replace(" ", "").isalpha():
        return bool(re.search(rf"\b{re.escape(t)}\b", text, re.I))
    return t in text.lower()


def _is_forbidden_declaration_line(line: str, *, banned_terms: Tuple[str, ...] = ()) -> bool:
    """Lines that list banned words on purpose must not count as contamination."""
    low = line.lower()
    stripped = line.strip()
    if (
        "do not use" in low
        or "forbidden:" in low
        or stripped.lower().startswith("forbidden")
        or "banned vocabulary" in low
        or "ban circle" in low
        or "ban in every stem" in low
        or "ban:" in low
        or ("ban " in low and "vocabulary" in low)
        or "not geometry" in low
        or "no unrelated geometry" in low
        or "no circle/tangent" in low
        or "ignore any circle-only" in low
        or "do not use circle" in low
        or "apply only the hard mode" in low
        or "no circle" in low
        or "never circle" in low
        or "not circle" in low
        or "circle diagram" in low
        or "unless chapter is circles" in low
    ):
        return True
    # Bullet list of banned tokens only, e.g. "  - tangent"
    if stripped.startswith("- "):
        item = stripped[2:].strip().lower()
        if banned_terms and item in {t.lower() for t in banned_terms}:
            return True
        if item in {
            "circle",
            "tangent",
            "secant",
            "radius",
            "chord",
            "concentric",
            "aob",
            "centre o",
        }:
            return True
    return False


def find_prompt_contamination(prompt: str, chapter: str) -> List[str]:
    """Return list of contamination signals (empty = pure)."""
    if not prompt:
        return []
    ch = (chapter or "generic").strip().lower()
    pack = get_chapter_rule_pack(ch)
    hits: List[str] = []
    low = prompt.lower()

    banned = tuple(pack.forbidden_terms)
    for line in prompt.splitlines():
        if _is_forbidden_declaration_line(line, banned_terms=banned):
            continue
        for term in pack.forbidden_terms:
            if _term_in_text(term, line):
                hits.append(f"forbidden:{term}")
                break

    for marker in _FOREIGN_SECTION_MARKERS.get(ch, ()):
        if marker.lower() in low:
            hits.append(f"section:{marker[:40]}")

    for arch_id in _FOREIGN_ARCHETYPE_IDS.get(ch, ()):
        if f"[{arch_id}]" in prompt or f"archetype={arch_id}" in prompt:
            hits.append(f"archetype:{arch_id}")

    # Other chapters' rule-pack titles embedded
    for other_key, other in CHAPTER_RULES.items():
        if other_key == ch:
            continue
        title = f"CHAPTER RULES — {other.display_title} ONLY"
        if title in prompt:
            hits.append(f"foreign_pack:{other_key}")

    return hits


def validate_prompt_purity(prompt: str, chapter: str, *, strict: bool = True) -> str:
    """
    Lexical + semantic + section-dominance purity. Raises PromptContaminationError on failure.
    """
    hits = find_prompt_contamination(prompt, chapter)
    if not hits:
        from app.generation.semantic_embedding_purity import (
            semantic_embedding_contamination,
        )

        hits = semantic_embedding_contamination(prompt, chapter)
    from app.core.config import settings

    if settings.ENABLE_PROMPT_SECTION_DOMINANCE:
        from app.generation.semantic_section_weight import validate_section_dominance

        dom = validate_section_dominance(
            prompt,
            chapter,
            max_foreign_ratio=settings.PROMPT_FOREIGN_TOPIC_RATIO_MAX,
        )
        if not dom.get("section_dominance_ok"):
            hits = hits + [f"dominance:{f}" for f in dom.get("section_dominance_flags", [])]
    if hits and strict:
        raise PromptContaminationError(chapter, hits)
    return prompt


def sanitize_prompt_lines(prompt: str, chapter: str) -> str:
    """Drop lines that contain forbidden terms (last-resort fallback)."""
    ch = (chapter or "generic").strip().lower()
    pack = get_chapter_rule_pack(ch)
    markers = set(_FOREIGN_SECTION_MARKERS.get(ch, ()))
    forbidden = {t.lower() for t in pack.forbidden_terms}
    out: List[str] = []
    for line in prompt.splitlines():
        low = line.lower()
        if any(m.lower() in low for m in markers):
            continue
        if any(_term_in_text(t, line) for t in forbidden):
            continue
        if any(f"[{aid}]" in line for aid in _FOREIGN_ARCHETYPE_IDS.get(ch, ())):
            continue
        out.append(line)
    return "\n".join(out)


def filter_stems_by_chapter(stems: List[str], chapter: str) -> List[str]:
    """Exclude prior stems from other chapters (e.g. circle items in quadratic paper)."""
    if not stems:
        return []
    hits_for = find_prompt_contamination  # reuse term check
    kept: List[str] = []
    for s in stems:
        if not s:
            continue
        contam = find_prompt_contamination(s, chapter)
        if not contam:
            kept.append(s)
    return kept


def filter_memory_prompt_block(block: str, chapter: str) -> str:
    """Remove memory lines that reference foreign-chapter theorems/combos."""
    if not block:
        return ""
    ch = (chapter or "generic").strip().lower()
    foreign_theorems = set()
    for other_key, other in CHAPTER_RULES.items():
        if other_key == ch:
            continue
        foreign_theorems.update(other.theorem_pattern_ids)
        foreign_theorems.update(other.archetype_ids)

    pack = get_chapter_rule_pack(ch)
    foreign_vocab = {t.lower() for t in pack.forbidden_terms}
    lines = []
    for line in block.splitlines():
        low = line.lower()
        if any(t.replace("_", " ") in low or t in low for t in foreign_theorems):
            if foreign_vocab and any(_term_in_text(term, line) for term in foreign_vocab):
                continue
        lines.append(line)
    return "\n".join(lines)
