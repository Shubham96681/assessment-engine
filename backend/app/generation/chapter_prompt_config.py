"""
Dynamic chapter prompt fragments — derived from ChapterRulePack + slot sequences.

Avoid duplicating role chains / exercise memory / suggested givens per chapter in
paper_uniqueness.py or author_imperfections.py. Register chapters in chapter_rule_packs.py.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.generation.author_styles import AuthorStyle, RD_SHARMA
from app.generation.chapter_rule_packs import CHAPTER_RULES, ChapterRulePack, get_chapter_rule_pack


def normalize_chapter_key(chapter: str) -> str:
    ch = (chapter or "generic").strip().lower()
    if ch == "similarity":
        return "triangles"
    return ch if ch in CHAPTER_RULES else "generic"


def _short_role_label(role: str, *, max_len: int = 52) -> str:
    text = (role or "").strip()
    if "—" in text:
        text = text.split("—", 1)[0].strip()
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text or "chapter task"


def sequence_slots_from_rule_pack(
    pack: ChapterRulePack,
    *,
    full_hard: bool = False,
) -> List[Dict[str, Any]]:
    """Build Q1–Q5 slot metadata from pack.cognitive_blueprint_5 (data-driven)."""
    blueprint = tuple(pack.cognitive_blueprint_5)
    if not blueprint:
        return []
    bands_hard = ("L5", "L5", "L5", "L5", "L5")
    bands_board = ("L2", "L3", "L5", "L3", "L5")
    bands = bands_hard if full_hard else bands_board
    slots: List[Dict[str, Any]] = []
    for i, role in enumerate(blueprint[:5]):
        slot_num = i + 1
        entry: Dict[str, Any] = {
            "slot": slot_num,
            "band": bands[i] if i < len(bands) else "L3",
            "role": role,
            "one_line_ok": False,
        }
        if slot_num == 2:
            entry["memory"] = "teach"
        if slot_num == 5:
            entry["memory"] = "reuse"
        if slot_num == 3:
            entry["sparse_hard"] = True
        slots.append(entry)
    return slots


def resolve_sequence_slots(
    chapter: str,
    ui_difficulty: str,
    *,
    full_hard: bool = False,
    question_count: int = 0,
) -> List[Dict[str, Any]]:
    """Slot sequence from quality plan, rule pack, or chapter_prompt_isolation."""
    from app.generation.chapter_paper_quality import expand_sequence_slots

    ch = normalize_chapter_key(chapter)
    n = question_count or 0
    if n > 0:
        expanded = expand_sequence_slots(
            ch, n, ui_difficulty=ui_difficulty, full_hard=full_hard
        )
        if expanded:
            return expanded
    from app.generation.chapter_prompt_isolation import sequence_slots_for_chapter

    return sequence_slots_for_chapter(
        ch,
        ui_difficulty,
        full_hard=full_hard,
    )


def uniqueness_role_chain(
    chapter: str,
    *,
    full_hard: bool = False,
    ui_difficulty: str = "hard",
) -> str:
    """Q1→Q5 role chain from slot sequence or cognitive blueprint."""
    slots = resolve_sequence_slots(chapter, ui_difficulty, full_hard=full_hard)
    if slots:
        labels = [_short_role_label(s.get("role", "")) for s in slots[:5]]
        if labels:
            return " → ".join(labels)
    pack = get_chapter_rule_pack(chapter)
    bp = pack.cognitive_blueprint_5
    if bp:
        return " → ".join(bp[:5])
    return " → ".join(
        get_chapter_rule_pack("generic").cognitive_blueprint_5[:5]
    )


def exercise_memory_note(
    chapter: str,
    question_count: int,
    *,
    teach_index: int = 1,
    reuse_index: Optional[int] = None,
) -> Dict[str, Any]:
    """Teach/reuse slot plan from rule pack patterns."""
    if question_count < 4:
        return {}
    pack = get_chapter_rule_pack(chapter)
    teach = teach_index
    reuse = reuse_index if reuse_index is not None else min(question_count - 1, 4)
    pattern = (
        pack.hard_difficulty_patterns[0]
        if pack.hard_difficulty_patterns
        else pack.cognitive_blueprint_5[1]
        if len(pack.cognitive_blueprint_5) > 1
        else "chapter pattern"
    )
    return {
        "teach_index": teach,
        "reuse_index": reuse,
        "pattern": pattern,
        "note": (
            f"Q{teach + 1} teaches {pattern}; Q{reuse + 1} reuses disguised "
            f"(new givens, same inference — {pack.display_title} only)."
        ),
    }


def build_exercise_memory_plan(
    question_count: int,
    *,
    locked_chapter: str = "",
) -> List[Dict[str, Any]]:
    if question_count < 4:
        return []
    mem = exercise_memory_note(locked_chapter, question_count)
    return [mem] if mem else []


def _chapter_uses_concentric_givens(pack: ChapterRulePack) -> bool:
    return pack.uses_concentric_uniqueness


def suggested_givens_lines(
    chapter: str,
    *,
    generation_num: int = 1,
    prior_stems: Optional[List[str]] = None,
    question_count: int = 5,
    full_hard: bool = True,
    ui_difficulty: str = "hard",
) -> List[str]:
    """Per-slot fresh-given hints — circles keeps numeric pair rotation; others from pack."""
    pack = get_chapter_rule_pack(chapter)
    if question_count < 5:
        return []
    prior_stems = prior_stems or []
    ch = pack.chapter_key

    if _chapter_uses_concentric_givens(pack):
        from app.generation.paper_uniqueness import (
            extract_concentric_pairs,
            pick_fresh_concentric_pair,
            pick_label_rotation,
        )

        used = extract_concentric_pairs(prior_stems)
        R, r, chord = pick_fresh_concentric_pair(generation_num, used)
        rot = pick_label_rotation(generation_num, prior_stems)
        lines = [
            "",
            "SUGGESTED FRESH GIVENS (use these or equivalent clean integers — NOT prior radii):",
            f"- Q1: concentric centre O, radii {R} cm and {r} cm (chord of larger = {chord} cm).",
            f"- Q2: external point {rot['q2_ext']}, tangent {rot['q2_tan']}, secant {rot['q2_sec']} — Hence only, cite Q1.",
            f"- Q3: independent converse tangent proof (new point label, not {rot['q2_ext']}).",
            f"- Q4: two circles with centres/labels different from O and {rot['q2_ext']}.",
            f"- Q5: fusion with {rot['fusion_ext']} from O, tangent {rot['fusion_tan']}, secant {rot['fusion_sec']}; cite Q1+Q2.",
        ]
        if used:
            banned = ", ".join(f"({a},{b})" for a, b in sorted(used)[:8])
            lines.append(f"- FORBIDDEN radii pairs already used: {banned}.")
        return lines

    slots = resolve_sequence_slots(ch, ui_difficulty, full_hard=full_hard)
    lines = [
        "",
        "SUGGESTED FRESH GIVENS (new numbers — not prior stems):",
    ]
    for i in range(min(5, question_count)):
        slot = slots[i] if i < len(slots) else {}
        role = slot.get("role") or (
            pack.cognitive_blueprint_5[i]
            if i < len(pack.cognitive_blueprint_5)
            else ""
        )
        anchor = ""
        if i < len(pack.embedding_anchors):
            anchor = f" (style: {pack.embedding_anchors[i][:72]}…)"
        lines.append(f"- Q{i + 1}: {_short_role_label(str(role))}.{anchor}")
    if pack.forbidden_terms:
        sample = ", ".join(pack.forbidden_terms[:6])
        lines.append(f"- Avoid prior stems; {pack.forbidden_block()}")
    return lines


def imperfection_profile_from_pack(
    pack: ChapterRulePack,
    author: AuthorStyle,
) -> "AuthorImperfectionProfile":
    from app.generation.author_imperfections import (
        AuthorImperfectionProfile,
        RD_IMPERFECTIONS,
        VisualStyleMemory,
        get_imperfection_profile,
    )

    key = (pack.imperfection_profile_key or "").strip().lower()
    if key == "rd_sharma":
        return RD_IMPERFECTIONS if author.id == RD_SHARMA.id else get_imperfection_profile(author)

    sparse_role = (
        pack.cognitive_blueprint_5[2]
        if len(pack.cognitive_blueprint_5) > 2
        else "sparse hard item"
    )
    figure_hints = list(pack.figure_types) or ["labeled_diagram"]
    forbidden_low = {t.lower() for t in pack.forbidden_terms}
    return AuthorImperfectionProfile(
        author_id=f"{pack.chapter_key}_derived",
        proof_structure_habit=pack.rag_style_note,
        closing_style=f"Match {pack.display_title} endings from SOURCE — exact surds/units as in chapter.",
        theorem_repeat_bias=list(pack.hard_difficulty_patterns[:3])
        or list(pack.theorem_pattern_ids[:3]),
        imperfect_compression_rate=0.25,
        sparse_hard_slot=3,
        sparse_hard_hint=(
            f"Sparse hard: minimal stem for {_short_role_label(sparse_role)} — "
            "answer needs 4+ steps; givens may be answer-only."
        ),
        visual=VisualStyleMemory(
            radius_style="N/A" if "circle" in forbidden_low or "radius" in forbidden_low else "per chapter CONTEXT",
            tangent_placement="N/A" if "tangent" in forbidden_low else "per chapter CONTEXT",
            chord_naming="N/A" if "chord" in forbidden_low else "labels from chapter CONTEXT",
            symmetry="follow SOURCE figure habits",
            figure_spec_hints=[pack.figure_types_block(), *figure_hints[:2]],
        ),
        exercise_memory_template=(
            "EXERCISE MEMORY: Q{teach} {pattern}; Q{reuse} disguised reuse ({chapter})."
        ),
    )


def exclude_prior_guidance_lines(chapter: str) -> List[str]:
    """Chapter-native NEVER REPEAT header — not circles radii/tangent boilerplate."""
    pack = get_chapter_rule_pack(chapter)
    chain = uniqueness_role_chain(chapter, full_hard=True, ui_difficulty="hard")
    lines = [
        "## NEVER REPEAT (mandatory)",
        "These stems were already used for this user/chapter. Write **entirely new** questions:",
        f"- Different numbers and givens vs the list below ({pack.display_title})",
        "- No paraphrase of the stems below",
        f"- Keep Q1→Q5 roles: {chain}",
    ]
    lines.append(pack.uniqueness_refresh_line())
    return lines


def imperfection_prompt_lines(
    pack: ChapterRulePack,
    question_count: int,
    memory: List[Dict[str, Any]],
) -> List[str]:
    profile = imperfection_profile_from_pack(pack, RD_SHARMA)
    lines = [
        f"AUTHOR IMPERFECTION — {pack.display_title} (controlled realism — not errors):",
        f"- Proof habit: {profile.proof_structure_habit}",
        f"- Closing: {profile.closing_style}",
        f"- May repeat patterns: {', '.join(profile.theorem_repeat_bias[:2])}",
        f"- Sparse hard at Q{profile.sparse_hard_slot}: {profile.sparse_hard_hint}",
        "- Imperfect compression: ~1 in 4 stems may keep slight redundancy (human, not AI-perfect).",
    ]
    if pack.figure_types and pack.max_figure_based_count > 0:
        lines.append(f"- Figure habits: {', '.join(pack.figure_types[:3])}")
    if pack.forbidden_terms:
        lines.append(f"- Chapter lock: {pack.forbidden_block()}")
    if memory:
        lines.append(f"- {memory[0]['note']}")
    return lines
