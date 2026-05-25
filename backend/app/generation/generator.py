"""
Core Question Generation Engine
Generates all question types using LLM + RAG context
"""
import json
import logging
import uuid
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple

from app.core.config import settings
from app.rag.retriever import HybridRetriever
from app.generation.prompts import PromptBuilder
from app.generation.content_profile import (
    build_content_profile,
    build_context_fallback,
    build_curriculum_context,
    build_rag_retrieval_query,
)
from app.generation.retrieval_confidence import compute_retrieval_confidence
from app.generation.theorem_coverage import infer_required_theorems
from app.generation.theorem_coverage_score import enforce_coverage_before_delivery
from app.generation.generation_memory import (
    load_generation_memory,
    memory_avoidance_prompt,
    record_paper_memory,
    reorder_theorems_avoid_memory,
)
from app.generation.rejection_corpus import (
    load_rejection_corpus,
    record_rejection,
    rejection_avoidance_prompt,
)
from app.generation.student_skill_profile import (
    apply_student_skill_profile,
    parse_skill_list,
    student_skill_prompt_block,
)
from app.generation.topic_isolation import clear_topic_cache, save_topic_map
from app.generation.generation_orchestrator import MultiAgentOrchestrator
from app.generation.strict_topic_gate import filter_questions_by_topic
from app.generation.structural_dedup import filter_structural_duplicates
from app.generation.rd_archetypes import (
    detect_chapter_key,
    get_slot_bands,
    get_slot_metadata,
)
from app.generation.author_styles import resolve_author_style
from app.generation.generation_oversample import (
    is_oversample_active,
    pool_question_count,
)


_planned_paper_template_id: Optional[str] = None


def _set_planned_paper_template_id(template_id: Optional[str]) -> None:
    """In-process plan template (rag_topic_state.json may lag until persist)."""
    global _planned_paper_template_id
    _planned_paper_template_id = str(template_id).strip() if template_id else None


def _semantic_plan_template_id() -> Optional[str]:
    """Template locked at plan build — must match finalize/integrity checks."""
    if _planned_paper_template_id:
        return _planned_paper_template_id
    from app.generation.topic_isolation import get_current_topic_state

    tid = (get_current_topic_state() or {}).get("paper_template_id")
    return str(tid).strip() if tid else None


from app.generation.question_regenerator import (
    build_cursor_slot_regen_question,
    collect_rejection_feedback,
    try_auto_repair,
)
from app.generation.dedup import DedupEngine
from app.generation.quality import QualityScorer
from app.generation.figures import FigureGenerator
from app.generation.local_llm import build_local_response, build_local_slot_response
from app.generation.rag_file_bridge import (
    RagAgentResponseMissing,
    request_rag_file_response,
    request_rag_slot_regeneration,
)
from app.schemas import GenerationConfig, QuestionType

logger = logging.getLogger(__name__)


