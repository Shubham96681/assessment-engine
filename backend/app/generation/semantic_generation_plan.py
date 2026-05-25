"""
Semantic generation plan — planning layer before prompt compilation.

Separates: what to generate (plan) from how to say it (PromptCompiler).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from app.generation.chapter_rule_packs import ChapterRulePack, get_chapter_rule_pack
from app.generation.content_profile import ContentProfile
from app.generation.rd_archetypes import (
    get_slot_metadata,
    pick_weighted_archetypes,
    sequence_slots_for_chapter,
)
from app.generation.theorem_coverage import pick_archetypes_with_theorem_coverage


@dataclass
class SlotPlan:
    slot: int
    band: str
    archetype_id: str
    archetype_name: str
    cognitive_type: str
    theorem_id: str = ""
    figure_hint: str = ""
    role: str = ""
    question_type: str = ""
    theorem_graph: str = ""
    depends_on_slots: List[int] = field(default_factory=list)
    paper_derives: List[str] = field(default_factory=list)


@dataclass
class SemanticGenerationPlan:
    locked_chapter: str
    chapter_title: str
    difficulty: str
    question_count: int
    question_types: List[str]
    bloom_level: str
    rule_pack: ChapterRulePack
    archetypes: List[Dict[str, Any]]
    required_theorems: List[Dict[str, Any]]
    slots: List[SlotPlan]
    forbidden_terms: List[str]
    figure_types: List[str]
    retrieval_confidence: float
    retrieval_mode: str  # pdf_rich | curriculum_fallback | sparse
    use_curriculum_archetypes: bool
    blueprint_text: str
    context_excerpt: str
    exclude_prior_stems: List[str] = field(default_factory=list)
    student_skill_block: str = ""
    memory_block: str = ""
    rejection_block: str = ""
    instructions: str = ""
    generation_num: int = 1
    subject: str = "Mathematics"
    class_label: str = "10"
    exam_track: str = "board"
    style_label: str = "textbook exercise"
    filename: str = ""
    topic_focus: str = ""
    difficulty_regime: str = "board_medium"
    full_hard: bool = False
    paper_dependency: Any = None  # PaperDependencyPlan
    paper_template_id: str = "chained_concentric"
    delivery_question_count: int = 0

    def cognitive_blueprint_dict(self) -> Dict[int, str]:
        return {s.slot: s.cognitive_type for s in self.slots}

    def archetype_ids(self) -> List[str]:
        return [a.get("id", "") for a in self.archetypes if a.get("id")]

    @property
    def delivery_count(self) -> int:
        d = int(self.delivery_question_count or 0)
        return d if d > 0 else self.question_count

    def effective_question_types(self) -> List[str]:
        """
        Chapter-native type mix — overrides UI 'all FigureBased' for algebra chapters.
        """
        pack = self.rule_pack
        preferred = list(pack.preferred_question_types)
        requested = [str(t) for t in self.question_types if t]
        if not requested:
            return preferred[: self.question_count] or ["ShortAnswer"]
        if self.locked_chapter == "quadratic" and all(
            t == "FigureBased" for t in requested
        ):
            return preferred[: self.question_count]
        if self.locked_chapter == "circles":
            return [
                requested[i % len(requested)]
                for i in range(self.question_count)
            ]
        if len(requested) == 1 and self.question_count > 1:
            return [
                requested[0]
                if i < pack.max_figure_based_count or requested[0] != "FigureBased"
                else preferred[i % len(preferred)]
                for i in range(self.question_count)
            ]
        out: List[str] = []
        for i in range(self.question_count):
            out.append(requested[i % len(requested)])
        return out


def _retrieval_mode(
    confidence: float,
    use_curriculum: bool,
) -> str:
    if use_curriculum or confidence < 0.45:
        return "curriculum_fallback"
    if confidence >= 0.55:
        return "pdf_rich"
    return "sparse"


def build_semantic_plan(
    *,
    locked_chapter: str,
    question_count: int,
    delivery_question_count: int = 0,
    question_types: List[Any],
    difficulty: str,
    bloom_level: Any,
    profile: ContentProfile,
    required_theorems: Optional[List[Dict[str, Any]]] = None,
    retrieval_confidence: float = 0.0,
    use_curriculum_archetypes: bool = False,
    context: str = "",
    exclude_prior_stems: Optional[List[str]] = None,
    student_skill_block: str = "",
    memory_block: str = "",
    rejection_block: str = "",
    instructions: str = "",
    generation_num: int = 1,
    author=None,
    difficulty_distribution=None,
    paper_template: Optional[str] = None,
) -> SemanticGenerationPlan:
    """Build plan once per run — PromptCompiler consumes this only."""
    from app.generation.archetype_registry import filter_archetype_dicts, validate_slot_archetypes
    from app.generation.author_styles import resolve_author_style
    from app.generation.difficulty_regime import resolve_difficulty_regime
    from app.generation.full_hard_mode import is_full_hard_paper
    from app.generation.theorem_graph_planner import plan_theorem_graph
    from app.generation.paper_dependency_graph import (
        align_archetypes_to_dependency,
        build_paper_dependency_plan,
    )
    from app.generation.paper_templates import (
        resolve_paper_template,
        template_slots_for_count,
    )

    chapter = locked_chapter or profile.chapter_key or "generic"
    profile.chapter_key = chapter
    pack = get_chapter_rule_pack(chapter)
    ui = (difficulty or "medium").lower()
    full_hard = is_full_hard_paper(difficulty_distribution)
    paper_tmpl = resolve_paper_template(
        override=paper_template,
        chapter=chapter,
        subject=profile.subject,
        class_level=profile.display_class(),
        exam_track=profile.exam_track,
        question_count=question_count,
        ui_difficulty=ui,
        full_hard=full_hard,
    )
    theorems = required_theorems or []
    author = author or resolve_author_style(instructions=instructions)

    if use_curriculum_archetypes and theorems:
        archetypes = pick_archetypes_with_theorem_coverage(
            question_count,
            chapter,
            theorems,
            ui_difficulty=ui,
        )
    else:
        archetypes = pick_weighted_archetypes(
            question_count, chapter, ui_difficulty=ui, full_hard=full_hard
        )
    archetypes = filter_archetype_dicts(archetypes, chapter)
    if not archetypes:
        from app.generation.archetype_registry import archetype_definitions_for_chapter

        archetypes = archetype_definitions_for_chapter(chapter)
        logger.warning(
            "Archetype pool empty after filter for chapter=%s — using registry definitions (%d)",
            chapter,
            len(archetypes),
        )

    dep_plan = build_paper_dependency_plan(
        chapter=chapter,
        question_count=question_count,
        slots=[],
        ui_difficulty=ui,
        full_hard=full_hard,
        paper_template_id=paper_tmpl.id,
    )
    archetypes = align_archetypes_to_dependency(archetypes, dep_plan)

    regime = resolve_difficulty_regime(
        ui,
        exam_track=profile.exam_track,
        class_level=profile.display_class(),
        full_hard=full_hard,
    )

    types = [
        t.value if hasattr(t, "value") else str(t) for t in question_types
    ]
    effective_types = list(pack.preferred_question_types)
    if chapter == "quadratic" and types and all(t == "FigureBased" for t in types):
        effective_types = list(pack.preferred_question_types)[:question_count]
    elif types:
        if len(types) == 1 and question_count > 1:
            effective_types = [
                types[0]
                if i < pack.max_figure_based_count or types[0] != "FigureBased"
                else pack.preferred_question_types[
                    i % len(pack.preferred_question_types)
                ]
                for i in range(question_count)
            ]
        else:
            effective_types = [types[i % len(types)] for i in range(question_count)]

    slot_meta = get_slot_metadata(
        question_count,
        author,
        ui_difficulty=ui,
        locked_chapter=chapter,
        full_hard=full_hard,
        difficulty_distribution=difficulty_distribution,
    )
    from app.generation.chapter_prompt_config import resolve_sequence_slots

    seq_slots = resolve_sequence_slots(
        chapter, ui, full_hard=full_hard, question_count=question_count
    )
    tmpl_slots = template_slots_for_count(paper_tmpl, question_count)
    cognitive_defaults = list(pack.cognitive_blueprint_5)
    slots: List[SlotPlan] = []
    if not archetypes:
        raise ValueError(
            f"No archetypes available for chapter '{chapter}'. "
            "Check chapter_rule_packs and rd_archetypes TRIGONOMETRY_ARCHETYPES."
        )
    for i in range(question_count):
        arch = archetypes[i] if i < len(archetypes) else archetypes[-1]
        meta = slot_meta[i] if i < len(slot_meta) else {}
        seq = seq_slots[i % len(seq_slots)]
        tmpl_slot = tmpl_slots[i] if i < len(tmpl_slots) else None
        cog = cognitive_defaults[i] if i < len(cognitive_defaults) else cognitive_defaults[-1]
        qtype = effective_types[i] if i < len(effective_types) else effective_types[-1]
        aid = arch.get("id", "")
        slot_dep = dep_plan.slot_dep(i + 1)
        slots.append(
            SlotPlan(
                slot=i + 1,
                band=meta.get("band", "L3"),
                archetype_id=aid,
                archetype_name=arch.get("name", ""),
                cognitive_type=cog,
                theorem_id=arch.get("theorem_id", "")
                or (theorems[i % len(theorems)].get("id", "") if theorems else ""),
                figure_hint=meta.get("figure_complexity", ""),
                role=(
                    tmpl_slot.role.value
                    if tmpl_slot
                    else seq.get("role", cog)
                ),
                question_type=qtype,
                theorem_graph=plan_theorem_graph(aid, chapter),
                depends_on_slots=list(slot_dep.depends_on_slots) if slot_dep else [],
                paper_derives=list(slot_dep.derives) if slot_dep else [],
            )
        )

    for warn in validate_slot_archetypes(slots, chapter):
        logger.warning("Archetype registry: %s", warn)

    bloom_str = bloom_level.value if hasattr(bloom_level, "value") else str(bloom_level)

    return SemanticGenerationPlan(
        locked_chapter=chapter,
        chapter_title=pack.display_title,
        difficulty=ui,
        question_count=question_count,
        delivery_question_count=delivery_question_count or question_count,
        question_types=types,
        bloom_level=bloom_str,
        rule_pack=pack,
        archetypes=archetypes,
        required_theorems=theorems,
        slots=slots,
        forbidden_terms=list(pack.forbidden_terms),
        figure_types=list(pack.figure_types),
        retrieval_confidence=retrieval_confidence,
        retrieval_mode=_retrieval_mode(retrieval_confidence, use_curriculum_archetypes),
        use_curriculum_archetypes=use_curriculum_archetypes,
        blueprint_text="",  # compiled only via ChapterRulePack.compact_blueprint in PromptCompiler
        context_excerpt=(context or "")[:8000],
        exclude_prior_stems=list(exclude_prior_stems or []),
        student_skill_block=student_skill_block,
        memory_block=memory_block,
        rejection_block=rejection_block,
        instructions=instructions or "",
        generation_num=generation_num,
        subject=profile.subject,
        class_label=profile.display_class(),
        exam_track=profile.exam_track,
        style_label=profile.style_label,
        filename=profile.filename or "",
        topic_focus=profile.topic_focus or "",
        difficulty_regime=regime,
        full_hard=full_hard,
        paper_dependency=dep_plan,
        paper_template_id=paper_tmpl.id,
    )
