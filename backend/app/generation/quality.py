"""
Quality pipeline — heuristic, authenticity, completeness, idiomatic fixes, curation.
"""
import logging
import json
import re
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.generation.textbook_constants import BANNED_META_PHRASES, STEM_WORD_TARGETS
from app.generation.authenticity import TextbookAuthenticityScorer
from app.generation.curation import curate_batch, diversity_ok
from app.generation.solution_difficulty import score_solution_difficulty
from app.generation.question_completeness import validate_completeness, should_reject_incomplete
from app.generation.stem_dependency_validator import (
    validate_stem_dependencies,
    should_reject_stem_dependencies,
)
from app.generation.figure_necessity import (
    validate_figure_necessity,
    should_reject_decorative_figure,
)
from app.generation.reasoning_depth import (
    reasoning_depth_score,
    should_reject_shallow_reasoning,
)
from app.generation.idiomatic_geometry_patterns import detect_awkward_idiom
from app.generation.rd_archetypes import get_slot_bands, get_slot_metadata
from app.generation.author_styles import resolve_author_style
from app.generation.hard_mode_calibration import (
    evaluate_hard_mode,
    should_reject_hard_mode,
)
from app.generation.theorem_topology_validator import (
    should_reject_topology,
    validate_minimum_stem_referents,
    validate_slot_topology,
)
from app.generation.numeric_constraint_validator import (
    validate_numeric_constraints,
    should_reject_numeric,
)
from app.generation.reasoning_signature import (
    annotate_paper_reasoning,
    reasoning_diversity_ok,
    should_reject_reasoning,
)
from app.generation.angle_target_validator import (
    validate_angle_targets,
    should_reject_angle_target,
)
from app.generation.proof_elegance import (
    evaluate_proof_elegance,
    should_reject_proof_elegance,
)
from app.generation.solution_elegance import (
    evaluate_solution_elegance,
    should_reject_solution_elegance,
)
from app.generation.strict_topic_gate import should_reject_topic_drift
from app.generation.topic_isolation import get_current_topic_state

logger = logging.getLogger(__name__)

EXAM_COMMAND_PHRASES = (
    "find ",
    "prove that",
    "show that",
    "calculate",
    "if ",
    "hence",
    "determine",
    "can a tangent",
    "two concentric",
    "tangents ",
)