class QuestionGenerator:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.prompt_builder = PromptBuilder()
        self.dedup = DedupEngine()
        self.quality = QualityScorer()
        self.figure_gen = FigureGenerator()

    async def generate(
        self,
        config: GenerationConfig,
        user_id: str,
        generation_num: int = 1,
        document_meta: Optional[Dict[str, Any]] = None,
        supplement_prior_stems: Optional[List[str]] = None,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Main entry point: config → list of question dicts
        """
        delivery_n = config.total_questions
        pool_n = pool_question_count(delivery_n)
        if is_oversample_active(delivery_n):
            logger.info(
                "Oversample: generating pool of %d, delivering best %d (gen #%s)",
                pool_n,
                delivery_n,
                generation_num,
            )
        else:
            logger.info(f"Generating {delivery_n} questions (gen #{generation_num})")

        plan = self._build_generation_plan(
            config, file_agent_mode=settings.RAG_FILE_AGENT_ENABLED
        )
        all_questions: List[Dict[str, Any]] = []
        generation_log: List[Dict[str, Any]] = []

        rag_document_meta = self._build_rag_document_meta(config, document_meta)
        from app.generation.full_hard_mode import is_full_hard_paper

        rag_document_meta["question_count"] = str(pool_n)
        rag_document_meta["delivery_question_count"] = str(delivery_n)
        rag_document_meta["full_hard"] = (
            "1" if is_full_hard_paper(getattr(config, "difficulty_distribution", None)) else "0"
        )
        _set_planned_paper_template_id(None)
        topic_state = clear_topic_cache(
            document_id=config.document_id,
            filename=(document_meta or {}).get("filename", ""),
            topic_focus=config.topic_focus or "",
            context="",
            force_invalidate_response=True,
        )
        topic_profile: Dict[str, Any] = {}
        if settings.MULTI_AGENT_ORCHESTRATION:
            orchestrator = MultiAgentOrchestrator(self.retriever)
            topic_profile, agent_steps = await orchestrator.prepare_run(
                config, document_meta
            )
            generation_log.extend(agent_steps)
            topic_state.update(
                {
                    "primary_topic": topic_profile.get("primary_topic"),
                    "subtopics": topic_profile.get("subtopics"),
                    "locked_chapter": topic_profile.get(
                        "locked_chapter", topic_state.get("locked_chapter")
                    ),
                }
            )
            save_topic_map(topic_profile)
        else:
            topic_profile = {
                "locked_chapter": topic_state.get("locked_chapter", "generic"),
                "required_theorems": infer_required_theorems(
                    topic_state.get("locked_chapter", "generic"),
                    topic_focus=config.topic_focus or "",
                ),
            }
        use_curriculum_archetypes = bool(
            topic_profile.get("use_curriculum_archetypes")
            or topic_state.get("use_curriculum_archetypes")
        )
        required_theorems = (
            topic_profile.get("required_theorems")
            or topic_state.get("required_theorems")
            or []
        )
        locked_chapter = (
            (topic_profile or {}).get("locked_chapter")
            or topic_state.get("locked_chapter")
            or "generic"
        )
        if getattr(config, "locked_chapter", None):
            locked_chapter = (config.locked_chapter or "").strip().lower() or locked_chapter
        topic_state["locked_chapter"] = locked_chapter
        if topic_profile is not None:
            topic_profile["locked_chapter"] = locked_chapter
        from app.core.cbse_curriculum_doc import is_cbse_curriculum_document

        if is_cbse_curriculum_document(config.document_id):
            use_curriculum_archetypes = True
            if topic_profile is not None:
                topic_profile["use_curriculum_archetypes"] = True
                topic_profile["generation_mode"] = "cbse_curriculum"
        weak_skills: List[str] = []
        strong_skills: List[str] = []
        gen_memory: Dict[str, Any] = {}

        weak_skills = parse_skill_list(config.weak_in)
        strong_skills = parse_skill_list(config.strong_in)
        if settings.ENABLE_STUDENT_SKILL_TARGETING and (weak_skills or strong_skills):
            required_theorems = apply_student_skill_profile(
                required_theorems,
                weak_in=weak_skills,
                strong_in=strong_skills,
            )
            topic_state["student_skill_block"] = student_skill_prompt_block(
                weak_in=weak_skills, strong_in=strong_skills
            )
            topic_state["weak_in"] = weak_skills
            topic_state["strong_in"] = strong_skills

        if settings.ENABLE_GENERATION_MEMORY:
            gen_memory = await load_generation_memory(
                user_id,
                document_id=config.document_id,
                subject=config.subject or "Mathematics",
            )
            gen_memory["chapter"] = locked_chapter
            required_theorems = reorder_theorems_avoid_memory(
                required_theorems, gen_memory
            )
            topic_state["generation_memory"] = gen_memory
            topic_state["memory_prompt"] = memory_avoidance_prompt(
                gen_memory, locked_chapter=locked_chapter
            )
            save_topic_map({**(topic_profile or {}), **topic_state})

        if settings.ENABLE_REJECTION_CORPUS:
            rej_corpus = await load_rejection_corpus(
                user_id,
                document_id=config.document_id,
                chapter=locked_chapter,
            )
            topic_state["rejection_corpus"] = rej_corpus
            topic_state["rejection_prompt"] = rejection_avoidance_prompt(
                rej_corpus, locked_chapter=locked_chapter
            )
            if rej_corpus.get("items"):
                logger.info(
                    "Rejection corpus: %d examples, top flags=%s",
                    len(rej_corpus["items"]),
                    list((rej_corpus.get("flag_counts") or {}).keys())[:5],
                )

        logger.info(
            "Topic isolation: locked_chapter=%s source=%s changed=%s topic=%s",
            locked_chapter,
            topic_state.get("locked_chapter_source"),
            topic_state.get("topic_changed"),
            topic_state.get("primary_topic", ""),
        )
        from app.generation.semantic_generation_plan import build_semantic_plan as _build_plan

        _diff, _bloom = self._resolve_generation_profile(config)
        _preview_profile = build_content_profile(
            topic_focus=config.topic_focus or "",
            filename=(document_meta or {}).get("filename", ""),
            context="",
            subject=config.subject or "Mathematics",
            class_level=config.class_level or "10",
            difficulty=_diff,
        )
        _preview_profile.chapter_key = locked_chapter
        try:
            _plan = _build_plan(
                locked_chapter=locked_chapter,
                question_count=pool_n,
                delivery_question_count=delivery_n,
                question_types=config.question_types,
                difficulty=_diff,
                bloom_level=_bloom,
                profile=_preview_profile,
                required_theorems=required_theorems,
                retrieval_confidence=float(
                    topic_profile.get("retrieval_confidence") or 0.0
                ),
                use_curriculum_archetypes=use_curriculum_archetypes,
                student_skill_block=topic_state.get("student_skill_block", ""),
                memory_block=topic_state.get("memory_prompt", ""),
                rejection_block=topic_state.get("rejection_prompt", ""),
                instructions=config.instructions or "",
                difficulty_distribution=config.difficulty_distribution,
                paper_template=getattr(config, "paper_template", None),
            )
            topic_state["semantic_plan_archetypes"] = _plan.archetype_ids()
            topic_state["paper_template_id"] = _plan.paper_template_id
            topic_state["semantic_plan_cognitive"] = _plan.cognitive_blueprint_dict()
            topic_state["prompt_compiler"] = True
            _set_planned_paper_template_id(_plan.paper_template_id)
            from app.generation.topic_isolation import persist_paper_template_id

            persist_paper_template_id(_plan.paper_template_id)
        except Exception as e:
            logger.warning("Semantic plan preview failed: %s", e)

        generation_log.append(
            {
                "step": "topic_profile",
                "paper_template_id": topic_state.get("paper_template_id")
                or _semantic_plan_template_id(),
                "primary_topic": topic_state.get("primary_topic"),
                "locked_chapter": locked_chapter,
                "subtopics": topic_state.get("subtopics", []),
                "required_theorems": [
                    t.get("id") if isinstance(t, dict) else t
                    for t in required_theorems
                ],
                "semantic_plan_archetypes": topic_state.get("semantic_plan_archetypes"),
                "semantic_plan_cognitive": topic_state.get("semantic_plan_cognitive"),
                "retrieval_confidence": topic_profile.get("retrieval_confidence"),
                "generation_mode": topic_profile.get("generation_mode", "pdf_rich"),
                "use_curriculum_archetypes": use_curriculum_archetypes,
                "language": config.language,
            }
        )
        prior_stems = await self.dedup.get_recent_stem_previews(
            user_id,
            config.subject or "Mathematics",
            config.class_level or "10",
            document_id=config.document_id,
        )
        if supplement_prior_stems:
            from app.generation.prior_question_bank import merge_prior_stem_lists

            prior_stems = merge_prior_stem_lists(
                supplement_prior_stems, prior_stems, limit=50
            )
        unique_questions: List[Dict[str, Any]] = []
        max_attempts = max(1, settings.DEDUP_MAX_REGEN_ATTEMPTS)
        last_context = ""
        last_task: Optional[Dict] = None
        last_source_chunks: List[str] = []

        for attempt in range(1, max_attempts + 1):
            all_questions = []
            attempt_llm_modes: List[str] = []
            exclude_stems = list(
                dict.fromkeys(
                    prior_stems
                    + [q.get("content", "") for q in unique_questions]
                    + [q.get("content", "") for q in all_questions]
                )
            )
            exclude_stems = [s for s in exclude_stems if s]

            for step_idx, task in enumerate(plan, start=1):
                profile = build_content_profile(
                    topic_focus=config.topic_focus or "",
                    filename=(document_meta or {}).get("filename", ""),
                    context=last_context,
                    subject=config.subject
                    or (document_meta or {}).get("subject", ""),
                    class_level=config.class_level
                    or (document_meta or {}).get("class_level", ""),
                    instructions=config.instructions or "",
                    difficulty=task.get("difficulty", "medium"),
                )
                query = build_rag_retrieval_query(
                    task=task,
                    profile=profile,
                    config_topic_focus=config.topic_focus or "",
                    config_instructions=config.instructions or "",
                )
                logger.info(
                    "RAG retrieval query (doc=%s): %s",
                    config.document_id[:8],
                    query[:120],
                )
                profile.chapter_key = locked_chapter
                from app.core.cbse_curriculum_doc import is_cbse_curriculum_document

                if is_cbse_curriculum_document(config.document_id):
                    chunks = []
                    retrieval_meta = {
                        "score": 0.0,
                        "use_curriculum_archetypes": True,
                        "mode": "cbse_curriculum",
                        "reason": "topic_only_cbse_reference",
                    }
                else:
                    chunks = await self.retriever.retrieve(
                        query=query,
                        document_id=config.document_id,
                        top_k=8,
                        locked_chapter=locked_chapter,
                    )
                    retrieval_meta = compute_retrieval_confidence(chunks)
                step_curriculum = use_curriculum_archetypes or retrieval_meta[
                    "use_curriculum_archetypes"
                ]

                if step_curriculum:
                    logger.info(
                        "Curriculum mode (confidence=%.2f) — archetype context for %s",
                        retrieval_meta["score"],
                        query[:50],
                    )
                    profile = build_content_profile(
                        topic_focus=config.topic_focus or "",
                        filename=(document_meta or {}).get("filename", ""),
                        context="",
                        subject=config.subject
                        or (document_meta or {}).get("subject", ""),
                        class_level=config.class_level
                        or (document_meta or {}).get("class_level", ""),
                        instructions=config.instructions or "",
                        difficulty=task.get("difficulty", "medium"),
                    )
                    profile.chapter_key = locked_chapter
                    context = topic_profile.get("curriculum_context") or build_curriculum_context(
                        profile,
                        required_theorems=required_theorems,
                        retrieval_confidence=retrieval_meta["score"],
                    )
                    from app.generation.cbse_reference_context import enrich_context_with_cbse_reference

                    context = await enrich_context_with_cbse_reference(
                        context,
                        query=query,
                        locked_chapter=locked_chapter,
                        class_level=config.class_level
                        or (document_meta or {}).get("class_level", ""),
                    )
                    last_context = context
                    last_task = task
                    source_chunk_ids = []
                    last_source_chunks = []
                    rag_chunk_summaries = [
                        {
                            "retrieval_confidence": retrieval_meta["score"],
                            "generation_mode": "curriculum_fallback",
                        }
                    ]
                elif not chunks:
                    logger.warning(
                        "No RAG chunks for query %s — using topic fallback (still generating)",
                        query[:60],
                    )
                    profile = build_content_profile(
                        topic_focus=config.topic_focus or "",
                        filename=(document_meta or {}).get("filename", ""),
                        context="",
                        subject=config.subject
                        or (document_meta or {}).get("subject", ""),
                        class_level=config.class_level
                        or (document_meta or {}).get("class_level", ""),
                        instructions=config.instructions or "",
                        difficulty=task.get("difficulty", "medium"),
                    )
                    context = build_context_fallback(profile)
                    from app.generation.cbse_reference_context import enrich_context_with_cbse_reference

                    context = await enrich_context_with_cbse_reference(
                        context,
                        query=query,
                        locked_chapter=locked_chapter,
                        class_level=config.class_level
                        or (document_meta or {}).get("class_level", ""),
                    )
                    last_context = context
                    last_task = task
                    source_chunk_ids = []
                    last_source_chunks = []
                    rag_chunk_summaries = []
                else:
                    context = "\n\n---\n\n".join([c["text"] for c in chunks[:settings.MAX_RETRIEVAL_CHUNKS]])
                    from app.generation.cbse_reference_context import enrich_context_with_cbse_reference

                    context = await enrich_context_with_cbse_reference(
                        context,
                        query=query,
                        locked_chapter=locked_chapter,
                        class_level=config.class_level
                        or (document_meta or {}).get("class_level", ""),
                    )
                    profile = build_content_profile(
                        topic_focus=config.topic_focus or "",
                        filename=(document_meta or {}).get("filename", ""),
                        context=context,
                        subject=config.subject
                        or (document_meta or {}).get("subject", ""),
                        class_level=config.class_level
                        or (document_meta or {}).get("class_level", ""),
                        instructions=config.instructions or "",
                        difficulty=task.get("difficulty", "medium"),
                    )
                    last_context = context
                    last_task = task
                    source_chunk_ids = [c.get("qdrant_id") for c in chunks[:6]]
                    last_source_chunks = source_chunk_ids
                    rag_chunk_summaries = [
                        {
                            "page_num": c.get("page_num"),
                            "score": round(c.get("score", 0), 4),
                            "text_preview": (c.get("text") or "")[:400],
                        }
                        for c in chunks[:6]
                    ]

                doc_filename = (rag_document_meta or {}).get("filename", "")
                prompt = self.prompt_builder.build(
                    question_type=task["type"],
                    difficulty=task["difficulty"],
                    bloom_level=task["bloom_level"],
                    context=context,
                    count=task["count"],
                    delivery_count=task.get("delivery_count", config.total_questions),
                    subject=config.subject,
                    class_level=config.class_level,
                    topic_focus=config.topic_focus,
                    exclude_topics=config.exclude_topics,
                    language=config.language,
                    generation_num=generation_num,
                    figure_types=config.figure_types if task["type"] == QuestionType.FIGURE_BASED else None,
                    instructions=config.instructions,
                    document_filename=doc_filename,
                    exclude_prior_stems=exclude_stems,
                    locked_chapter=locked_chapter,
                    required_theorems=required_theorems,
                    retrieval_confidence=retrieval_meta.get("score", 0.0),
                    use_curriculum_archetypes=step_curriculum,
                    student_skill_block=topic_state.get("student_skill_block", ""),
                    memory_block=topic_state.get("memory_prompt", ""),
                    rejection_block=topic_state.get("rejection_prompt", ""),
                    difficulty_distribution=config.difficulty_distribution,
                )

                raw_questions, llm_mode = await self._generate_raw_response(
                    prompt,
                    context,
                    task,
                    document_meta=rag_document_meta,
                    retrieval_query=query,
                    exclude_prior_stems=exclude_stems,
                    generation_num=generation_num,
                    generation_attempt=attempt,
                )
                attempt_llm_modes.append(llm_mode)

                parsed = self._parse_llm_output(
                    raw_questions, task, config, source_chunk_ids
                )
                parsed, topic_rejected = filter_questions_by_topic(
                    parsed,
                    locked_chapter=locked_chapter,
                    lenient_fallback=settings.TOPIC_GATE_LENIENT_FALLBACK,
                )
                if topic_rejected:
                    logger.warning(
                        "Topic gate rejected %d items (locked=%s)",
                        len(topic_rejected),
                        locked_chapter,
                    )
                parsed = filter_structural_duplicates(parsed)

                if task["type"] == QuestionType.FIGURE_BASED and settings.ENABLE_FIGURE_GENERATION:
                    parsed = await self._attach_figures(parsed)

                generation_log.append({
                    "step": step_idx,
                    "attempt": attempt,
                    "question_type": task["type"].value if hasattr(task["type"], "value") else str(task["type"]),
                    "difficulty": task["difficulty"],
                    "bloom_level": task["bloom_level"].value if hasattr(task["bloom_level"], "value") else str(task["bloom_level"]),
                    "count_requested": task["count"],
                    "rag_query": query,
                    "rag_chunks": rag_chunk_summaries,
                    "llm_prompt": prompt,
                    "llm_response": (raw_questions or "")[:20000],
                    "llm_mode": llm_mode,
                    "llm_note": {
                        "gemini": "Live AI response from Google Gemini using the RAG prompt",
                        "openai": "Live AI response from OpenAI using the RAG prompt",
                        "groq": "Live AI response from Groq using the RAG prompt",
                        "ollama": "Live AI response from Ollama (local) using the full RAG prompt",
                        "rag_file_agent": "Response from rag_response.txt (Cursor / file agent read rag_query.txt)",
                        "local": "Structured output built from RAG prompt + PDF chunks",
                    }.get(llm_mode, f"Response via {llm_mode}"),
                    "questions_parsed": len(parsed),
                    "question_previews": [q["content"][:200] for q in parsed],
                })

                all_questions.extend(parsed)

            for i, q in enumerate(all_questions):
                q["order_index"] = i

            all_questions = filter_structural_duplicates(all_questions)
            skip_history = "local" in attempt_llm_modes
            if skip_history:
                logger.info(
                    "Dedup: skip_history=True (local template fallback — fixed stems vs history)"
                )
            unique_questions = await self.dedup.filter(
                all_questions,
                user_id,
                config.subject or "Mathematics",
                config.class_level or "10",
                document_id=config.document_id,
                skip_history=skip_history,
            )
            before_gate = len(unique_questions)
            unique_questions, topic_rejected_final = filter_questions_by_topic(
                unique_questions,
                locked_chapter=locked_chapter,
                lenient_fallback=settings.TOPIC_GATE_LENIENT_FALLBACK,
            )
            generation_log.append({
                "step": "dedup",
                "attempt": attempt,
                "parsed": len(all_questions),
                "unique_after_dedup": len(unique_questions),
                "prior_stems_excluded": len(exclude_stems),
            })
            generation_log.append(
                MultiAgentOrchestrator.validator_agent_log(
                    parsed=len(all_questions),
                    accepted=len(unique_questions),
                    rejected=len(topic_rejected_final),
                    dedup_in=before_gate,
                    dedup_out=len(unique_questions),
                )
            )
            if len(unique_questions) >= pool_n:
                break
            if attempt < max_attempts and self._can_regenerate():
                logger.warning(
                    "Only %d unique questions (need %d) — regeneration attempt %d",
                    len(unique_questions),
                    pool_n,
                    attempt + 1,
                )
                continue
            break

        # 7–9. Score → curate → textbook authenticity filter
        _, dominant_diff = self._resolve_generation_profile(config)
        slot_bands = get_slot_bands(
            len(unique_questions),
            ui_difficulty=dominant_diff,
            difficulty_distribution=config.difficulty_distribution,
        )
        author = resolve_author_style(instructions=config.instructions or "")
        from app.generation.full_hard_mode import is_full_hard_paper

        _full_hard = is_full_hard_paper(config.difficulty_distribution)
        slot_meta = get_slot_metadata(
            len(unique_questions),
            author,
            ui_difficulty=dominant_diff,
            locked_chapter=locked_chapter,
            full_hard=_full_hard,
            difficulty_distribution=config.difficulty_distribution,
        )
        from app.generation.topic_isolation import get_current_topic_state

        _ts_plan = get_current_topic_state() or {}
        _plan_arch = _ts_plan.get("semantic_plan_archetypes") or []
        _plan_cog = _ts_plan.get("semantic_plan_cognitive") or {}
        for _si, _sm in enumerate(slot_meta):
            _sn = int(_sm.get("slot") or (_si + 1))
            if _plan_cog.get(_sn):
                _sm["cognitive_type"] = _plan_cog[_sn]
            if _si < len(_plan_arch) and _plan_arch[_si]:
                _sm["archetype_id"] = _plan_arch[_si]
        scored = await self.quality.score_batch(
            unique_questions,
            slot_bands=slot_bands,
            ui_difficulty=dominant_diff,
            slot_metadata=slot_meta,
        )
        curated = self.quality.curate_batch(
            scored,
            author_instructions=config.instructions or "",
            ui_difficulty=dominant_diff,
        )

        if settings.ENABLE_PAPER_DEPENDENCY_GRAPH and locked_chapter:
            from app.generation.paper_dependency_graph import (
                apply_paper_dependency_enforcement,
                build_paper_dependency_plan,
                merge_dependency_into_slot_meta,
                plan_to_dict,
                validate_paper_dependency_chain,
            )
            from app.generation.paper_templates import resolve_paper_template

            _tmpl = resolve_paper_template(
                override=getattr(config, "paper_template", None),
                plan_template_id=_semantic_plan_template_id(),
                chapter=locked_chapter,
                subject=config.subject or "Mathematics",
                class_level=config.class_level or "10",
                question_count=config.total_questions,
                ui_difficulty=dominant_diff,
                full_hard=_full_hard,
            )
            dep_plan = build_paper_dependency_plan(
                chapter=locked_chapter,
                question_count=config.total_questions,
                slots=[],
                ui_difficulty=dominant_diff,
                full_hard=_full_hard,
                paper_template_id=_tmpl.id,
            )
            slot_meta = merge_dependency_into_slot_meta(slot_meta, dep_plan)
            curated = apply_paper_dependency_enforcement(curated, dep_plan)
            chain_report = validate_paper_dependency_chain(curated, dep_plan)
            if settings.ENABLE_CROSS_QUESTION_CONSISTENCY:
                from app.generation.cross_question_consistency import (
                    validate_cross_question_consistency,
                )

                xq_report = validate_cross_question_consistency(
                    curated, chapter=locked_chapter
                )
                generation_log.append({"step": "cross_question_numeric", **xq_report})
                chain_report["cross_question_ok"] = xq_report.get("cross_question_ok")
            generation_log.append(
                {"step": "paper_dependency", **plan_to_dict(dep_plan), **chain_report}
            )
            curated = await self.quality.score_batch(
                curated,
                slot_bands=slot_bands,
                ui_difficulty=dominant_diff,
                slot_metadata=slot_meta,
            )
            for i, q in enumerate(curated):
                if i < len(slot_meta):
                    q["slot_meta"] = slot_meta[i]
            if _full_hard:
                l5_slots = sum(
                    1 for m in slot_meta if (m.get("band") or "").upper() == "L5"
                )
                generation_log.append(
                    {
                        "step": "full_hard_L5_slots",
                        "l5_slot_count": l5_slots,
                        "required": len(curated),
                        "all_L5": l5_slots >= len(curated),
                    }
                )

        exclude_stems_final = list(
            dict.fromkeys(
                prior_stems + [q.get("content", "") for q in curated if q.get("content")]
            )
        )
        if settings.QUALITY_REGEN_ENABLED and last_task and last_context:
            final, regen_log = await self._ensure_quality_accepted(
                curated=curated,
                slot_meta=slot_meta,
                config=config,
                dominant_diff=dominant_diff,
                task=last_task,
                context=last_context,
                source_chunks=last_source_chunks,
                document_meta=rag_document_meta,
                exclude_stems=[s for s in exclude_stems_final if s],
                generation_log=generation_log,
                user_id=user_id,
            )
            generation_log.append({"step": "quality_regen", **regen_log})
        else:
            pool = []
            for i, q in enumerate(curated):
                meta = slot_meta[i] if i < len(slot_meta) else None
                if not self.quality.should_reject(
                    q, ui_difficulty=dominant_diff, slot_meta=meta
                ):
                    pool.append(q)
                elif settings.ENABLE_REJECTION_CORPUS and q.get("content"):
                    await record_rejection(
                        q,
                        user_id=user_id,
                        document_id=config.document_id,
                        chapter=locked_chapter,
                        slot_index=i,
                        slot_meta=meta or {},
                        source="quality_pool_reject",
                    )
            if len(pool) < pool_n:
                pool = sorted(
                    curated,
                    key=lambda q: q.get("combined_score", q.get("quality_score", 0)),
                    reverse=True,
                )
            if not pool and unique_questions:
                logger.warning(
                    "Dedup/quality left 0 questions — restoring %d unique parsed items",
                    len(unique_questions),
                )
                pool = unique_questions[:pool_n]
            from app.generation.generation_oversample import select_best_for_chapter

            final, oversample_meta = select_best_for_chapter(
                pool if pool else curated,
                delivery_n,
                chapter=locked_chapter,
                ui_difficulty=dominant_diff,
                slot_meta=slot_meta,
            )
            if is_oversample_active(delivery_n):
                generation_log.append(
                    {"step": "oversample_selection", **oversample_meta}
                )

        if required_theorems and final:
            final, coverage_report = enforce_coverage_before_delivery(
                final,
                curated,
                required_theorems,
                chapter=locked_chapter,
                target_count=config.total_questions,
            )
            generation_log.append({"step": "theorem_coverage", **coverage_report})
            if not coverage_report.get("meets_minimum"):
                logger.warning(
                    "Coverage weighted=%.0f%% cognitive=%.0f%% required=%.0f%% — missing: %s",
                    (coverage_report.get("weighted_coverage_score", 0) or 0) * 100,
                    (coverage_report.get("cognitive_diversity_score", 0) or 0) * 100,
                    (coverage_report.get("required_theorem_ratio", 0) or 0) * 100,
                    coverage_report.get("missing_theorems_weighted")
                    or coverage_report.get("missing_theorems"),
                )

        if len(final) < config.total_questions:
            logger.warning(
                "Delivering %d unique questions (%d requested). "
                "Prior stems blocked repeats — regenerate or edit rag_response.txt with new items.",
                len(final),
                config.total_questions,
            )

        if settings.ENABLE_GENERATION_MEMORY and final:
            try:
                await record_paper_memory(
                    final,
                    user_id=user_id,
                    subject=config.subject or "Mathematics",
                    class_level=config.class_level or "10",
                    document_id=config.document_id,
                    chapter=locked_chapter,
                    required_theorems=required_theorems,
                )
            except Exception as e:
                logger.warning("record_paper_memory failed: %s", e)

        if final:
            final = self._finalize_paper_delivery(
                final,
                config=config,
                locked_chapter=locked_chapter,
                dominant_diff=dominant_diff,
                full_hard=_full_hard,
                generation_log=generation_log,
            )

        generation_log.append({
            "step": "finalize",
            "count_requested": delivery_n,
            "count_pool": pool_n,
            "count_parsed": len(all_questions),
            "count_after_dedup": len(unique_questions),
            "count_delivered": len(final),
            "dedup_strict": True,
            "weak_in": weak_skills,
            "strong_in": strong_skills,
            "recent_combos_avoided": (gen_memory or {}).get("recent_combos", [])[:6],
        })
        logger.info(
            "Generated %d questions (requested %d, parsed %d)",
            len(final),
            config.total_questions,
            len(all_questions),
        )
        return final, generation_log

    def _finalize_paper_delivery(
        self,
        final: List[Dict[str, Any]],
        *,
        config: GenerationConfig,
        locked_chapter: str,
        dominant_diff: str,
        full_hard: bool,
        generation_log: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Renumber slots, enforce dependency wording, reject broken papers."""
        from app.generation.paper_integrity import (
            normalize_paper_slot_order,
            should_reject_paper_integrity,
            validate_paper_integrity,
        )

        final = normalize_paper_slot_order(final)

        from app.generation.paper_templates import resolve_paper_template

        _tmpl = resolve_paper_template(
            override=getattr(config, "paper_template", None),
            plan_template_id=_semantic_plan_template_id(),
            chapter=locked_chapter,
            subject=config.subject or "Mathematics",
            class_level=config.class_level or "10",
            question_count=config.total_questions,
            ui_difficulty=dominant_diff,
            full_hard=full_hard,
        )

        from app.generation.paper_repair import fill_missing_paper_slots, repair_paper_questions

        if len(final) < config.total_questions:
            if not self._local_fallback_allowed():
                raise RagAgentResponseMissing(
                    f"Paper has {len(final)} question(s) but {config.total_questions} required. "
                    "Provide a full rag_response.txt (ENABLE_LOCAL_LLM_FALLBACK is false)."
                )
            final = fill_missing_paper_slots(
                final,
                config.total_questions,
                chapter=locked_chapter,
                difficulty=dominant_diff,
            )
            final = normalize_paper_slot_order(final)

        final = repair_paper_questions(
            final,
            chapter=locked_chapter,
            re_enrich_figures=False,
            paper_template_id=_tmpl.id,
        )

        if settings.ENABLE_PAPER_DEPENDENCY_GRAPH and locked_chapter:
            from app.generation.paper_dependency_graph import (
                apply_paper_dependency_enforcement,
                build_paper_dependency_plan,
            )
            dep_plan = build_paper_dependency_plan(
                chapter=locked_chapter,
                question_count=config.total_questions,
                slots=[],
                ui_difficulty=dominant_diff,
                full_hard=full_hard,
                paper_template_id=_tmpl.id,
            )
            if dep_plan.enabled:
                final = apply_paper_dependency_enforcement(final, dep_plan)
                final = normalize_paper_slot_order(final)
                final = repair_paper_questions(
                    final,
                    chapter=locked_chapter,
                    re_enrich_figures=False,
                    paper_template_id=_tmpl.id,
                )

        if settings.ENABLE_FIGURE_GENERATION:
            final = self._prepare_figure_questions(final)

        if settings.ENABLE_CROSS_QUESTION_CONSISTENCY:
            from app.generation.cross_question_consistency import (
                validate_cross_question_consistency,
            )

            xq = validate_cross_question_consistency(final, chapter=locked_chapter)
            generation_log.append({"step": "cross_question_numeric_final", **xq})

        integrity = validate_paper_integrity(
            final,
            chapter=locked_chapter,
            expected_count=config.total_questions,
            paper_template_id=_tmpl.id,
        )
        generation_log.append(
            {"step": "paper_integrity", "paper_template_id": _tmpl.id, **integrity}
        )
        from app.generation.question_pipeline import finalize_questions_list

        if should_reject_paper_integrity(
            final,
            chapter=locked_chapter,
            expected_count=config.total_questions,
            paper_template_id=_tmpl.id,
        ):
            from app.generation.canonical_question_signature import (
                disambiguate_duplicate_signatures,
            )

            for q in final:
                q["locked_chapter"] = locked_chapter
            disambiguate_duplicate_signatures(final, chapter=locked_chapter)
            final = repair_paper_questions(
                final,
                chapter=locked_chapter,
                re_enrich_figures=False,
                paper_template_id=_tmpl.id,
            )
            integrity_retry = validate_paper_integrity(
                final,
                chapter=locked_chapter,
                expected_count=config.total_questions,
                paper_template_id=_tmpl.id,
            )
            generation_log.append(
                {
                    "step": "paper_integrity_retry",
                    "paper_template_id": _tmpl.id,
                    **integrity_retry,
                }
            )
            if not should_reject_paper_integrity(
                final,
                chapter=locked_chapter,
                expected_count=config.total_questions,
                paper_template_id=_tmpl.id,
            ):
                return finalize_questions_list(final)

            from app.generation.full_hard_mode import is_full_hard_paper

            final = self._salvage_paper_marks(
                final,
                chapter=locked_chapter,
                paper_template_id=_tmpl.id,
                full_hard=is_full_hard_paper(config.difficulty_distribution),
            )
            final = repair_paper_questions(
                final,
                chapter=locked_chapter,
                re_enrich_figures=False,
                paper_template_id=_tmpl.id,
            )
            integrity_salvage = validate_paper_integrity(
                final,
                chapter=locked_chapter,
                expected_count=config.total_questions,
                paper_template_id=_tmpl.id,
            )
            generation_log.append(
                {
                    "step": "paper_integrity_salvage",
                    "paper_template_id": _tmpl.id,
                    **integrity_salvage,
                }
            )
            if not should_reject_paper_integrity(
                final,
                chapter=locked_chapter,
                expected_count=config.total_questions,
                paper_template_id=_tmpl.id,
            ):
                return finalize_questions_list(final)

            flags = integrity_retry.get("paper_integrity_flags") or []
            generation_log.append(
                {
                    "step": "draft_before_reject",
                    "questions": final,
                    "flags": flags,
                }
            )
            if not getattr(settings, "PAPER_INTEGRITY_BLOCK_EXPORT", False):
                generation_log.append(
                    {
                        "step": "integrity_export_relaxed",
                        "flags": flags[:12],
                        "note": "Exported after background salvage; flags logged only.",
                    }
                )
                return finalize_questions_list(final)
            raise ValueError(
                "Paper integrity failed — refusing to export: "
                + "; ".join(flags[:8])
            )

        return finalize_questions_list(final)

    def _salvage_paper_marks(
        self,
        questions: List[Dict[str, Any]],
        *,
        chapter: str,
        paper_template_id: str = "",
        full_hard: bool = False,
    ) -> List[Dict[str, Any]]:
        """Clamp marks to blueprint caps and clear fixable quality flags (background repair)."""
        from app.generation.chapter_paper_quality import (
            annotate_chapter_paper_quality,
            normalize_chapter_paper_marks,
        )

        if not chapter:
            return questions
        normalize_chapter_paper_marks(
            questions, chapter=chapter, full_hard=full_hard
        )
        for q in questions:
            if q.get("marks_normalized"):
                q["chapter_quality_flags"] = [
                    f
                    for f in (q.get("chapter_quality_flags") or [])
                    if not f.startswith("marks_inflated")
                    and not f.startswith("marks_deflated")
                ]
        annotate_chapter_paper_quality(questions, chapter=chapter)
        return questions

    def _quality_regen_use_cursor(self) -> bool:
        return bool(
            settings.QUALITY_REGEN_USE_CURSOR and settings.RAG_FILE_AGENT_ENABLED
        )

    async def _regenerate_slot_raw(
        self,
        *,
        prompt: str,
        slot_index: int,
        context: str,
        document_meta: Optional[Dict[str, str]],
        exclude_stems: List[str],
        reject_feedback: str,
        rejected_stem: str,
    ) -> tuple[str, str]:
        """
        Regenerate one slot. Prefer Cursor (rag_query → rag_response) when enabled.
        Returns (raw_json_text, source) where source is 'cursor' or 'llm'.
        """
        if self._quality_regen_use_cursor():
            single = await request_rag_slot_regeneration(
                context,
                prompt,
                slot_index=slot_index,
                document_meta=document_meta,
                retrieval_query="QUALITY REGENERATION slot fix",
                exclude_prior_stems=exclude_stems,
                reject_feedback=reject_feedback,
                rejected_stem=rejected_stem,
            )
            if single:
                return single, "cursor"
            if not self._local_fallback_allowed():
                raise RagAgentResponseMissing(
                    f"Slot {slot_index + 1} quality regen: Cursor did not update rag_response.txt in time."
                )
            logger.warning(
                "Cursor slot regen timed out for slot %d — falling back to LLM",
                slot_index + 1,
            )
        raw = await self._generate_regen_raw(
            prompt,
            slot_index=slot_index,
            context=context,
            locked_chapter=(document_meta or {}).get("locked_chapter", ""),
            filename=(document_meta or {}).get("filename", ""),
        )
        return raw, "llm"

    @staticmethod
    def _cloud_llm_allowed() -> bool:
        """Skip cloud APIs when file-agent-only mode is on."""
        if settings.RAG_FILE_AGENT_ENABLED and settings.RAG_FILE_AGENT_ONLY:
            return False
        return True

    @staticmethod
    def _cloud_provider_order() -> List[str]:
        """Provider try-order; PRIMARY_LLM (groq | gemini | openai) is tried first."""
        primary = (getattr(settings, "PRIMARY_LLM", None) or "gemini").strip().lower()
        known = ("groq", "gemini", "openai")
        if primary not in known:
            primary = "gemini"
        return [primary] + [p for p in known if p != primary]

    @staticmethod
    def _local_fallback_allowed() -> bool:
        """Structured local_llm templates — off by default; use Cursor / cloud AI only."""
        return bool(getattr(settings, "ENABLE_LOCAL_LLM_FALLBACK", False))

    async def _safe_groq_generate(self, prompt: str) -> Optional[str]:
        if not settings.GROQ_API_KEY:
            return None
        for max_chars in (9000, 6000, 4500):
            try:
                compact = self._trim_prompt_for_groq(prompt, max_chars=max_chars)
                return await self._groq_generate(compact)
            except Exception as e:
                err = str(e).lower()
                if "413" in err or "too large" in err or "rate_limit" in err:
                    logger.warning(
                        "Groq prompt too large at %d chars — retrying smaller",
                        max_chars,
                    )
                    continue
                logger.warning("Groq unavailable (%s); using fallback", e)
                return None
        return None

    async def _generate_via_cloud_llm(
        self, prompt: str
    ) -> Optional[tuple[str, str]]:
        """Try cloud LLMs in PRIMARY_LLM order (default: groq → gemini → openai)."""
        for provider in self._cloud_provider_order():
            if provider == "groq" and settings.GROQ_API_KEY:
                out = await self._safe_groq_generate(prompt)
                if out:
                    logger.info("Question generation via Groq (%s)", settings.GROQ_MODEL)
                    return out, "groq"
            elif provider == "gemini" and settings.GOOGLE_GEMINI_API_KEY:
                return await self._gemini_generate(prompt), "gemini"
            elif provider == "openai" and settings.OPENAI_API_KEY:
                return await self._openai_generate(prompt), "openai"
        return None

    async def _generate_regen_raw(
        self,
        prompt: str,
        *,
        slot_index: int = 0,
        context: str = "",
        task: Optional[Dict[str, Any]] = None,
        locked_chapter: str = "",
        filename: str = "",
    ) -> str:
        """Single-question regeneration — file agent / local only when RAG_FILE_AGENT_ONLY."""
        suffix = "\n\nReturn ONLY a JSON array with ONE object. Start with [ end with ]."
        if settings.has_cloud_llm():
            cloud = await self._generate_via_cloud_llm(prompt + suffix)
            if cloud:
                return cloud[0]
            if settings.OLLAMA_ENABLED and self._local_fallback_allowed():
                out = await self._ollama_generate(prompt)
                if out:
                    return out
        if not self._local_fallback_allowed():
            raise RagAgentResponseMissing(
                f"Slot {slot_index + 1} regen requires Cursor rag_response.txt (local fallback disabled)."
            )
        task_stub = task or {
            "type": "FigureBased",
            "difficulty": "hard",
            "bloom_level": "Analyze",
            "count": 1,
        }
        return build_local_slot_response(
            context,
            task_stub,
            slot_index,
            locked_chapter=locked_chapter,
            filename=filename,
        )

    async def _ensure_quality_accepted(
        self,
        *,
        curated: List[Dict[str, Any]],
        slot_meta: List[Dict[str, Any]],
        config: GenerationConfig,
        dominant_diff: str,
        task: Dict[str, Any],
        context: str,
        source_chunks: List[str],
        document_meta: Optional[Dict[str, str]],
        exclude_stems: List[str],
        generation_log: List[Dict[str, Any]],
        user_id: str = "",
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fill every slot with a quality-accepted question; regenerate rejected slots.
        """
        from app.generation.topic_isolation import get_current_topic_state

        locked_chapter = (get_current_topic_state() or {}).get("locked_chapter", "generic")
        n = config.total_questions
        bands = get_slot_bands(
            n,
            ui_difficulty=dominant_diff,
            difficulty_distribution=config.difficulty_distribution,
        )
        slots: List[Optional[Dict[str, Any]]] = [None] * n
        regen_attempts = 0
        accepted_first_pass = 0
        used_stems: set[str] = set()

        from app.generation.paper_integrity import question_matches_slot_role
        from app.generation.paper_templates import resolve_paper_template
        from app.generation.full_hard_mode import is_full_hard_paper

        _slot_tmpl = resolve_paper_template(
            override=getattr(config, "paper_template", None),
            plan_template_id=_semantic_plan_template_id(),
            chapter=locked_chapter,
            subject=config.subject or "Mathematics",
            class_level=config.class_level or "10",
            question_count=n,
            ui_difficulty=dominant_diff,
            full_hard=is_full_hard_paper(config.difficulty_distribution),
        )

        def _stem_key(text: str) -> str:
            return (text or "").strip().lower()[:240]

        def _slot_already_used(q: Dict[str, Any]) -> bool:
            return _stem_key(q.get("content") or "") in used_stems

        def _role_ok(i: int, q: Dict[str, Any]) -> bool:
            return question_matches_slot_role(
                q,
                i + 1,
                chapter=locked_chapter,
                paper_template_id=_slot_tmpl.id,
            )

        def _pick_for_slot(i: int, pool: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            for j, cand in enumerate(pool):
                if _role_ok(i, cand) and not _slot_already_used(cand):
                    return pool.pop(j)
            return None

        def _place_in_slot(
            i: int, q: Dict[str, Any], meta: Optional[Dict[str, Any]] = None
        ) -> None:
            from app.generation.paper_repair import repair_slot_by_number

            q = repair_slot_by_number(
                q, i + 1, chapter=locked_chapter
            )
            slots[i] = dict(q)
            slots[i]["order_index"] = i
            slots[i]["slot_number"] = i + 1
            slots[i]["locked_chapter"] = locked_chapter
            if meta:
                for key in ("archetype_id", "cognitive_type", "slot_archetype"):
                    if meta.get(key) and not slots[i].get(key):
                        slots[i][key] = meta[key]
            used_stems.add(_stem_key(q.get("content") or ""))

        # Place curated items by slot_number when present (not always curated[0] → slot 0)
        unassigned: List[Dict[str, Any]] = []
        for q in curated:
            sn = q.get("slot_number")
            if sn is not None and 1 <= int(sn) <= n:
                idx = int(sn) - 1
                meta = slot_meta[idx] if idx < len(slot_meta) else {"slot": idx + 1}
                if slots[idx] is not None:
                    unassigned.append(q)
                    continue
                if (
                    not self.quality.should_reject(
                        q, ui_difficulty=dominant_diff, slot_meta=meta
                    )
                    and not _slot_already_used(q)
                    and _role_ok(idx, q)
                ):
                    _place_in_slot(idx, q, meta)
                    accepted_first_pass += 1
                else:
                    unassigned.append(q)
                    if settings.ENABLE_REJECTION_CORPUS and q.get("content"):
                        await record_rejection(
                            q,
                            user_id=user_id,
                            document_id=config.document_id,
                            chapter=locked_chapter,
                            slot_index=idx,
                            slot_meta=meta,
                            source="quality_first_pass",
                        )
            else:
                unassigned.append(q)

        for i in range(n):
            if slots[i] is not None:
                continue
            if not unassigned:
                break
            meta = slot_meta[i] if i < len(slot_meta) else {"slot": i + 1}
            q = _pick_for_slot(i, unassigned)
            if q is None:
                break
            if not self.quality.should_reject(
                q, ui_difficulty=dominant_diff, slot_meta=meta
            ) and not _slot_already_used(q) and _role_ok(i, q):
                _place_in_slot(i, q, meta)
                accepted_first_pass += 1
            elif settings.ENABLE_REJECTION_CORPUS and q.get("content"):
                await record_rejection(
                    q,
                    user_id=user_id,
                    document_id=config.document_id,
                    chapter=locked_chapter,
                    slot_index=i,
                    slot_meta=meta,
                    source="quality_first_pass",
                )

        for i in range(n):
            if slots[i] is not None:
                continue
            meta = slot_meta[i] if i < len(slot_meta) else {"slot": i + 1, "band": bands[i]}
            band = bands[i] if i < len(bands) else meta.get("band", "L3")
            rejected = curated[i] if i < len(curated) else {}
            reject_stem = (rejected.get("content") or "") if rejected else ""

            for attempt in range(1, settings.QUALITY_REGEN_MAX_PER_SLOT + 1):
                candidate = try_auto_repair(dict(rejected), meta)
                scored = await self.quality.score_batch(
                    [candidate],
                    slot_bands=[band],
                    ui_difficulty=dominant_diff,
                    slot_metadata=[meta],
                )
                candidate = self.quality.curate_batch(
                    scored,
                    author_instructions=config.instructions or "",
                    ui_difficulty=dominant_diff,
                )[0]
                if not self.quality.should_reject(
                    candidate, ui_difficulty=dominant_diff, slot_meta=meta
                ):
                    _place_in_slot(i, candidate, meta)
                    candidate["quality_regen_attempts"] = attempt
                    logger.info(
                        "Slot %d accepted after auto-repair (attempt %d)", i + 1, attempt
                    )
                    break

                feedback = collect_rejection_feedback(candidate)
                if settings.ENABLE_REJECTION_CORPUS:
                    await record_rejection(
                        candidate,
                        user_id=user_id,
                        document_id=config.document_id,
                        chapter=locked_chapter,
                        slot_index=i,
                        slot_meta=meta,
                        feedback=feedback,
                        source="quality_regen",
                    )
                reject_stem_now = reject_stem or (candidate.get("content") or "")
                prompt = build_cursor_slot_regen_question(
                    slot_index=i,
                    slot_meta=meta,
                    slot_band=band,
                    context=context,
                    task=task,
                    reject_feedback=feedback,
                    rejected_stem=reject_stem_now,
                    exclude_stems=exclude_stems,
                    ui_difficulty=dominant_diff,
                    locked_chapter=locked_chapter,
                )
                try:
                    raw, regen_source = await self._regenerate_slot_raw(
                        prompt=prompt,
                        slot_index=i,
                        context=context,
                        document_meta=document_meta,
                        exclude_stems=exclude_stems,
                        reject_feedback=feedback,
                        rejected_stem=reject_stem_now,
                    )
                except Exception as e:
                    if not self._local_fallback_allowed():
                        logger.error(
                            "Slot %d regen failed (%s) — Cursor agent required",
                            i + 1,
                            e,
                        )
                        rejected = candidate
                        continue
                    logger.warning(
                        "Slot %d regen failed (%s); using local fallback",
                        i + 1,
                        e,
                    )
                    raw = await self._generate_regen_raw(
                        prompt,
                        slot_index=i,
                        context=context,
                        task=task,
                        locked_chapter=locked_chapter,
                        filename=(document_meta or {}).get("filename", ""),
                    )
                    regen_source = "local_fallback"
                regen_attempts += 1
                parsed = self._parse_llm_output(raw, task, config, source_chunks)
                if not parsed:
                    rejected = candidate
                    continue
                candidate = parsed[0]
                for key in ("archetype_id", "cognitive_type"):
                    if meta.get(key) and not candidate.get(key):
                        candidate[key] = meta[key]
                if _slot_already_used(candidate):
                    if self._local_fallback_allowed():
                        logger.warning(
                            "Slot %d: regen returned duplicate stem — trying local template",
                            i + 1,
                        )
                        raw_fb = build_local_slot_response(
                            context,
                            task,
                            i,
                            locked_chapter=locked_chapter,
                            filename=(document_meta or {}).get("filename", ""),
                        )
                        parsed_fb = self._parse_llm_output(
                            raw_fb, task, config, source_chunks
                        )
                        if not parsed_fb or _slot_already_used(parsed_fb[0]):
                            rejected = candidate
                            continue
                        candidate = parsed_fb[0]
                    else:
                        rejected = candidate
                        continue
                candidate["order_index"] = i
                if (
                    task.get("type") == QuestionType.FIGURE_BASED
                    and settings.ENABLE_FIGURE_GENERATION
                ):
                    attached = await self._attach_figures([candidate])
                    if attached:
                        candidate = attached[0]
                scored = await self.quality.score_batch(
                    [candidate],
                    slot_bands=[band],
                    ui_difficulty=dominant_diff,
                    slot_metadata=[meta],
                )
                candidate = self.quality.curate_batch(
                    scored,
                    author_instructions=config.instructions or "",
                    ui_difficulty=dominant_diff,
                )[0]
                if (
                    not self.quality.should_reject(
                        candidate, ui_difficulty=dominant_diff, slot_meta=meta
                    )
                    and _role_ok(i, candidate)
                ):
                    candidate["quality_regen_attempts"] = attempt
                    candidate["quality_regen_source"] = regen_source
                    _place_in_slot(i, candidate, meta)
                    logger.info(
                        "Slot %d accepted after %s regeneration (attempt %d)",
                        i + 1,
                        regen_source,
                        attempt,
                    )
                    break
                rejected = candidate
                reject_stem = candidate.get("content") or reject_stem

        for i in range(n):
            if slots[i] is not None:
                continue
            if i < len(curated) and curated[i].get("content"):
                q_be = curated[i]
                if (
                    not _slot_already_used(q_be)
                    and _role_ok(i, q_be)
                ):
                    _place_in_slot(i, q_be, meta)
                    logger.warning(
                        "Slot %d: using best-effort curated item after max regen attempts",
                        i + 1,
                    )
                continue
            if self._local_fallback_allowed():
                try:
                    raw = build_local_slot_response(
                        context,
                        task,
                        i,
                        locked_chapter=locked_chapter,
                        filename=(document_meta or {}).get("filename", ""),
                    )
                    parsed_fb = self._parse_llm_output(raw, task, config, source_chunks)
                    if parsed_fb:
                        slots[i] = parsed_fb[0]
                        slots[i]["order_index"] = i
                        slots[i]["quality_regen_source"] = "local_slot_template"
                        logger.warning(
                            "Slot %d: filled with chapter slot template %d",
                            i + 1,
                            i,
                        )
                except Exception as e:
                    logger.warning("Slot %d local template fallback failed: %s", i + 1, e)
            else:
                logger.error(
                    "Slot %d empty — Cursor must supply rag_response.txt (no local fallback)",
                    i + 1,
                )

        final = [slots[i] for i in range(n) if slots[i] is not None]
        log = {
            "accepted_first_pass": accepted_first_pass,
            "regen_attempts": regen_attempts,
            "slots_filled": len(final),
            "slots_requested": n,
        }
        generation_log.append(
            {
                "step": "quality_regen_detail",
                "slots": [
                    {
                        "slot": i + 1,
                        "accepted": slots[i] is not None,
                        "attempts": slots[i].get("quality_regen_attempts") if slots[i] else None,
                    }
                    for i in range(n)
                ],
            }
        )
        return final, log

    def _build_generation_plan(
        self, config: GenerationConfig, file_agent_mode: bool = False
    ) -> List[Dict]:
        """Distribute total_questions across types/difficulties/bloom levels."""
        types = config.question_types
        total = config.total_questions

        # File-agent mode: ONE step only — one rag_query / one rag_response for whole paper
        if file_agent_mode:
            from app.generation.generation_oversample import pool_question_count

            difficulty, bloom_level = self._resolve_generation_profile(config)
            pool = pool_question_count(total)
            return [{
                "type": types[0],
                "all_types": types,
                "difficulty": difficulty,
                "bloom_level": bloom_level,
                "count": pool,
                "delivery_count": total,
            }]

        plan = []
        total = config.total_questions
        per_type = max(1, total // len(types))
        remainder = total - per_type * len(types)

        diff_dist = config.difficulty_distribution
        bloom_levels = config.bloom_levels

        for i, qtype in enumerate(types):
            count = per_type + (1 if i < remainder else 0)
            # Distribute difficulty
            easy_n = max(1, round(count * diff_dist.easy / 100))
            medium_n = max(1, round(count * diff_dist.medium / 100))
            hard_n = max(0, count - easy_n - medium_n)

            for difficulty, n in [("easy", easy_n), ("medium", medium_n), ("hard", hard_n)]:
                if n <= 0:
                    continue
                bloom = bloom_levels[i % len(bloom_levels)]
                plan.append({
                    "type": qtype,
                    "difficulty": difficulty,
                    "bloom_level": bloom,
                    "count": n,
                })
        return plan

    @staticmethod
    def _resolve_generation_profile(config: GenerationConfig) -> Tuple[str, Any]:
        """Pick dominant difficulty and a bloom level suited to that difficulty."""
        dd = config.difficulty_distribution
        easy, medium, hard = dd.easy, dd.medium, dd.hard
        # File-agent single batch: bias to hardest tier with meaningful weight (textbook HOTS)
        if hard >= 90 and (easy + medium) <= 10:
            difficulty = "hard"
        elif hard >= 25 or (hard >= easy and hard >= medium):
            difficulty = "hard"
        elif medium >= easy:
            difficulty = "medium"
        elif easy >= medium and easy >= hard:
            difficulty = "easy"
        else:
            difficulty = "medium"

        blooms = config.bloom_levels or []
        bloom_names = [
            b.value if hasattr(b, "value") else str(b) for b in blooms
        ]
        if difficulty == "hard":
            for preferred in ("Analyze", "Apply", "Evaluate", "Understand", "Remember"):
                if preferred in bloom_names:
                    from app.schemas import BloomLevel
                    return difficulty, BloomLevel(preferred)
            from app.schemas import BloomLevel
            return difficulty, BloomLevel.APPLY
        if bloom_names:
            from app.schemas import BloomLevel
            return difficulty, blooms[0]
        from app.schemas import BloomLevel
        return difficulty, BloomLevel.REMEMBER

    @staticmethod
    def _build_rag_document_meta(
        config: GenerationConfig,
        document_meta: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Metadata written into rag_query.txt so the file agent matches the selected PDF."""
        meta: Dict[str, str] = {"document_id": config.document_id}
        if document_meta:
            for key in ("filename", "subject", "class_level"):
                if document_meta.get(key):
                    meta[key] = str(document_meta[key])
        if config.subject and "subject" not in meta:
            meta["subject"] = config.subject
        if config.class_level and "class_level" not in meta:
            meta["class_level"] = config.class_level
        if config.topic_focus:
            meta["topic_focus"] = config.topic_focus
        if config.exclude_topics:
            meta["exclude_topics"] = config.exclude_topics
        if config.instructions:
            meta["instructions"] = config.instructions
        return meta

    def _build_query(
        self,
        task: Dict,
        config: GenerationConfig,
        document_meta: Optional[Dict[str, Any]] = None,
        *,
        context: str = "",
    ) -> str:
        """Semantic search query — dynamic from selected document and exam level."""
        profile = build_content_profile(
            topic_focus=config.topic_focus or "",
            filename=(document_meta or {}).get("filename", ""),
            context=context,
            subject=config.subject or (document_meta or {}).get("subject", ""),
            class_level=config.class_level or (document_meta or {}).get("class_level", ""),
            instructions=config.instructions or "",
            difficulty=task.get("difficulty", "medium"),
        )
        return build_rag_retrieval_query(
            task=task,
            profile=profile,
            config_topic_focus=config.topic_focus or "",
            config_instructions=config.instructions or "",
        )

    @staticmethod
    def _has_llm_key() -> bool:
        return settings.has_cloud_llm()

    @staticmethod
    def _can_regenerate() -> bool:
        return bool(
            settings.GOOGLE_GEMINI_API_KEY
            or settings.OPENAI_API_KEY
            or settings.GROQ_API_KEY
            or settings.OLLAMA_ENABLED
            or settings.RAG_FILE_AGENT_ENABLED
        )

    async def _generate_raw_response(
        self,
        prompt: str,
        context: str,
        task: Dict,
        *,
        document_meta: Optional[Dict[str, str]] = None,
        retrieval_query: str = "",
        exclude_prior_stems: Optional[List[str]] = None,
        generation_num: int = 1,
        generation_attempt: int = 1,
    ) -> tuple[str, str]:
        """
        Prompt in → structured JSON out.
        When RAG file agent is enabled, use it first (writes rag_query.txt, waits for rag_response.txt).
        Otherwise: cloud API → Ollama → local builder.
        """
        from app.generation.topic_isolation import get_current_topic_state

        if settings.RAG_FILE_AGENT_ENABLED:
            from app.generation.topic_isolation import response_matches_current_topic

            stale_response = not response_matches_current_topic()
            if stale_response:
                logger.warning(
                    "rag_response may be stale or cross-chapter — waiting for fresh Cursor response"
                )
            meta = document_meta or {}
            ts = dict(get_current_topic_state() or {})
            meta = document_meta or {}
            ts["question_count"] = int(meta.get("question_count") or (task or {}).get("count") or 5)
            ts["full_hard"] = str(meta.get("full_hard", "0")).lower() in ("1", "true", "yes")
            profile = build_content_profile(
                topic_focus=meta.get("topic_focus", ""),
                filename=meta.get("filename", ""),
                context=context[:1200],
                subject=meta.get("subject", ""),
                class_level=meta.get("class_level", ""),
                instructions=meta.get("instructions", ""),
                difficulty=task.get("difficulty", "medium"),
            )
            dynamic_retrieval = build_rag_retrieval_query(
                task=task,
                profile=profile,
                config_topic_focus=meta.get("topic_focus", ""),
                config_instructions=meta.get("instructions", ""),
            )
            max_tries = (
                settings.RAG_FILE_MAX_RETRIES
                if settings.RAG_FILE_AGENT_ONLY
                else 1
            )
            file_answer = None
            for try_num in range(1, max_tries + 1):
                file_answer = await request_rag_file_response(
                    context,
                    prompt,
                    document_meta=document_meta,
                    retrieval_query=retrieval_query or dynamic_retrieval,
                    exclude_prior_stems=exclude_prior_stems,
                    topic_state=ts,
                    generation_attempt=try_num if try_num > 1 else generation_attempt,
                    generation_num=generation_num,
                )
                if file_answer:
                    return file_answer, "rag_file_agent"
                if try_num < max_tries:
                    logger.warning(
                        "RAG file agent attempt %d/%d — still waiting for rag_response.txt",
                        try_num,
                        max_tries,
                    )
            if settings.RAG_FILE_AGENT_ONLY:
                raise RagAgentResponseMissing(
                    "Cursor agent did not write rag_response.txt in time. "
                    "Enable Cursor Hooks, keep an Agent chat open, and ensure "
                    ".cursor/rules/rag-response-agent.mdc is active."
                )

        if self._cloud_llm_allowed():
            cloud = await self._generate_via_cloud_llm(prompt)
            if cloud:
                return cloud
        if settings.OLLAMA_ENABLED and self._cloud_llm_allowed():
            ollama_out = await self._ollama_generate(prompt)
            if ollama_out:
                return ollama_out, "ollama"

        if not self._local_fallback_allowed():
            raise RagAgentResponseMissing(
                "RAG file agent is required; local question builder is disabled."
            )

        logger.info("Using structured local generator (RAG context → JSON output)")
        ch = (get_current_topic_state() or {}).get("locked_chapter", "")
        fn = (document_meta or {}).get("filename", "") if document_meta else ""
        return (
            build_local_response(
                context,
                task,
                locked_chapter=ch,
                filename=fn,
            ),
            "local",
        )

    async def _ollama_generate(self, prompt: str) -> str | None:
        """Call Ollama with the full RAG prompt (install Ollama + pull model for free local AI)."""
        import httpx

        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                r = await client.post(
                    url,
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt + "\n\nReturn ONLY a valid JSON array. Start with [ and end with ].",
                        "stream": False,
                        "options": {"temperature": 0.75, "num_predict": 4096},
                    },
                )
                if r.status_code != 200:
                    logger.warning(f"Ollama returned {r.status_code}")
                    return None
                data = r.json()
                text = (data.get("response") or "").strip()
                if "[" in text and "]" in text:
                    logger.info("Ollama generated response from RAG prompt")
                    return text
                return None
        except Exception as e:
            logger.warning(f"Ollama not available ({e}); using structured local generator")
            return None

    async def _gemini_generate(self, prompt: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config=genai.types.GenerationConfig(
                temperature=0.85,
                max_output_tokens=8192,
            ),
        )
        response = model.generate_content(prompt)
        return response.text

    async def _openai_generate(self, prompt: str) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=8192,
        )
        return response.choices[0].message.content

    @staticmethod
    def _trim_prompt_for_groq(prompt: str, max_chars: int = 9000) -> str:
        """Groq on-demand TPM caps large RAG prompts — keep head + output contract tail."""
        if len(prompt) <= max_chars:
            return prompt
        markers = ("OUTPUT CONTRACT:", "QUESTION:", "EXERCISE BLUEPRINT")
        cut = -1
        for m in markers:
            idx = prompt.rfind(m)
            if idx > cut:
                cut = idx
        if cut > 0:
            head_budget = min(6000, max_chars // 3)
            tail_budget = max_chars - head_budget - 80
            return (
                prompt[:head_budget]
                + "\n\n[Context trimmed for Groq TPM — syllabus rules preserved below.]\n\n"
                + prompt[cut : cut + tail_budget]
            )
        return prompt[: max_chars - 80] + "\n\n[Prompt trimmed for Groq TPM.]"

    async def _groq_generate(self, prompt: str) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        if len(prompt) > 9000:
            logger.info("Groq prompt trimmed %d → %d chars", len(prompt), len(prompt[:9000]))
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=2400,
        )
        return response.choices[0].message.content

    def _parse_llm_output(
        self,
        raw: str,
        task: Dict,
        config: GenerationConfig,
        source_chunks: List[str],
    ) -> List[Dict]:
        """Parse JSON array from LLM output."""
        questions = []
        try:
            # Extract JSON block
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1 or end == 0:
                logger.warning("No JSON array found in LLM output")
                return []
            json_str = raw[start:end]
            items = json.loads(json_str)

            marks_map = {
                "MCQ": 1.0, "ShortAnswer": 3.0, "LongAnswer": 5.0,
                "FigureBased": 4.0, "TrueFalse": 1.0, "FillBlank": 1.0,
                "AssertionReason": 2.0, "MatchColumn": 3.0, "CaseStudy": 6.0,
            }
            if config.marks_per_type:
                marks_map.update(config.marks_per_type.model_dump())

            qtype_str = task["type"].value if hasattr(task["type"], "value") else str(task["type"])

            task_diff = task["difficulty"]
            for order_index, item in enumerate(items):
                item_type = item.get("type")
                if item_type:
                    qtype_str = item_type if isinstance(item_type, str) else str(item_type)
                from app.generation.question_text import ensure_plain_text

                content = ensure_plain_text(
                    item.get("question", item.get("content", "")).strip()
                )
                if not content:
                    continue
                if isinstance(item.get("figure_spec"), dict) and not item.get("figure_type"):
                    item["figure_type"] = item["figure_spec"].get("type", "labeled_diagram")
                marks = item.get("marks", marks_map.get(qtype_str, 1.0))
                if task_diff == "hard" and qtype_str == "FigureBased":
                    marks = max(float(marks), 5.0)
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                slot_number = None
                raw_id = item.get("id")
                if raw_id is not None and str(raw_id).strip().isdigit():
                    slot_number = int(str(raw_id).strip())
                arch_id = (item.get("archetype_id") or item.get("slot_archetype") or "").strip()
                cog = (item.get("cognitive_type") or "").strip()
                q = {
                    "id": str(uuid.uuid4()),
                    "slot_number": slot_number,
                    "archetype_id": arch_id or None,
                    "cognitive_type": cog or None,
                    "content": content,
                    "question_type": qtype_str,
                    "difficulty": task_diff,
                    "bloom_level": task["bloom_level"].value if hasattr(task["bloom_level"], "value") else task["bloom_level"],
                    "options": item.get("options"),
                    "correct_answer": ensure_plain_text(
                        str(
                            item.get("answer", item.get("correct_answer", ""))
                            or ""
                        ).strip()
                    ),
                    "explanation": ensure_plain_text(
                        str(item.get("explanation", "") or "").strip()
                    ),
                    "marks": marks,
                    "figure_spec": item.get("figure_spec"),
                    "figure_type": item.get("figure_type"),
                    "content_hash": content_hash,
                    "source_chunks": source_chunks,
                    "quality_score": 0.0,
                    "order_index": (slot_number - 1)
                    if slot_number and slot_number >= 1
                    else order_index,
                }
                from app.generation.question_pipeline import finalize_question_dict

                questions.append(finalize_question_dict(q))
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nRaw: {raw[:500]}")
        return questions

    # Two-letter tokens from English/OR stems — not geometry point names
    _NON_POINT_BIGRAMS = frozenset(
        {
            "OR", "IF", "TO", "IT", "IS", "AN", "AS", "AT", "BE", "BY", "DO",
            "GO", "HE", "ME", "NO", "SO", "UP", "US", "WE", "AM", "CM", "MM",
            "KM",
        }
    )

    @staticmethod
    def _extract_point_labels_from_text(text: str) -> set[str]:
        """Single standard uppercase letters A–Z used as point names in the stem."""
        labels: set[str] = set()
        if not text:
            return labels
        # Avoid treating **OR** branch markers as point R (and similar noise)
        text = re.sub(r"\*\*OR\*\*", " ", text, flags=re.I)
        patterns = [
            r"(?:centre|center)\s+([A-Z])\b",
            r"\bpoint\s+([A-Z])\b",
            r"\bat\s+([A-Z])\b",
            r"\bthrough\s+(?:point\s+)?([A-Z])\b",
            r"\b(?:radius|tangent|segment)\s+([A-Z])([A-Z])\b",
            r"\b([A-Z])([A-Z])\s+(?:is|are)\b",
            r"\b([A-Z])([A-Z])\s+and\s+([A-Z])([A-Z])\b",
            r"\b([A-Z])\s*=\s*\d",
            r"\b(?:angle|triangle)\s+([A-Z])([A-Z])([A-Z])\b",
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                for g in m.groups():
                    if g and len(g) == 1 and g.isalpha():
                        labels.add(g.upper())
                    elif g and len(g) == 2 and g.isalpha():
                        labels.add(g[0].upper())
                        labels.add(g[1].upper())
        for pair in re.finditer(r"\b([A-Z])([A-Z])\b", text):
            bigram = pair.group(0).upper()
            if bigram in QuestionGenerator._NON_POINT_BIGRAMS:
                continue
            labels.add(pair.group(1))
            labels.add(pair.group(2))
        return labels

    @staticmethod
    def _point_labels_in_figure_spec(spec: Dict) -> set[str]:
        found: set[str] = set()
        for el in spec.get("elements") or []:
            lbl = el.get("label") or ""
            if len(lbl) == 1 and lbl.isalpha():
                found.add(lbl.upper())
            for key in ("from", "to"):
                v = el.get(key)
                if v and len(str(v)) == 1 and str(v).isalpha():
                    found.add(str(v).upper())
        return found

    @staticmethod
    def _infer_point_position(
        letter: str,
        elements: List[Dict],
        centre_lbl: Optional[str],
    ) -> str:
        """Guess centre / outside / on_circle from segment graph."""
        if letter == centre_lbl or (not centre_lbl and letter == "O"):
            return "centre"
        segs = [
            el
            for el in elements
            if (el.get("shape") or "").lower() == "segment"
        ]
        neighbors: set[str] = set()
        for el in segs:
            frm, to = el.get("from"), el.get("to")
            if frm == letter and to:
                neighbors.add(str(to))
            elif to == letter and frm:
                neighbors.add(str(frm))
        if centre_lbl and centre_lbl in neighbors and len(neighbors) == 1:
            return "centre"
        on_circle_neighbors = {n for n in neighbors if n != centre_lbl}
        if len(on_circle_neighbors) >= 2 and centre_lbl not in neighbors:
            return "outside"
        if len(on_circle_neighbors) == 1 and centre_lbl not in neighbors:
            return "outside"
        return "on_circle"

    def _sync_figure_labels(self, content: str, spec: Dict) -> Dict:
        """Ensure every A–Z point named in the question exists in figure_spec.elements."""
        spec = dict(spec)
        needed = self._extract_point_labels_from_text(content)
        present = self._point_labels_in_figure_spec(spec)
        missing = needed - present
        if not missing:
            return spec
        elements = list(spec.get("elements") or [])
        centre_lbl = next(
            (
                el.get("label")
                for el in elements
                if (el.get("position") or "").lower() in ("centre", "center")
            ),
            None,
        )
        for letter in sorted(missing):
            if letter == centre_lbl:
                continue
            pos = self._infer_point_position(letter, elements, centre_lbl)
            elements.append({"shape": "point", "label": letter, "position": pos})
            logger.warning(
                "Added missing point %s to figure_spec (position=%s)", letter, pos
            )
        spec["elements"] = elements
        labels_map = dict(spec.get("labels") or {})
        for letter in missing:
            labels_map.setdefault(letter, letter)
        spec["labels"] = labels_map
        return spec

    @staticmethod
    def _ensure_centre_to_external_segment(content: str, spec: Dict) -> Dict:
        """Draw dashed O–P when stem gives OP = … and both points exist."""
        if not content:
            return spec
        elements = list(spec.get("elements") or [])
        centre = next(
            (
                el.get("label")
                for el in elements
                if (el.get("position") or "").lower() in ("centre", "center")
            ),
            "O",
        )
        m = re.search(
            rf"\b{re.escape(str(centre))}([A-Z])\s*=\s*\d",
            content,
            re.I,
        )
        if not m:
            return spec
        other = m.group(1).upper()
        has_seg = any(
            (el.get("shape") or "").lower() == "segment"
            and {el.get("from"), el.get("to")} == {centre, other}
            for el in elements
        )
        if not has_seg:
            elements.append(
                {
                    "shape": "segment",
                    "from": centre,
                    "to": other,
                    "style": "dashed",
                }
            )
            spec = dict(spec)
            spec["elements"] = elements
        return spec

    def _prepare_figure_questions(self, questions: List[Dict]) -> List[Dict]:
        """Sync Fig. numbers, captions, and question↔figure point labels."""
        prepared = []
        fig_idx = 0
        for q in questions:
            q = dict(q)
            if q.get("question_type") != "FigureBased" or not q.get("figure_spec"):
                prepared.append(q)
                continue
            fig_idx += 1
            content = q.get("content", "")
            # Do not inject "Fig. N" into stems — captions are rendered in pdf_builder only.
            content = re.sub(r"(?i)\s*fig\.?\s*\d+\s*", " ", content).strip()
            q["content"] = content
            from app.generation.figure_spec_builder import enrich_figure_spec

            spec = enrich_figure_spec(content, dict(q["figure_spec"]))
            spec = self._sync_figure_labels(content, spec)
            spec = self._ensure_centre_to_external_segment(content, spec)
            spec["title"] = f"Fig. {fig_idx}"
            q["figure_spec"] = spec
            q["figure_number"] = fig_idx
            prepared.append(q)
        return prepared

    async def _attach_figures(self, questions: List[Dict]) -> List[Dict]:
        """Generate and attach figures for figure-based questions in parallel."""
        import asyncio
        questions = self._prepare_figure_questions(questions)
        async def _gen_one(q: Dict) -> Dict:
            spec = q.get("figure_spec")
            fig_type = q.get("figure_type", "labeled_diagram")
            if not spec:
                return q
            try:
                fig_url = await self.figure_gen.generate(spec, fig_type)
                if fig_url:
                    q["figure_url"] = fig_url
                    logger.info("Figure attached for Q order %s: %s", q.get("order_index"), fig_url)
                else:
                    logger.warning("Figure generation returned no URL (order %s)", q.get("order_index"))
            except Exception as e:
                logger.error("Figure generation failed (order %s): %s", q.get("order_index"), e)
            return q
        return await asyncio.gather(*[_gen_one(q) for q in questions])
