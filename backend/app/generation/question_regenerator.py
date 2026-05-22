"""
Per-slot regeneration when quality gate rejects a question.
Retries with fix instructions until accepted or max attempts.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.generation.angle_target_validator import try_fix_angle_target
from app.generation.prompt_compiler import PromptCompiler
from app.generation.semantic_generation_plan import build_semantic_plan
from app.generation.content_profile import build_content_profile
from app.generation.question_completeness import ensure_minimum_context
from app.generation.rd_archetypes import ARCHETYPE_BY_ID, get_slot_bands

logger = logging.getLogger(__name__)


def collect_rejection_feedback(q: Dict[str, Any]) -> str:
    """Human-readable fix list for regeneration prompt."""
    parts: List[str] = []
    for key in (
        "completeness_flags",
        "stem_dependency_flags",
        "figure_necessity_flags",
        "reasoning_depth_flags",
        "hard_mode_flags",
        "reasoning_flags",
        "angle_target_flags",
        "proof_elegance_flags",
        "numeric_flags",
        "geometry_flags",
        "authenticity_flags",
    ):
        flags = q.get(key) or []
        for f in flags:
            if f and f not in parts:
                parts.append(str(f))
    if q.get("combined_score", 1) < 0.38:
        parts.append("low_combined_quality_score")
    return "; ".join(parts[:12]) or "quality_below_threshold"


def build_slot_regeneration_prompt(
    *,
    slot_index: int,
    slot_meta: Dict[str, Any],
    slot_band: str,
    context: str,
    task: Dict[str, Any],
    reject_feedback: str,
    rejected_stem: str,
    exclude_stems: List[str],
    ui_difficulty: str,
    locked_chapter: str = "",
) -> str:
    arch_id = slot_meta.get("archetype_id", "")
    arch = ARCHETYPE_BY_ID.get(arch_id, {})
    hint = arch.get("stem_hint") or arch.get("example") or ""
    exclude_block = ""
    if exclude_stems:
        lines = "\n".join(f"- {s[:180]}" for s in exclude_stems[:20])
        exclude_block = f"\nDo NOT repeat these stems:\n{lines}\n"

    return build_cursor_slot_regen_question(
        slot_index=slot_index,
        slot_meta=slot_meta,
        slot_band=slot_band,
        context=context,
        task=task,
        reject_feedback=reject_feedback,
        rejected_stem=rejected_stem,
        exclude_stems=exclude_stems,
        ui_difficulty=ui_difficulty,
        locked_chapter=locked_chapter,
    )


def build_cursor_slot_regen_question(
    *,
    slot_index: int,
    slot_meta: Dict[str, Any],
    slot_band: str,
    context: str,
    task: Dict[str, Any],
    reject_feedback: str,
    rejected_stem: str,
    exclude_stems: List[str],
    ui_difficulty: str,
    locked_chapter: str = "",
) -> str:
    """Prompt body for rag_query.txt — Cursor agent regenerates one rejected slot."""
    arch_id = slot_meta.get("archetype_id", "")
    arch = ARCHETYPE_BY_ID.get(arch_id, {})
    hint = arch.get("stem_hint") or arch.get("example") or ""
    exclude_block = ""
    if exclude_stems:
        lines = "\n".join(f"- {s[:180]}" for s in exclude_stems[:20])
        exclude_block = f"\nPRIOR QUESTIONS — DO NOT REPEAT OR PARAPHRASE:\n{lines}\n"

    chapter = locked_chapter or slot_meta.get("locked_chapter") or "generic"
    profile = build_content_profile(
        topic_focus="",
        filename="",
        context=context[:1200],
        difficulty=ui_difficulty,
    )
    profile.chapter_key = chapter
    plan = build_semantic_plan(
        locked_chapter=chapter,
        question_count=slot_index + 5,
        question_types=[task.get("type") or "FigureBased"],
        difficulty=ui_difficulty,
        bloom_level=task.get("bloom_level", "Analyze"),
        profile=profile,
        context=context,
        exclude_prior_stems=exclude_stems,
    )
    compiler = PromptCompiler.from_plan(plan)

    qtype = task.get("type")
    if hasattr(qtype, "value"):
        qtype = qtype.value
    qtype = qtype or "FigureBased"

    regen_header = compiler.compile_slot_regeneration(
        slot_index=slot_index,
        reject_feedback=reject_feedback,
        rejected_stem=rejected_stem,
    )
    return (
        regen_header
        + f"\n\nREGENERATION TARGET:\n"
        f"- Type: {qtype} | Difficulty: {task.get('difficulty', 'hard')} | Bloom: {task.get('bloom_level', 'Analyze')}\n"
        f"- Archetype hint: {hint}\n"
        f"{exclude_block}\n"
        f"\nCHAPTER CONTEXT (use only):\n---\n{context[:4000]}\n---"
    )


def try_auto_repair(q: Dict[str, Any], slot_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Rule-based fixes before calling LLM again."""
    out = dict(q)
    out = ensure_minimum_context(out)
    flags = (out.get("numeric_flags") or []) + (out.get("hard_mode_flags") or [])
    stem = (out.get("content") or "").lower()

    if any("tangent_secant_mismatch" in f for f in flags):
        stem_full = out.get("content") or ""
        if "TC = 6" in stem_full and "TD = 15" in stem_full:
            out["content"] = stem_full.replace("TC = 6", "TC = 3").replace(
                "TD = 15", "TD = 27"
            )
        elif "TA = 9" in stem_full:
            out["content"] = stem_full.replace("TD = 15", "TD = 27").replace(
                "TC = 6", "TC = 3"
            )

    if any("angle_center_mismatch" in f for f in flags) or (
        "angle poq" in stem and "ta" in stem and "tb" in stem
    ):
        out["content"] = (out.get("content") or "").replace("angle POQ", "angle AOB").replace(
            "angle poq", "angle AOB"
        )

    stem_full = out.get("content") or ""
    fixed_stem, angle_fixed = try_fix_angle_target(stem_full)
    if angle_fixed:
        out["content"] = fixed_stem
        out["angle_target_repaired"] = True

    if slot_meta and slot_meta.get("sparse_hard"):
        ans = out.get("correct_answer") or ""
        if isinstance(ans, str) and len(ans) > 200 and "step 1" in ans.lower():
            from app.generation.curation import compress_textbook_proof_answer

            out["correct_answer"] = compress_textbook_proof_answer(ans)

    out["auto_repaired"] = True
    return out
