"""
Resolve question types from ChapterRulePack — no FigureBased default for non-geometry chapters.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.generation.chapter_rule_packs import get_chapter_rule_pack


def preferred_type_for_slot(chapter: str, slot_index: int) -> str:
    """Slot-native type from pack.preferred_question_types (0-based slot_index)."""
    pack = get_chapter_rule_pack(chapter)
    types = tuple(pack.preferred_question_types) or ("LongAnswer",)
    t = types[slot_index % len(types)]
    if t == "FigureBased" and pack.max_figure_based_count <= 0:
        return "LongAnswer"
    return t


def resolve_slot_question_type(
    chapter: str,
    slot_index: int,
    explicit: str = "",
) -> str:
    """Prefer explicit JSON type; else pack slot type; never silent FigureBased for algebra/trig."""
    ex = (explicit or "").strip()
    if ex and ex != "FigureBased":
        return ex
    pack = get_chapter_rule_pack(chapter)
    if ex == "FigureBased":
        if pack.uses_concentric_uniqueness or pack.max_figure_based_count > 2:
            return "FigureBased"
        return preferred_type_for_slot(chapter, slot_index)
    return preferred_type_for_slot(chapter, slot_index)


def user_selected_figure_based(question_types: Optional[List[Any]]) -> bool:
    if not question_types:
        return False
    for t in question_types:
        s = t.value if hasattr(t, "value") else str(t)
        if s == "FigureBased":
            return True
    return False


def coerce_exportable_question_types(
    questions: List[Dict[str, Any]],
    chapter: str,
) -> List[Dict[str, Any]]:
    """
    Downgrade FigureBased without figure_url so PDF export does not block.
    Respects pack: trig/quad default to text types.
    """
    pack = get_chapter_rule_pack(chapter)
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(questions):
        fixed = dict(q)
        slot = int(fixed.get("slot_number") or (i + 1))
        qtype = fixed.get("question_type") or fixed.get("type") or ""
        if qtype == "FigureBased" and not fixed.get("figure_url"):
            if not pack.uses_concentric_uniqueness or pack.max_figure_based_count <= 1:
                new_type = preferred_type_for_slot(chapter, slot - 1)
                fixed["question_type"] = new_type
                fixed["type"] = new_type
                fixed.pop("figure_spec", None)
                fixed.pop("figure_type", None)
                fixed["export_type_coerced"] = True
        out.append(fixed)
    return out