class QualityScorer:
    def __init__(self):
        self.authenticity = TextbookAuthenticityScorer()

    def _apply_completeness_and_combined(
        self,
        q: Dict[str, Any],
        band: str,
        *,
        ui_difficulty: str = "medium",
        slot_meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        q.update(validate_completeness(q))
        from app.core.config import settings

        if settings.ENABLE_STEM_DEPENDENCY_VALIDATION:
            q.update(validate_stem_dependencies(q))
        if settings.ENABLE_COGNITIVE_GRAPH_VALIDATION:
            from app.generation.cognitive_graph_validator import evaluate_cognitive_graph

            q.update(
                evaluate_cognitive_graph(
                    q, slot_meta=slot_meta, ui_difficulty=ui_difficulty
                )
            )
        if settings.ENABLE_ARC_GEOMETRY_VALIDATION:
            from app.generation.arc_geometry_validator import validate_circle_geometry

            q.update(
                validate_circle_geometry(q, ui_difficulty=ui_difficulty)
            )
        if settings.ENABLE_THEOREM_TOPOLOGY_VALIDATION:
            q.update(validate_minimum_stem_referents(q))
            q.update(
                validate_slot_topology(
                    q, slot_meta=slot_meta, ui_difficulty=ui_difficulty
                )
            )
        if settings.ENABLE_FIGURE_NECESSITY_VALIDATION:
            q.update(validate_figure_necessity(q))
        q.update(
            reasoning_depth_score(q, slot_band=band, ui_difficulty=ui_difficulty)
        )
        self.authenticity.score_question(q, slot_band=band)
        q["quality_score"] = self._heuristic_score(q, band)
        awkward = detect_awkward_idiom(q.get("content") or "")
        if awkward:
            q["quality_score"] = max(0.0, q["quality_score"] - 0.12 * len(awkward))
        from app.generation.topic_isolation import get_current_topic_state

        locked = (get_current_topic_state() or {}).get("locked_chapter") or q.get(
            "locked_chapter", ""
        )
        hard_report = evaluate_hard_mode(
            q,
            slot_band=band,
            ui_difficulty=ui_difficulty,
            slot_meta=slot_meta,
            locked_chapter=locked,
        )
        q.update(hard_report)
        num_report = validate_numeric_constraints(q)
        q.update(num_report)
        angle_report = validate_angle_targets(q.get("content") or "", q)
        q.update(
            {
                "angle_target_ok": angle_report.get("angle_target_ok"),
                "angle_target_flags": angle_report.get("angle_target_flags"),
                "angle_target_score": angle_report.get("angle_target_score"),
            }
        )
        if (ui_difficulty or "").lower() in ("hard", "difficult"):
            q.update(evaluate_proof_elegance(q))
            if band in ("L4", "L5") or q.get("sparse_hard"):
                q.update(evaluate_solution_elegance(q))
        hard_w = 0.2 if (ui_difficulty or "").lower() in ("hard", "difficult") else 0.0
        eleg_w = (
            settings.SOLUTION_ELEGANCE_WEIGHT
            if (ui_difficulty or "").lower() in ("hard", "difficult")
            else 0.0
        )
        q["combined_score"] = round(
            0.30 * q["quality_score"]
            + 0.36 * q.get("authenticity_score", 0)
            + 0.16 * q.get("completeness_score", 0)
            + 0.06 * q.get("dependency_score", 1.0)
            + 0.05 * q.get("paper_dependency_score", 1.0)
            + 0.05 * q.get("cross_question_score", 1.0)
            + 0.06 * q.get("figure_necessity_score", 1.0)
            + 0.10 * q.get("reasoning_depth_score", 0.5)
            + hard_w * q.get("hard_mode_score", 1.0)
            + 0.08 * q.get("solution_difficulty", 0)
            + 0.06 * q.get("numeric_consistency_score", 1.0)
            + eleg_w * q.get("solution_elegance_score", 0.75),
            3,
        )

    async def score_batch(
        self,
        questions: List[Dict[str, Any]],
        slot_bands: Optional[List[str]] = None,
        *,
        ui_difficulty: str = "medium",
        slot_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        if not questions:
            return []
        ui = ui_difficulty or "medium"
        bands = slot_bands or get_slot_bands(len(questions), ui_difficulty=ui)
        meta_list = slot_metadata or get_slot_metadata(
            len(questions), resolve_author_style(), ui_difficulty=ui
        )
        for q in questions:
            idx = min(q.get("order_index", 0), len(bands) - 1)
            band = bands[idx] if bands else "L3"
            meta = meta_list[idx] if idx < len(meta_list) else None
            score_solution_difficulty(q)
            self._apply_completeness_and_combined(
                q, band, ui_difficulty=ui, slot_meta=meta
            )
        annotate_paper_reasoning(questions, ui_difficulty=ui)
        for q in questions:
            idx = min(q.get("order_index", 0), len(bands) - 1)
            band = bands[idx] if bands else "L3"
            if q.get("reasoning_duplicate"):
                q["combined_score"] = max(
                    0.0, q.get("combined_score", 0) - 0.22
                )
            if not q.get("angle_target_ok", True):
                q["combined_score"] = max(
                    0.0, q.get("combined_score", 0) - 0.18
                )
        if settings.ENABLE_SELF_ENHANCEMENT and settings.has_cloud_llm():
            try:
                sample = questions[: min(2, len(questions))]
                await self._llm_score_sample(sample)
            except Exception as e:
                logger.warning(f"LLM quality scoring failed (using heuristic): {e}")
        return questions

    def curate_batch(
        self,
        questions: List[Dict[str, Any]],
        *,
        author_instructions: str = "",
        ui_difficulty: str = "medium",
    ) -> List[Dict[str, Any]]:
        author = resolve_author_style(instructions=author_instructions)
        ui = ui_difficulty or "medium"
        slot_meta = get_slot_metadata(len(questions), author, ui_difficulty=ui)
        curated = curate_batch(questions, slot_metadata=slot_meta)
        bands = get_slot_bands(len(curated), ui_difficulty=ui)
        for i, q in enumerate(curated):
            band = bands[i] if i < len(bands) else "L3"
            meta = slot_meta[i] if i < len(slot_meta) else None
            self._apply_completeness_and_combined(
                q, band, ui_difficulty=ui, slot_meta=meta
            )
        ok, reason = diversity_ok(curated)
        if not ok:
            logger.info("Paper diversity note: %s", reason)
        annotate_paper_reasoning(curated, ui_difficulty=ui)
        from app.generation.topic_isolation import get_current_topic_state
        from app.generation.theorem_variety_engine import mark_theorem_equivalence_duplicates

        mark_theorem_equivalence_duplicates(curated)
        locked = (get_current_topic_state() or {}).get("locked_chapter", "")
        r_ok, r_reason = reasoning_diversity_ok(
            curated, ui_difficulty=ui, locked_chapter=locked
        )
        if not r_ok:
            logger.info("Reasoning diversity note: %s", r_reason)
        return curated

    def should_reject(
        self,
        q: Dict[str, Any],
        *,
        ui_difficulty: str = "medium",
        slot_meta: Optional[Dict[str, Any]] = None,
        lenient: bool = False,
    ) -> bool:
        from app.generation.topic_isolation import get_current_topic_state

        band = (slot_meta or {}).get("band") or q.get("slot_band") or "L3"
        locked = (get_current_topic_state() or {}).get("locked_chapter") or q.get(
            "locked_chapter"
        )

        if self.authenticity.should_reject(q):
            return True
        if should_reject_incomplete(q):
            return True
        from app.core.config import settings

        if settings.ENABLE_STEM_DEPENDENCY_VALIDATION and should_reject_stem_dependencies(
            q
        ):
            return True
        if settings.ENABLE_PAPER_DEPENDENCY_GRAPH:
            from app.generation.paper_dependency_graph import should_reject_paper_dependency

            if should_reject_paper_dependency(q, ui_difficulty=ui_difficulty):
                return True
        if settings.ENABLE_CROSS_QUESTION_CONSISTENCY:
            from app.generation.cross_question_consistency import (
                should_reject_cross_question_inconsistency,
            )

            if should_reject_cross_question_inconsistency(q, ui_difficulty=ui_difficulty):
                return True
        if settings.ENABLE_FIGURE_NECESSITY_VALIDATION and should_reject_decorative_figure(
            q
        ):
            return True
        if should_reject_shallow_reasoning(
            q, slot_band=band, ui_difficulty=ui_difficulty
        ):
            return True
        if should_reject_numeric(q):
            return True
        if locked and should_reject_topic_drift(q, locked_chapter=locked):
            return True
        if should_reject_angle_target(q):
            return True
        if q.get("theorem_equivalent_duplicate"):
            return True
        from app.core.config import settings

        if settings.ENABLE_HARDNESS_SCORER and ui_difficulty.lower() in (
            "hard",
            "difficult",
        ):
            from app.generation.hardness_scorer import should_reject_hardness

            if should_reject_hardness(
                q, slot_band=band, ui_difficulty=ui_difficulty
            ):
                return True
        if settings.ENABLE_EXAMINER_SIMULATION and ui_difficulty.lower() in (
            "hard",
            "difficult",
        ):
            from app.generation.examiner_simulation import should_reject_examiner

            if should_reject_examiner(
                q,
                index=int(q.get("order_index") or q.get("slot_number") or 0),
                total=10,
                slot_band=band,
                ui_difficulty=ui_difficulty,
            ):
                return True
        if should_reject_reasoning(
            q, slot_band=band, ui_difficulty=ui_difficulty
        ):
            return True
        if should_reject_proof_elegance(
            q, slot_band=band, ui_difficulty=ui_difficulty
        ):
            return True
        if should_reject_solution_elegance(
            q, slot_band=band, ui_difficulty=ui_difficulty
        ):
            return True
        if lenient:
            return q.get("combined_score", 0) < 0.28
        if should_reject_hard_mode(
            q,
            slot_band=band,
            ui_difficulty=ui_difficulty,
            slot_meta=slot_meta,
            locked_chapter=locked or "",
            full_hard=bool((slot_meta or {}).get("full_hard")),
        ):
            return True
        if settings.ENABLE_COGNITIVE_GRAPH_VALIDATION:
            from app.generation.cognitive_graph_validator import should_reject_cognitive_graph

        if settings.ENABLE_COGNITIVE_GRAPH_VALIDATION and should_reject_cognitive_graph(
            q,
            slot_meta=slot_meta,
            ui_difficulty=ui_difficulty,
        ):
            return True
        if settings.ENABLE_ARC_GEOMETRY_VALIDATION:
            from app.generation.arc_geometry_validator import should_reject_arc_geometry

            if should_reject_arc_geometry(q, ui_difficulty=ui_difficulty):
                return True
        if settings.ENABLE_THEOREM_TOPOLOGY_VALIDATION and should_reject_topology(
            q,
            slot_meta=slot_meta,
            ui_difficulty=ui_difficulty,
        ):
            return True
        if q.get("combined_score", 0) < 0.38:
            return True
        return False

    def _heuristic_score(self, q: Dict, band: str = "L3") -> float:
        score = 0.4
        content = q.get("content", "") or ""
        answer = (q.get("correct_answer") or "") if isinstance(q.get("correct_answer"), str) else ""
        lower = content.lower()
        n_words = len(content.split())

        meta_hits = sum(1 for p in BANNED_META_PHRASES if p in lower)
        score -= min(0.5, meta_hits * 0.14)

        lo, hi = STEM_WORD_TARGETS.get(band, (20, 40))
        if q.get("question_type") == "FigureBased":
            hi += 15
            lo += 8
        if lo <= n_words <= hi:
            score += 0.16
        elif n_words > hi + 20:
            score -= 0.2
        elif 8 <= n_words < lo and self.authenticity._is_one_line_conceptual(content):
            score += 0.1
        elif n_words < lo - 3:
            score -= 0.08

        if any(p in lower for p in ("which statement", "best supported by", "define ")):
            score -= 0.25

        cmd_hits = sum(1 for p in EXAM_COMMAND_PHRASES if p in lower)
        score += min(0.18, cmd_hits * 0.05)

        if re.search(r"\bfind\b|\bprove\b|\bshow that\b", lower):
            score += 0.06

        if answer and len(answer) > 60:
            score += 0.08

        return max(0.0, min(1.0, score))

    async def _llm_score_sample(self, sample: List[Dict]) -> None:
        if not settings.has_cloud_llm():
            return
        for q in sample:
            prompt = f"""
Rate Class 10 Maths question (0.0–1.0).

Question: {q['content']}
Flags: {q.get('completeness_flags', [])}

HIGH: idiomatic RD Sharma, self-contained givens, solvable without figure.
LOW: awkward idiom, 'find angle' without data, meta language.

Return ONLY JSON: {{"total": 0.0, "feedback": "one line"}}
"""
            try:
                if settings.GOOGLE_GEMINI_API_KEY:
                    import google.generativeai as genai

                    genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    text = model.generate_content(prompt).text
                else:
                    from openai import AsyncOpenAI

                    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    resp = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=200,
                    )
                    text = resp.choices[0].message.content
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1:
                    scores = json.loads(text[start:end])
                    llm = scores.get("total", q["quality_score"])
                    q["quality_score"] = (q["quality_score"] + llm) / 2
                    q["quality_breakdown"] = scores
            except Exception as e:
                logger.debug(f"LLM scoring error: {e}")
