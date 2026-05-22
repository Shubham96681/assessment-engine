"""
Multi-agent generation orchestrator.

Agents (logical roles, same process):
  1. TopicAgent    — extract chapter + subtopics from PDF chunks
  2. RetrieverAgent — hybrid RAG retrieval aligned to locked chapter
  3. GeneratorAgent — delegated to QuestionGenerator (LLM / file / local)
  4. ValidatorAgent  — topic gate + structural dedup + quality (in generator)

Returns agent_log steps for generation_log / UI transparency.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.generation.content_profile import (
    build_content_profile,
    build_curriculum_context,
    build_rag_retrieval_query,
)
from app.generation.retrieval_confidence import compute_retrieval_confidence
from app.generation.topic_extractor import extract_document_topic_profile
from app.generation.topic_isolation import save_topic_map
from app.rag.retriever import HybridRetriever
from app.schemas import GenerationConfig

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    def __init__(self, retriever: Optional[HybridRetriever] = None):
        self.retriever = retriever or HybridRetriever()

    async def prepare_run(
        self,
        config: GenerationConfig,
        document_meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Run topic + retriever agents before question generation.
        Returns (topic_profile, agent_log).
        """
        meta = document_meta or {}
        agent_log: List[Dict[str, Any]] = []

        # ── Agent 1: Topic ─────────────────────────────────────────────
        topic_profile = await extract_document_topic_profile(
            config.document_id,
            filename=meta.get("filename", ""),
            topic_focus=config.topic_focus or "",
            subject=config.subject or meta.get("subject", "Mathematics"),
            class_level=config.class_level or meta.get("class_level", ""),
        )
        save_topic_map(topic_profile)
        agent_log.append(
            {
                "agent": "topic_agent",
                "status": "ok",
                "primary_topic": topic_profile.get("primary_topic"),
                "locked_chapter": topic_profile.get("locked_chapter"),
                "subtopics_count": len(topic_profile.get("subtopics") or []),
                "subtopics_preview": (topic_profile.get("subtopics") or [])[:8],
                "required_theorems": [
                    t.get("id") for t in (topic_profile.get("required_theorems") or [])
                ],
            }
        )
        logger.info(
            "TopicAgent: chapter=%s topic=%s subtopics=%d",
            topic_profile.get("locked_chapter"),
            topic_profile.get("primary_topic"),
            len(topic_profile.get("subtopics") or []),
        )

        locked = topic_profile.get("locked_chapter", "generic")
        profile = build_content_profile(
            topic_focus=config.topic_focus or "",
            filename=meta.get("filename", ""),
            context="",
            subject=config.subject or "",
            class_level=config.class_level or "",
            instructions=config.instructions or "",
            difficulty="medium",
        )
        profile.chapter_key = locked
        retrieval_query = build_rag_retrieval_query(
            task={
                "type": config.question_types[0] if config.question_types else "MCQ",
                "difficulty": "medium",
            },
            profile=profile,
            config_topic_focus=config.topic_focus or "",
            config_instructions=config.instructions or "",
        )

        # ── Agent 2: Retriever ───────────────────────────────────────────
        chunks: List[Dict[str, Any]] = []
        try:
            chunks = await self.retriever.retrieve(
                retrieval_query,
                config.document_id,
                subject=config.subject,
                locked_chapter=locked,
            )
        except Exception as e:
            logger.warning("RetrieverAgent failed: %s", e)
            agent_log.append(
                {"agent": "retriever_agent", "status": "error", "detail": str(e)[:200]}
            )
        else:
            agent_log.append(
                {
                    "agent": "retriever_agent",
                    "status": "ok",
                    "query": retrieval_query[:200],
                    "chunks": len(chunks),
                    "pages": [c.get("page_num") for c in chunks[:6]],
                }
            )

        retrieval_meta = compute_retrieval_confidence(chunks)
        topic_profile["retrieval_confidence"] = retrieval_meta["score"]
        topic_profile["generation_mode"] = retrieval_meta["mode"]
        topic_profile["use_curriculum_archetypes"] = retrieval_meta[
            "use_curriculum_archetypes"
        ]
        if retrieval_meta["use_curriculum_archetypes"]:
            profile = build_content_profile(
                topic_focus=config.topic_focus or "",
                filename=meta.get("filename", ""),
                context="",
                subject=config.subject or "",
                class_level=config.class_level or "",
                instructions=config.instructions or "",
            )
            profile.chapter_key = locked
            topic_profile["curriculum_context"] = build_curriculum_context(
                profile,
                required_theorems=topic_profile.get("required_theorems"),
                retrieval_confidence=retrieval_meta["score"],
            )
        agent_log.append(
            {
                "agent": "retriever_agent",
                "status": "confidence",
                "retrieval_confidence": retrieval_meta["score"],
                "generation_mode": retrieval_meta["mode"],
                "reason": retrieval_meta.get("reason"),
            }
        )

        topic_profile["retrieval_preview"] = [
            {"page": c.get("page_num"), "preview": (c.get("text") or "")[:120]}
            for c in chunks[:4]
        ]
        return topic_profile, agent_log

    @staticmethod
    def validator_agent_log(
        *,
        parsed: int,
        accepted: int,
        rejected: int,
        dedup_in: int,
        dedup_out: int,
        coverage_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        log = {
            "agent": "validator_agent",
            "status": "ok",
            "parsed": parsed,
            "topic_gate_accepted": accepted,
            "topic_gate_rejected": rejected,
            "dedup_in": dedup_in,
            "dedup_out": dedup_out,
        }
        if coverage_report:
            log["theorem_coverage_score"] = coverage_report.get("coverage_score")
            log["weighted_coverage_score"] = coverage_report.get(
                "weighted_coverage_score"
            )
            log["cognitive_diversity_score"] = coverage_report.get(
                "cognitive_diversity_score"
            )
            log["theorem_combo_score"] = coverage_report.get("combo_score")
            log["missing_theorems"] = coverage_report.get(
                "missing_theorems_weighted"
            ) or coverage_report.get("missing_theorems")
        return log
