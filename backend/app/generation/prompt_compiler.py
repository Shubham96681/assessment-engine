"""
Hierarchical prompt compiler — chapter-exclusive assembly; no global geometry DNA.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.core.config import settings
from app.generation.content_profile import ContentProfile, build_chapter_alignment
from app.generation.prompt_purity import (
    filter_memory_prompt_block,
    filter_stems_by_chapter,
    find_prompt_contamination,
    sanitize_prompt_lines,
    validate_prompt_purity,
)
from app.generation.prompt_sections import (
    PromptSection,
    PromptSectionGuardError,
    assert_sections_match_chapter,
    assemble_prompt,
    filter_sections_by_chapter,
)
from app.generation.semantic_generation_plan import SemanticGenerationPlan, build_semantic_plan

logger = logging.getLogger(__name__)


class PromptCompiler:
    """Compile from SemanticGenerationPlan + single ChapterRulePack only."""

    def __init__(self, plan: SemanticGenerationPlan):
        self.plan = plan
        self.pack = plan.rule_pack
        self._locked = (plan.locked_chapter or "generic").strip().lower()

    @classmethod
    def from_plan(cls, plan: SemanticGenerationPlan) -> "PromptCompiler":
        return cls(plan)

    def _sec(self, category: str, text: str, *, chapter: str = "") -> PromptSection:
        ch = (chapter or self._locked or "any").strip().lower()
        return PromptSection(chapter=ch, category=category, text=text)

    def section_system_role(self) -> str:
        p = self.plan
        tmpl_line = ""
        if getattr(p, "paper_template_id", ""):
            from app.generation.paper_templates import get_paper_template, template_header_for_plan

            tmpl = get_paper_template(p.paper_template_id)
            if tmpl:
                tmpl_line = f"\n{template_header_for_plan(tmpl)}"
        return (
            f"SYSTEM: {p.class_label} {p.subject} author ({p.style_label}).\n"
            f"LOCKED CHAPTER: {p.chapter_title} (key={p.locked_chapter}).\n"
            f"Exam track: {p.exam_track}. Round #{p.generation_num}.\n"
            f"You must generate ONLY {p.chapter_title} content — no other chapter templates."
            f"{tmpl_line}"
        )

    def section_difficulty_calibration(self) -> str:
        from app.generation.prompt_builder import PromptBuilder

        return PromptBuilder.difficulty_section(self.plan)

    def section_assessment_architect(self) -> str:
        from app.generation.prompt_builder import PromptBuilder

        return PromptBuilder.architect_section(
            chapter=self._locked,
            question_count=self.plan.question_count,
            full_hard=getattr(self.plan, "full_hard", False),
        )

    def section_preferred_types(self) -> str:
        return self.pack.preferred_types_block()

    def section_chapter_rules(self) -> str:
        """Hard / numeric / reasoning / idiomatic — chapter pack methods only."""
        p = self.plan
        parts = [
            f"CHAPTER RULES — {self.pack.display_title} ONLY:",
            self.pack.forbidden_block(),
            self.pack.figure_types_block(),
            "",
            "Allowed archetype ids (exclusive pool):",
            self.pack.archetype_table(),
        ]
        # hard_mode_block already includes reasoning + numeric + idiomatic (no duplicate blocks)
        if p.difficulty in ("hard", "difficult"):
            hm = self.pack.hard_mode_block(
                p.difficulty, full_hard=getattr(p, "full_hard", False)
            )
            if hm:
                parts.extend(["", hm])
        else:
            for block in (
                self.pack.numeric_rules_block(),
                self.pack.reasoning_diversity_block(
                    question_count=p.question_count,
                    paper_template_id=getattr(p, "paper_template_id", None),
                    ui_difficulty=p.difficulty,
                    full_hard=getattr(p, "full_hard", False),
                ),
                self.pack.idiomatic_block(),
            ):
                if block:
                    parts.extend(["", block])
        return "\n".join(parts)

    def section_author_imperfection(self) -> str:
        from app.generation.author_imperfections import chapter_imperfection_prompt_block

        return chapter_imperfection_prompt_block(
            self._locked, self.plan.question_count
        )

    def section_cognitive_blueprint(self) -> str:
        from app.generation.theorem_graph_planner import blueprint_theorem_graph_section

        lines = [f"COGNITIVE BLUEPRINT — {self.pack.display_title}:"]
        for s in self.plan.slots:
            qtype = getattr(s, "question_type", "") or ""
            type_note = f" | type={qtype}" if qtype else ""
            graph = getattr(s, "theorem_graph", "") or ""
            graph_note = f" | graph: {graph}" if graph else ""
            lines.append(
                f"  Q{s.slot} [{s.band}] {s.cognitive_type} | archetype={s.archetype_id}{type_note}{graph_note}"
            )
        graph_block = blueprint_theorem_graph_section(self.plan.slots, self._locked)
        if graph_block:
            lines.extend(["", graph_block])
        return "\n".join(lines)

    def _section_paper_dependency(self) -> str:
        dep = getattr(self.plan, "paper_dependency", None)
        if not dep or not getattr(dep, "enabled", False):
            return ""
        from app.generation.paper_dependency_graph import dependency_prompt_section

        return dependency_prompt_section(dep)

    def section_exercise_blueprint(self) -> str:
        return self.pack.compact_blueprint(
            self.plan.slots,
            ui_difficulty=self.plan.difficulty,
            full_hard=getattr(self.plan, "full_hard", False),
        )

    def section_author_style(self) -> str:
        return self.pack.author_style_note()

    def section_few_shot_style(self) -> str:
        from app.generation.prompt_builder import PromptBuilder

        base = PromptBuilder.few_shot_section(
            self._locked,
            full_hard=getattr(self.plan, "full_hard", False),
        )
        return (
            f"{base}\n"
            f"- Pack example: {self.pack.stem_example}\n"
            f"- {self.pack.rag_style_note}\n"
            "- BAN: Use the diagram; Show your working; Students often; Using theorem."
        )

    def section_retrieval_context(self) -> str:
        p = self.plan
        if p.retrieval_mode == "curriculum_fallback":
            guidance = (
                "RAG STYLE (not content copy): curriculum structures only; textbook-aligned.\n"
                "Avoid theorem fusion absent from syllabus list."
            )
        elif p.retrieval_mode == "pdf_rich":
            guidance = (
                "RAG STYLE (not content copy): match SOURCE compression, step depth, cognitive rhythm.\n"
                f"Retrieval confidence {p.retrieval_confidence:.2f} — invent new numbers/labels."
            )
        else:
            guidance = "RAG STYLE: light SOURCE inspiration; prefer chapter rule pack structures."
        ctx = p.context_excerpt
        if p.locked_chapter in ("quadratic", "triangles", "trigonometry"):
            ctx_hits = find_prompt_contamination(ctx, p.locked_chapter)
            if ctx_hits:
                ctx = (
                    "[Context trimmed — foreign phrases removed from retrieval.]\n"
                    + sanitize_prompt_lines(ctx, p.locked_chapter)
                )
        return (
            guidance
            + "\n\nSOURCE CONTENT:\n---\n"
            + ctx
            + "\n---"
        )

    def section_student_and_memory(self) -> str:
        parts = []
        if self.plan.student_skill_block:
            parts.append(self.plan.student_skill_block.strip())
        if self.plan.memory_block:
            filtered = filter_memory_prompt_block(
                self.plan.memory_block, self.plan.locked_chapter
            )
            if filtered:
                parts.append(filtered)
        if self.plan.rejection_block:
            parts.append(self.plan.rejection_block.strip())
        return "\n\n".join(parts)

    def section_validation_rules(self) -> str:
        terms = "\n".join(f"  - {t}" for t in self.plan.forbidden_terms[:18])
        return (
            f"VALIDATION — {self.pack.display_title}:\n"
            f"FORBIDDEN:\n{terms}\n"
            + self.pack.semantic_completeness_rules()
        )

    def section_output_schema(self) -> str:
        effective = self.plan.effective_question_types()
        types = ", ".join(effective)
        n = self.plan.question_count
        per_slot = "\n".join(
            f'  id "{s.slot}": type={getattr(s, "question_type", "") or effective[(s.slot - 1) % len(effective)]}'
            for s in self.plan.slots
        )
        return f"""
