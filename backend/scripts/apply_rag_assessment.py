"""Apply rag_response.txt to a stuck or failed assessment (bypasses HTTP)."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.demo_user import DEMO_USER_ID
from app.core.demo_user import DEMO_USER_ID
from app.generation.canonical_question_signature import disambiguate_duplicate_signatures
from app.generation.paper_uniqueness import validate_unique_vs_priors
from app.generation.prior_question_bank import fetch_prior_stems_from_db, merge_prior_stem_lists
from app.generation.cross_question_consistency import validate_cross_question_consistency
from app.generation.generator import QuestionGenerator
from app.generation.paper_integrity import validate_paper_integrity
from app.generation.paper_repair import fill_missing_paper_slots, repair_paper_questions
from app.generation.question_pipeline import finalize_questions_list
from app.generation.rag_file_bridge import parse_rag_response, read_rag_response
from app.generation.structural_dedup import filter_structural_duplicates
from app.generation.strict_topic_gate import filter_questions_by_topic
from app.generation.theorem_variety_engine import filter_theorem_equivalence_duplicates
from app.generation.topic_isolation import clear_topic_cache
from app.models import Assessment, Document, Question
from app.schemas import GenerationConfig


async def main(assessment_id: str) -> None:
    raw = read_rag_response()
    if not raw:
        print("rag_response.txt missing")
        return
    answer, _ = parse_rag_response(raw)

    async with AsyncSessionLocal() as db:
        a = (
            await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        ).scalar_one_or_none()
        if not a:
            print("Assessment not found:", assessment_id)
            return
        cfg = GenerationConfig(**(a.config or {}))
        gen = QuestionGenerator()
        diff, bloom = QuestionGenerator._resolve_generation_profile(cfg)
        task = {
            "type": "FigureBased",
            "difficulty": diff,
            "bloom_level": bloom,
            "count": cfg.total_questions,
        }
        parsed = gen._parse_llm_output(answer, task, cfg, [])
        if not parsed:
            print("No questions parsed from rag_response.txt")
            return
        db_prior = await fetch_prior_stems_from_db(
            db, cfg.document_id, exclude_assessment_id=assessment_id
        )
        qdrant_prior = await gen.dedup.get_recent_stem_previews(
            DEMO_USER_ID,
            cfg.subject or "Mathematics",
            cfg.class_level or "10",
            document_id=cfg.document_id,
        )
        all_prior = merge_prior_stem_lists(db_prior, qdrant_prior, limit=50)
        force = "--force" in sys.argv or os.environ.get("RAG_APPLY_FORCE") == "1"
        ok_unique, uniq_issues = validate_unique_vs_priors(parsed, all_prior)
        if not ok_unique and not force:
            print("Uniqueness failed:", uniq_issues[:8])
            print("Re-run with --force to apply anyway.")
            return
        if not ok_unique and force:
            print("Uniqueness warnings (forced):", uniq_issues[:8])

        parsed = filter_structural_duplicates(parsed, min_keep=cfg.total_questions)
        parsed = filter_theorem_equivalence_duplicates(parsed)
        if cfg.question_types and any(
            str(t) == "FigureBased" or getattr(t, "value", None) == "FigureBased"
            for t in cfg.question_types
        ):
            parsed = gen._prepare_figure_questions(parsed)
            if settings.ENABLE_FIGURE_GENERATION:
                parsed = await gen._attach_figures(parsed)

        for i, q in enumerate(parsed):
            sn = q.get("slot_number") or (i + 1)
            q["slot_number"] = int(sn)
            q["order_index"] = int(sn) - 1

        doc = (
            await db.execute(select(Document).where(Document.id == cfg.document_id))
        ).scalar_one_or_none()
        topic_state = clear_topic_cache(
            document_id=cfg.document_id,
            filename=doc.filename if doc else "",
            topic_focus=cfg.topic_focus or "",
        )
        locked = topic_state.get("locked_chapter", "circles")
        parsed = disambiguate_duplicate_signatures(parsed, chapter=locked)

        from app.generation.paper_templates import resolve_paper_template
        from app.generation.full_hard_mode import is_full_hard_paper

        _tmpl = resolve_paper_template(
            override=getattr(cfg, "paper_template", None),
            plan_template_id=topic_state.get("paper_template_id"),
            chapter=locked,
            subject=cfg.subject or "Mathematics",
            class_level=cfg.class_level or "10",
            question_count=cfg.total_questions,
            ui_difficulty=diff,
            full_hard=is_full_hard_paper(cfg.difficulty_distribution),
        )

        parsed = repair_paper_questions(
            parsed,
            chapter=locked,
            re_enrich_figures=True,
            paper_template_id=_tmpl.id,
        )
        parsed = fill_missing_paper_slots(
            parsed,
            cfg.total_questions,
            chapter=locked,
            difficulty=diff,
        )
        parsed = finalize_questions_list(parsed)

        integrity = validate_paper_integrity(
            parsed,
            chapter=locked,
            expected_count=cfg.total_questions,
            paper_template_id=_tmpl.id,
        )
        if not integrity.get("paper_integrity_ok"):
            print("Integrity failed:", integrity.get("paper_integrity_flags"))
            return
        validate_cross_question_consistency(parsed, chapter=locked)

        filtered, _ = filter_questions_by_topic(parsed, locked_chapter=locked)
        if len(filtered) < cfg.total_questions:
            filtered = parsed[: cfg.total_questions]

        # Remove old questions
        old = (
            await db.execute(
                select(Question).where(Question.assessment_id == assessment_id)
            )
        ).scalars().all()
        for q in old:
            await db.delete(q)

        question_ids: list[str] = []
        for qd in filtered:
            row = Question(
                document_id=cfg.document_id,
                assessment_id=assessment_id,
                content=qd.get("content") or "",
                question_type=qd.get("question_type") or "FigureBased",
                difficulty=qd.get("difficulty") or diff,
                bloom_level=qd.get("bloom_level") or bloom,
                correct_answer=qd.get("correct_answer") or "",
                explanation=qd.get("explanation") or "",
                marks=qd.get("marks") or 1.0,
                figure_url=qd.get("figure_url"),
                figure_type=qd.get("figure_type"),
                figure_spec=qd.get("figure_spec"),
            )
            db.add(row)
            await db.flush()
            question_ids.append(row.id)

        a.question_ids = question_ids
        a.total_marks = sum(float(qd.get("marks") or 1.0) for qd in filtered)
        a.status = "ready"
        a.generation_log = a.generation_log or []
        a.generation_log.append(
            {
                "source": "rag_response.txt",
                "note": "Applied via scripts/apply_rag_assessment.py",
            }
        )
        await db.flush()
        from app.export.pdf_builder import PDFExporter
        from app.api.assessments import _questions_for_export

        qr2 = (
            await db.execute(
                select(Question).where(Question.assessment_id == assessment_id)
            )
        ).scalars().all()
        cfg_dict = dict(a.config or {})
        cfg_dict["title"] = a.title or cfg_dict.get("title") or "Assessment"
        doc = (
            await db.execute(select(Document).where(Document.id == cfg.document_id))
        ).scalar_one_or_none()
        if doc:
            cfg_dict.setdefault("subject", doc.subject or "Mathematics")
            cfg_dict.setdefault("class_level", doc.class_level or "11")
        export_payload = _questions_for_export(a, qr2, polish=True)
        for i, qd in enumerate(export_payload):
            qd["order_index"] = i
            qd["slot_number"] = i + 1
        urls = PDFExporter(settings.LOCAL_STORAGE_PATH).export_assessment(
            export_payload, cfg_dict, assessment_id
        )
        a.pdf_url = urls["pdf_url"]
        a.answer_key_url = urls.get("answer_key_url")
        await db.commit()
        print(
            f"Applied {len(question_ids)} questions to {assessment_id} — "
            f"status ready, PDF {urls['pdf_url']}"
        )


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    aid = args[0] if args else "68128914-3240-4240-9e0a-6ea317be1606"
    asyncio.run(main(aid))