OUTPUT CONTRACT:
- JSON array only; exactly {n} objects; ids "1".." {n}"
- Chapter-native type mix (see per-slot types below):
{per_slot}
- Allowed types this paper: {types}
- Keys: id, type, question, marks, correct_answer
- MCQ: options[4], correct_answer label
- FigureBased: only when diagram/table required; figure_type in ({", ".join(self.pack.figure_types)}); figure_spec; correct_answer
- Max FigureBased count: {self.pack.max_figure_based_count}
- Optional: explanation, theorem_tags, cognitive_type
""".strip()

    def section_alignment_guard(self) -> str:
        profile = ContentProfile(
            chapter_key=self.plan.locked_chapter,
            subject=self.plan.subject,
            class_label=self.plan.class_label,
            filename=self.plan.filename,
            chapter_title=self.plan.chapter_title,
            exam_track=self.plan.exam_track,
        )
        return build_chapter_alignment(profile)

    def section_exclude_prior(self) -> str:
        from app.generation.prompts import _format_exclude_prior_block

        stems = filter_stems_by_chapter(
            self.plan.exclude_prior_stems, self.plan.locked_chapter
        )
        return _format_exclude_prior_block(stems, locked_chapter=self.plan.locked_chapter)

    def compile_sections(self) -> List[PromptSection]:
        """Ordered tagged sections — chapter-exclusive; no global TEXTBOOK_EXERCISE_STYLE."""
        raw: List[PromptSection] = [
            self._sec("system", self.section_system_role()),
            self._sec("difficulty", self.section_difficulty_calibration()),
            self._sec("assessment_architect", self.section_assessment_architect()),
            self._sec("preferred_types", self.section_preferred_types()),
            self._sec("author_style", self.section_author_style()),
            self._sec("author_imperfection", self.section_author_imperfection()),
            self._sec("chapter_rules", self.section_chapter_rules()),
            self._sec("cognitive_blueprint", self.section_cognitive_blueprint()),
            self._sec(
                "paper_dependency",
                self._section_paper_dependency(),
            ),
            self._sec("exercise_blueprint", self.section_exercise_blueprint()),
            self._sec("few_shot", self.section_few_shot_style()),
            self._sec("retrieval", self.section_retrieval_context()),
            self._sec("memory", self.section_student_and_memory()),
            self._sec("validation", self.section_validation_rules()),
            self._sec("output_schema", self.section_output_schema()),
            self._sec("alignment", self.section_alignment_guard()),
            self._sec("exclude_prior", self.section_exclude_prior()),
        ]
        return [s for s in raw if s.text and s.text.strip()]

    def compile_full_prompt(self, *, strict_sections: bool = True) -> str:
        """
        Chapter-exclusive prompt — filter foreign sections, assert tags, check dominance.
        """
        sections = filter_sections_by_chapter(
            self.compile_sections(), self._locked
        )
        if strict_sections:
            assert_sections_match_chapter(sections, self._locked)
        prompt = assemble_prompt(sections)
        from app.core.config import settings

        if settings.ENABLE_PROMPT_SECTION_DOMINANCE:
            from app.generation.semantic_section_weight import (
                validate_section_dominance,
            )

            report = validate_section_dominance(
                prompt,
                self._locked,
                max_foreign_ratio=settings.PROMPT_FOREIGN_TOPIC_RATIO_MAX,
            )
            if not report.get("section_dominance_ok"):
                flags = report.get("section_dominance_flags") or []
                logger.warning(
                    "Section dominance weak chapter=%s foreign=%.3f flags=%s",
                    self._locked,
                    report.get("foreign_topic_ratio"),
                    flags,
                )
                if settings.PROMPT_SECTION_DOMINANCE_STRICT:
                    from app.generation.prompt_purity import PromptContaminationError

                    raise PromptContaminationError(
                        self._locked,
                        [f"dominance:{f}" for f in flags],
                    )
        return prompt

    def compile_core(self) -> str:
        return self.compile_full_prompt()

    def compile_file_agent_task(
        self,
        *,
        types_label: str,
        extra_task_note: str = "",
    ) -> str:
        p = self.plan
        effective = p.effective_question_types()
        label = types_label or ", ".join(effective)
        from app.generation.generation_oversample import oversample_prompt_note

        task = (
            f"TASK: Generate exactly {p.question_count} questions.\n"
            f"Types (chapter-native mix): {label}. Difficulty: {p.difficulty}. Bloom: {p.bloom_level}.\n"
            f"Chapter: {p.chapter_title} ONLY.\n"
            f"Max FigureBased: {self.pack.max_figure_based_count}.\n"
            f"{oversample_prompt_note(p.delivery_count)}{extra_task_note}"
        )
        return task + "\n\n" + self.compile_full_prompt()

    def compile_slot_regeneration(
        self,
        *,
        slot_index: int,
        reject_feedback: str,
        rejected_stem: str,
    ) -> str:
        p = self.plan
        s = p.slots[slot_index] if slot_index < len(p.slots) else None
        arch_hint = f"Archetype: {s.archetype_id} | {s.cognitive_type}" if s else ""
        qtype = getattr(s, "question_type", "") if s else ""
        return (
            f"QUALITY REGENERATION — slot {slot_index + 1} | {p.chapter_title} ONLY.\n"
            f"{arch_hint}\n"
            f"Required type: {qtype}\n"
            f"FIX: {reject_feedback}\n"
            f"REJECTED: {rejected_stem[:400]}\n\n"
            + self.compile_full_prompt()
            + f"\n\nANSWER: one JSON object; id={slot_index + 1}; type={qtype}"
        )


def build_generation_prompt(
    plan: SemanticGenerationPlan,
    *,
    type_tail: str = "",
    types_label: str = "",
    file_agent: bool = False,
    strict_purity: bool = True,
) -> str:
    compiler = PromptCompiler.from_plan(plan)
    if file_agent:
        prompt = compiler.compile_file_agent_task(types_label=types_label)
    else:
        prompt = compiler.compile_full_prompt()
    if type_tail:
        tail_hits = find_prompt_contamination(type_tail, plan.locked_chapter)
        if tail_hits:
            logger.warning("Type tail contamination stripped: %s", tail_hits[:5])
            type_tail = sanitize_prompt_lines(type_tail, plan.locked_chapter)
        prompt = prompt + "\n\nTYPE-SPECIFIC OUTPUT:\n" + type_tail
    validate_prompt_purity(prompt, plan.locked_chapter, strict=strict_purity)
    if settings.ENABLE_CBSE_BENCHMARK:
        try:
            from app.generation.cbse_benchmark import benchmark_prompt_hints

            hints = benchmark_prompt_hints(plan.class_label or "10")
            if hints:
                prompt = prompt + "\n\n" + hints
        except Exception as exc:
            logger.debug("CBSE benchmark prompt hints skipped: %s", exc)
    if settings.ENABLE_CBSE_REFERENCE and plan.locked_chapter not in ("", "generic"):
        try:
            from app.generation.cbse_reference_ingest import load_cbse_reference_manifest

            man = load_cbse_reference_manifest()
            ch_count = (man.get("chapters") or {}).get(plan.locked_chapter, 0)
            if ch_count:
                prompt = prompt + (
                    f"\n\nCBSE chapter index: {ch_count} board stems for "
                    f"{plan.locked_chapter}; match SQP mark weight and stem compression."
                )
        except Exception as exc:
            logger.debug("CBSE reference prompt hints skipped: %s", exc)
    logger.debug(
        "Prompt purity OK chapter=%s len=%d",
        plan.locked_chapter,
        len(prompt),
    )
    return prompt


def build_plan_and_prompt(
    *,
    locked_chapter: str,
    question_count: int,
    question_types: list,
    difficulty: str,
    bloom_level,
    profile: ContentProfile,
    context: str,
    required_theorems: Optional[list] = None,
    retrieval_confidence: float = 0.0,
    use_curriculum_archetypes: bool = False,
    exclude_prior_stems: Optional[list] = None,
    student_skill_block: str = "",
    memory_block: str = "",
    rejection_block: str = "",
    instructions: str = "",
    generation_num: int = 1,
    file_agent: bool = False,
    types_label: str = "",
    type_tail: str = "",
    strict_purity: bool = True,
    difficulty_distribution=None,
    paper_template: Optional[str] = None,
) -> tuple[SemanticGenerationPlan, str]:
    plan = build_semantic_plan(
        locked_chapter=locked_chapter,
        question_count=question_count,
        question_types=question_types,
        difficulty=difficulty,
        bloom_level=bloom_level,
        profile=profile,
        required_theorems=required_theorems,
        retrieval_confidence=retrieval_confidence,
        use_curriculum_archetypes=use_curriculum_archetypes,
        context=context,
        exclude_prior_stems=exclude_prior_stems,
        student_skill_block=student_skill_block,
        memory_block=memory_block,
        rejection_block=rejection_block,
        instructions=instructions or "",
        generation_num=generation_num,
        difficulty_distribution=difficulty_distribution,
        paper_template=paper_template,
    )
    prompt = build_generation_prompt(
        plan,
        type_tail=type_tail,
        types_label=types_label,
        file_agent=file_agent,
        strict_purity=strict_purity,
    )
    return plan, prompt
