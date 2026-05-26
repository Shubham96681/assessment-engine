"""Assessments API — No Auth, synchronous generation"""
import json
import logging
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import load_only
import os

from app.core.database import get_db
from app.models import Document, Assessment, Question
from app.schemas import (
    GenerationConfig,
    AssessmentOut,
    AssessmentListItemOut,
    AssessmentStatusOut,
    QuestionOut,
)
from app.export.pdf_builder import PDFExporter
from app.core.config import settings
from app.core.demo_user import DEMO_USER_ID
from app.generation.generator import QuestionGenerator
from app.generation.answer_format import ensure_answer_text
from app.generation.question_text import ensure_plain_text

router = APIRouter()
logger = logging.getLogger(__name__)


def _question_row_to_dict(q: Question, slot_number: int) -> Dict[str, Any]:
    content = ensure_plain_text(q.content or "")
    return {
        "content": content,
        "question": content,
        "question_type": q.question_type,
        "difficulty": q.difficulty,
        "bloom_level": q.bloom_level,
        "options": q.options,
        "correct_answer": ensure_answer_text(q.correct_answer or ""),
        "explanation": ensure_plain_text(q.explanation or ""),
        "marks": q.marks or 1.0,
        "figure_url": q.figure_url,
        "figure_type": q.figure_type,
        "figure_spec": q.figure_spec,
        "source_chunks": q.source_chunks,
        "content_hash": q.content_hash,
        "quality_score": q.quality_score or 0.0,
        "slot_number": slot_number,
        "order_index": slot_number - 1,
    }


def _merge_regen_slot_into_paper(
    existing: List[Dict[str, Any]],
    new_q: Dict[str, Any],
    slot_number: int,
) -> List[Dict[str, Any]]:
    """Replace one slot in a saved paper with a quality-regen rag_response item."""
    sn = int(
        new_q.get("slot_number")
        or new_q.get("id")
        or slot_number
    )
    merged: List[Dict[str, Any]] = []
    replaced = False
    for i, q in enumerate(existing):
        cur_sn = int(q.get("slot_number") or i + 1)
        if cur_sn == sn:
            updated = dict(new_q)
            updated["slot_number"] = sn
            updated["order_index"] = sn - 1
            if not updated.get("content"):
                updated["content"] = updated.get("question") or ""
            merged.append(updated)
            replaced = True
        else:
            merged.append(dict(q))
    if not replaced:
        updated = dict(new_q)
        updated["slot_number"] = sn
        updated["order_index"] = sn - 1
        merged.append(updated)
    return sorted(merged, key=lambda x: int(x.get("slot_number") or 0))


async def _assessment_out_with_questions(
    a: Assessment, db: AsyncSession
) -> AssessmentOut:
    out = _to_out(a)
    qr = await db.execute(select(Question).where(Question.assessment_id == a.id))
    out.questions = [_q_to_out(q) for q in _ordered_questions(a, qr.scalars().all())]
    return out


def _read_regen_slot_number() -> Optional[int]:
    from app.generation.rag_file_bridge import REGEN_PENDING_FILE

    if not REGEN_PENDING_FILE.exists():
        return None
    try:
        regen = json.loads(REGEN_PENDING_FILE.read_text(encoding="utf-8"))
        sn = regen.get("slot_number")
        if sn is not None:
            return int(sn)
        idx = regen.get("slot_index")
        if idx is not None:
            return int(idx) + 1
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return None
    return None


@router.post("/generate", response_model=AssessmentOut)
async def generate_assessment(
    config: GenerationConfig,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    from app.core.cbse_curriculum_doc import (
        CBSE_CURRICULUM_DOCUMENT_ID,
        ensure_cbse_curriculum_document,
        is_cbse_curriculum_document,
    )

    locked = (config.locked_chapter or "").strip().lower()
    user_doc_id = (config.document_id or "").strip()
    use_pdf = bool(config.use_chapter_pdf) and bool(user_doc_id)

    if not locked and not user_doc_id:
        raise HTTPException(
            status_code=400,
            detail="Select a topic or upload a PDF (document_id or locked_chapter required).",
        )

    if use_pdf:
        r = await db.execute(select(Document).where(Document.id == user_doc_id))
        doc = r.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Document not ready — status: {doc.status}",
            )
        config = config.model_copy(
            update={
                "document_id": user_doc_id,
                "locked_chapter": locked or config.locked_chapter,
                "use_chapter_pdf": True,
                "source_document_id": user_doc_id,
            }
        )
    elif locked:
        curriculum_id = await ensure_cbse_curriculum_document()
        updates: dict = {
            "document_id": curriculum_id,
            "locked_chapter": locked,
            "use_chapter_pdf": False,
        }
        if user_doc_id and not is_cbse_curriculum_document(user_doc_id):
            updates["source_document_id"] = user_doc_id
        config = config.model_copy(update=updates)
    else:
        raise HTTPException(
            status_code=400,
            detail="Select a topic, or enable 'Use chapter PDF' with a ready document.",
        )

    r = await db.execute(select(Document).where(Document.id == config.document_id))
    doc = r.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(status_code=400, detail=f"Document not ready — status: {doc.status}")

    count_r = await db.execute(
        select(func.count(Assessment.id)).where(
            Assessment.user_id == DEMO_USER_ID,
            Assessment.document_id == config.document_id,
        )
    )
    gen_num = (count_r.scalar() or 0) + 1

    assessment = Assessment(
        user_id=DEMO_USER_ID,
        document_id=config.document_id,
        title=config.title or "Assessment",
        config=config.model_dump(mode="json"),
        question_ids=[],
        generation_num=gen_num,
        status="generating",
        total_marks=0.0,
    )
    db.add(assessment)
    await db.flush()
    assessment_id = assessment.id
    # Commit before background work so GET /assessments/{id} never 404s right after create
    await db.commit()
    await db.refresh(assessment)

    background_tasks.add_task(_run_generation, assessment_id, config, gen_num)

    return AssessmentOut(
        id=assessment_id, title=assessment.title,
        config=assessment.config, total_marks=0.0,
        status="generating", pdf_url=None, answer_key_url=None,
        generation_num=gen_num, created_at=assessment.created_at,
    )


async def _run_generation(assessment_id: str, config: GenerationConfig, gen_num: int):
    from app.core.database import AsyncSessionLocal
    generator = QuestionGenerator()
    exporter = PDFExporter(settings.LOCAL_STORAGE_PATH)

    async with AsyncSessionLocal() as db:
        generation_log: list = []
        try:
            doc_r = await db.execute(select(Document).where(Document.id == config.document_id))
            doc_row = doc_r.scalar_one_or_none()
            document_meta = None
            if doc_row:
                document_meta = {
                    "filename": doc_row.original_filename or doc_row.filename,
                    "subject": doc_row.subject,
                    "class_level": doc_row.class_level,
                }
            from app.generation.prior_question_bank import fetch_prior_stems_from_db

            db_prior_stems = await fetch_prior_stems_from_db(
                db,
                config.document_id,
                exclude_assessment_id=assessment_id,
            )
            questions_data, generation_log = await generator.generate(
                config,
                DEMO_USER_ID,
                gen_num,
                document_meta=document_meta,
                supplement_prior_stems=db_prior_stems,
            )
            cfg_dict = config.model_dump(mode="json")
            cfg_dict["title"] = config.title or "Assessment"

            from app.generation.chapter_concept_classifier import resolve_locked_chapter
            from app.generation.question_pipeline import prepare_questions_for_storage

            locked_ch, _, _ = resolve_locked_chapter(
                filename=(document_meta or {}).get("filename", ""),
                topic_focus=config.topic_focus or "",
                context=(questions_data[0].get("content") if questions_data else "") or "",
            )
            questions_data = prepare_questions_for_storage(
                questions_data,
                chapter=locked_ch,
            )
            question_ids, total_marks = [], 0.0
            for qd in questions_data:
                q = Question(
                    document_id=config.document_id,
                    assessment_id=assessment_id,
                    content=qd["content"],
                    question_type=qd.get("question_type"),
                    difficulty=qd.get("difficulty"),
                    bloom_level=qd.get("bloom_level"),
                    options=qd.get("options"),
                    correct_answer=qd.get("correct_answer"),
                    explanation=qd.get("explanation"),
                    marks=qd.get("marks", 1.0),
                    figure_url=qd.get("figure_url"),
                    figure_type=qd.get("figure_type"),
                    figure_spec=qd.get("figure_spec"),
                    source_chunks=qd.get("source_chunks"),
                    content_hash=qd.get("content_hash"),
                    embedding_id=qd.get("embedding_id"),
                    quality_score=qd.get("quality_score", 0.0),
                )
                db.add(q)
                await db.flush()
                question_ids.append(q.id)
                total_marks += qd.get("marks", 1.0)

            cfg_dict["subject"] = config.subject or (doc_row.subject if doc_row else "") or "Mathematics"
            from app.generation.content_profile import parse_filename_hints

            _hints = parse_filename_hints(doc_row.filename if doc_row else "")
            _cls = (config.class_level or (doc_row.class_level if doc_row else "") or "").strip()
            if _hints.get("class_num") and not re.search(r"\d", _cls):
                _cls = f"Class {_hints['class_num']}"
            cfg_dict["class_level"] = _cls or "10"

            r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
            a = r.scalar_one()
            a.question_ids = question_ids
            await db.flush()
            qr_export = await db.execute(
                select(Question).where(Question.assessment_id == assessment_id)
            )
            export_payload = _questions_for_export(a, qr_export.scalars().all(), polish=True)
            for i, qd in enumerate(export_payload):
                qd["order_index"] = i
                qd["slot_number"] = i + 1
            export_urls = exporter.export_assessment(
                questions=export_payload,
                config=cfg_dict,
                assessment_id=assessment_id,
                teacher_name="Teacher",
                institution="Assessment Engine",
            )
            a.total_marks = total_marks
            a.generation_log = generation_log
            a.pdf_url = export_urls["pdf_url"]
            a.answer_key_url = export_urls["answer_key_url"]
            if not question_ids:
                a.status = "failed"
                a.generation_log = generation_log
                fail_hint = "No questions after parse/dedup/quality. "
                for step in generation_log or []:
                    if step.get("error"):
                        fail_hint += step["error"] + " "
                    if step.get("questions_parsed") == 0 and step.get("llm_response"):
                        fail_hint += "JSON parse may have failed. "
                merged = dict(cfg_dict)
                merged["failure_detail"] = fail_hint.strip()
                a.config = merged
                await db.commit()
                logger.error(f"Assessment {assessment_id}: generation produced 0 questions — {fail_hint}")
                return

            a.status = "ready"
            await db.commit()
            logger.info(f"Assessment {assessment_id}: {len(question_ids)} questions, {total_marks} marks")

        except Exception as e:
            from app.generation.generation_oversample import pool_question_count

            logger.error(f"Generation failed {assessment_id}: {e}", exc_info=True)
            r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
            a = r.scalar_one_or_none()
            if a:
                merged = dict(a.config or {})
                merged["failure_detail"] = (
                    f"{type(e).__name__}: {e} "
                    f"(pool={pool_question_count(config.total_questions)}, "
                    f"delivery={config.total_questions})"
                )
                from app.generation.rag_file_bridge import RagAgentResponseMissing

                if isinstance(e, RagAgentResponseMissing):
                    merged["failure_detail"] = str(e)

                a.generation_log = generation_log

                draft: list = []
                for step in reversed(generation_log or []):
                    qs = step.get("questions")
                    if isinstance(qs, list) and qs:
                        draft = qs
                        break
                if draft:
                    from app.generation.chapter_concept_classifier import (
                        resolve_locked_chapter,
                    )
                    from app.generation.question_pipeline import prepare_questions_for_storage

                    locked_ch, _, _ = resolve_locked_chapter(
                        filename=(document_meta or {}).get("filename", ""),
                        topic_focus=config.topic_focus or "",
                        context=(draft[0].get("content") if draft else "") or "",
                    )
                    draft = prepare_questions_for_storage(draft, chapter=locked_ch)
                    question_ids, total_marks = [], 0.0
                    for qd in draft:
                        q = Question(
                            document_id=config.document_id,
                            assessment_id=assessment_id,
                            content=qd["content"],
                            question_type=qd.get("question_type"),
                            difficulty=qd.get("difficulty"),
                            bloom_level=qd.get("bloom_level"),
                            options=qd.get("options"),
                            correct_answer=qd.get("correct_answer"),
                            explanation=qd.get("explanation"),
                            marks=qd.get("marks", 1.0),
                            figure_url=qd.get("figure_url"),
                            figure_type=qd.get("figure_type"),
                            figure_spec=qd.get("figure_spec"),
                            source_chunks=qd.get("source_chunks"),
                            content_hash=qd.get("content_hash"),
                            embedding_id=qd.get("embedding_id"),
                            quality_score=qd.get("quality_score", 0.0),
                        )
                        db.add(q)
                        await db.flush()
                        question_ids.append(q.id)
                        total_marks += qd.get("marks", 1.0)
                    a.question_ids = question_ids
                    a.total_marks = total_marks
                    a.generation_log = generation_log
                    a.status = "ready"
                    merged.pop("failure_detail", None)
                    try:
                        cfg_dict = dict(merged)
                        cfg_dict["title"] = config.title or "Assessment"
                        export_urls = exporter.export_assessment(
                            questions=draft,
                            config=cfg_dict,
                            assessment_id=assessment_id,
                            teacher_name="Teacher",
                            institution="Assessment Engine",
                        )
                        a.pdf_url = export_urls.get("pdf_url")
                        a.answer_key_url = export_urls.get("answer_key_url")
                    except Exception as ex:
                        logger.warning("Partial recovery PDF export failed: %s", ex)
                    a.config = merged
                    await db.commit()
                    logger.info(
                        "Assessment %s: partial recovery saved %d questions",
                        assessment_id,
                        len(question_ids),
                    )
                    return

                a.status = "failed"
                a.config = merged
                await db.commit()


@router.get("", response_model=List[AssessmentListItemOut])
async def list_assessments(db: AsyncSession = Depends(get_db)):
    """Lightweight list — skips generation_log/config (multi‑MB per row)."""
    r = await db.execute(
        select(Assessment)
        .options(
            load_only(
                Assessment.id,
                Assessment.title,
                Assessment.total_marks,
                Assessment.status,
                Assessment.pdf_url,
                Assessment.answer_key_url,
                Assessment.generation_num,
                Assessment.created_at,
            )
        )
        .order_by(Assessment.created_at.desc())
    )
    return [_to_list_item(a) for a in r.scalars().all()]


@router.get("/{assessment_id}/status", response_model=AssessmentStatusOut)
async def get_assessment_status(assessment_id: str, db: AsyncSession = Depends(get_db)):
    """Fast poll while background generation runs (avoids loading huge generation_log)."""
    r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    cnt_r = await db.execute(
        select(func.count(Question.id)).where(Question.assessment_id == assessment_id)
    )
    return AssessmentStatusOut(
        id=a.id,
        title=a.title,
        status=a.status,
        question_count=int(cnt_r.scalar() or 0),
        total_marks=float(a.total_marks or 0),
    )


@router.get("/{assessment_id}", response_model=AssessmentOut)
async def get_assessment(assessment_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    qr = await db.execute(select(Question).where(Question.assessment_id == assessment_id))
    questions = _ordered_questions(a, qr.scalars().all())
    out = _to_out(a)
    out.questions = [_q_to_out(q) for q in questions]
    return out


@router.get("/{assessment_id}/download")
async def download_pdf(assessment_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = r.scalar_one_or_none()
    if not a or not a.pdf_url:
        raise HTTPException(status_code=404, detail="PDF not ready")
    # pdf_url is like /uploads/exports/xxx.pdf — map to filesystem
    pdf_path = a.pdf_url.replace("/uploads", settings.LOCAL_STORAGE_PATH, 1).replace("/", os.sep)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file missing")
    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"assessment_{assessment_id}.pdf")


@router.get("/{assessment_id}/download-key")
async def download_answer_key(assessment_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = r.scalar_one_or_none()
    if not a or not a.answer_key_url:
        raise HTTPException(status_code=404, detail="Answer key not ready")
    ak_path = a.answer_key_url.replace("/uploads", settings.LOCAL_STORAGE_PATH, 1).replace("/", os.sep)
    if not os.path.exists(ak_path):
        raise HTTPException(status_code=404, detail="Answer key file missing")
    return FileResponse(ak_path, media_type="application/pdf",
                        filename=f"answerkey_{assessment_id}.pdf")


@router.post("/{assessment_id}/apply-rag-response", response_model=AssessmentOut)
async def apply_rag_response(
    assessment_id: str,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete a stuck 'generating' assessment using rag_response.txt on disk.
    Set force=true to rebuild an assessment that is already ready.
    """
    from app.generation.rag_file_bridge import read_rag_response, parse_rag_response
    from app.generation.generator import QuestionGenerator
    from app.schemas import GenerationConfig

    r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")

    recover_failed = force and a.status == "failed"

    raw = read_rag_response()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="rag_response.txt not found at project root. Fill it first.",
        )
    answer, _ = parse_rag_response(raw)
    cfg = GenerationConfig(**(a.config or {}))
    from app.generation.generation_oversample import (
        is_oversample_active,
        pool_question_count,
        score_and_select_best,
    )

    delivery_n = cfg.total_questions
    pool_n = pool_question_count(delivery_n)
    gen = QuestionGenerator()
    difficulty, bloom_level = QuestionGenerator._resolve_generation_profile(cfg)
    task = {
        "type": cfg.question_types[0] if cfg.question_types else "FigureBased",
        "difficulty": difficulty,
        "bloom_level": bloom_level,
        "count": pool_n,
        "delivery_count": delivery_n,
    }
    parsed = gen._parse_llm_output(answer, task, cfg, [])
    if not parsed:
        raise HTTPException(status_code=400, detail="rag_response.txt has no valid JSON array")

    regen_slot_number = _read_regen_slot_number()
    if not regen_slot_number and len(parsed) == 1:
        regen_slot_number = int(
            parsed[0].get("slot_number") or parsed[0].get("id") or 0
        ) or None

    qr_existing = await db.execute(
        select(Question).where(Question.assessment_id == assessment_id)
    )
    existing_rows = _ordered_questions(a, qr_existing.scalars().all())
    slot_merge = bool(
        regen_slot_number
        and existing_rows
        and len(parsed) < delivery_n
        and (a.status == "ready" or force)
    )

    if a.status == "ready" and not force and not slot_merge:
        return await _assessment_out_with_questions(a, db)

    if slot_merge:
        existing_paper = [
            _question_row_to_dict(q, i + 1) for i, q in enumerate(existing_rows)
        ]
        for i, qd in enumerate(existing_paper):
            qd["slot_number"] = int(qd.get("slot_number") or i + 1)
            qd["order_index"] = int(qd["slot_number"]) - 1
        parsed = _merge_regen_slot_into_paper(
            existing_paper, parsed[0], regen_slot_number
        )
        force = True
        logger.info(
            "apply-rag-response: merging slot %d into existing %d-question paper",
            regen_slot_number,
            len(parsed),
        )

    from app.generation.canonical_question_signature import (
        disambiguate_duplicate_signatures,
    )
    from app.generation.structural_dedup import filter_structural_duplicates
    from app.generation.theorem_variety_engine import (
        filter_theorem_equivalence_duplicates,
        mark_theorem_equivalence_duplicates,
        validate_paper_theorem_variety,
    )
    from app.generation.full_hard_mode import is_full_hard_paper
    from app.generation.examiner_simulation import run_examiner_simulation

    from app.generation.prior_question_bank import fetch_prior_stems_from_db, merge_prior_stem_lists
    from app.generation.paper_uniqueness import validate_unique_vs_priors
    from app.core.demo_user import DEMO_USER_ID

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
    ok_unique, uniq_issues = validate_unique_vs_priors(parsed, all_prior)
    if not ok_unique and not force and not slot_merge:
        raise HTTPException(
            status_code=400,
            detail=(
                "rag_response.txt repeats a prior paper for this document. "
                f"Issues: {', '.join(uniq_issues[:6])}. "
                "Regenerate with new numbers/labels (see UNIQUENESS MANDATE in rag_query.txt)."
            ),
        )

    for i, q in enumerate(parsed):
        sn = q.get("slot_number")
        if sn is None or int(sn) < 1:
            sn = i + 1
            q["slot_number"] = sn
        q["order_index"] = int(sn) - 1
    doc_r = await db.execute(select(Document).where(Document.id == cfg.document_id))
    doc_row = doc_r.scalar_one_or_none()
    from app.generation.topic_isolation import clear_topic_cache
    from app.generation.strict_topic_gate import filter_questions_by_topic

    topic_state = clear_topic_cache(
        document_id=cfg.document_id,
        filename=doc_row.filename if doc_row else "",
        topic_focus=cfg.topic_focus or "",
        force_invalidate_response=not recover_failed,
    )
    locked = topic_state.get("locked_chapter", "generic")
    if recover_failed and (cfg.topic_focus or "").strip():
        from app.generation.rd_archetypes import detect_chapter_key

        tf = detect_chapter_key(topic_focus=cfg.topic_focus or "")
        if tf and tf != "generic":
            locked = tf
    parsed = disambiguate_duplicate_signatures(parsed, chapter=locked)

    from app.generation.question_type_resolver import (
        coerce_exportable_question_types,
        user_selected_figure_based,
    )

    parsed = await gen.attach_figures_for_figure_based(parsed)
    if not user_selected_figure_based(cfg.question_types):
        parsed = coerce_exportable_question_types(parsed, locked)
    full_hard = is_full_hard_paper(getattr(cfg, "difficulty_distribution", None))
    if (
        full_hard
        and locked == "quadratic"
        and settings.ENABLE_QUADRATIC_QUALITY_MONITOR
    ):
        from app.generation.quadratic_generation_pipeline import (
            run_quadratic_pool_pipeline,
        )

        drop_stems = (
            settings.QUADRATIC_QUALITY_BLOCK_DELIVERY and not force
        )
        parsed, pq_report = run_quadratic_pool_pipeline(
            parsed,
            delivery_count=delivery_n,
            drop_failed_stems=drop_stems,
            apply_structural_dedup=False,
        )
        if settings.ENABLE_QUADRATIC_MATH_VERIFY:
            from app.generation.quadratic_math_gate import (
                pool_math_verification_report,
                require_quadratic_pool_math_verified,
            )

            try:
                require_quadratic_pool_math_verified(parsed)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            _math_ok, _math_reasons = pool_math_verification_report(parsed)
            if not _math_ok:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "rag_response.txt failed quadratic math verification: "
                        + "; ".join(_math_reasons[:10])
                    ),
                )
        if pq_report.get("paper_block"):
            detail = (
                "rag_response.txt failed quadratic L5 paper quality: "
                + "; ".join(pq_report.get("paper_reasons") or [])[:8]
            )
            if settings.QUADRATIC_QUALITY_BLOCK_DELIVERY and not force:
                raise HTTPException(status_code=400, detail=detail)
            logger.warning("apply-rag-response: %s (force=%s)", detail, force)

    from app.generation.quadratic_generation_pipeline import structural_dedup_pool

    parsed = structural_dedup_pool(parsed, delivery_count=delivery_n)
    parsed = filter_theorem_equivalence_duplicates(parsed)

    mark_theorem_equivalence_duplicates(parsed)
    variety_ok, variety_issues = validate_paper_theorem_variety(
        parsed,
        locked_chapter=locked,
        full_hard=full_hard,
        question_count=cfg.total_questions,
    )
    if not variety_ok:
        logger.warning(
            "apply-rag-response theorem variety issues: %s",
            variety_issues[:8],
        )
    ex_ok, ex_report = run_examiner_simulation(
        parsed,
        locked_chapter=locked,
        ui_difficulty=difficulty,
        full_hard=full_hard,
    )
    if not ex_ok:
        logger.warning("apply-rag-response examiner simulation: %s", ex_report)

    from app.generation.paper_integrity import validate_paper_integrity
    from app.generation.cross_question_consistency import validate_cross_question_consistency

    from app.generation.paper_repair import repair_paper_questions

    from app.generation.paper_templates import resolve_paper_template

    _apply_tmpl = resolve_paper_template(
        override=getattr(cfg, "paper_template", None),
        plan_template_id=topic_state.get("paper_template_id"),
        chapter=locked,
        subject=cfg.subject or "Mathematics",
        class_level=cfg.class_level or "10",
        question_count=cfg.total_questions,
        ui_difficulty=difficulty,
        full_hard=full_hard,
    )

    parsed = repair_paper_questions(
        parsed,
        chapter=locked,
        re_enrich_figures=True,
        paper_template_id=_apply_tmpl.id,
    )
    from app.generation.paper_repair import fill_missing_paper_slots
    from app.generation.paper_integrity import normalize_paper_slot_order

    min_required = delivery_n if recover_failed else (
        pool_n if is_oversample_active(delivery_n) and not slot_merge else delivery_n
    )
    if len(parsed) < min_required and not slot_merge:
        from app.core.config import settings as app_settings

        if force and len(parsed) >= delivery_n:
            logger.warning(
                "apply-rag-response: pool %d/%d (force apply continues)",
                len(parsed),
                min_required,
            )
        elif not getattr(app_settings, "ENABLE_LOCAL_LLM_FALLBACK", False):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"rag_response.txt has {len(parsed)} question(s) but "
                    f"{min_required} required"
                    + (
                        f" (pool for best {delivery_n}; ids \"1\"–\"{pool_n}\")"
                        if is_oversample_active(delivery_n)
                        else f' (ids "1" through "{delivery_n}")'
                    )
                    + " (local template fill is disabled)."
                ),
            )
        parsed = fill_missing_paper_slots(
            parsed,
            min_required,
            chapter=locked,
            difficulty=difficulty,
        )
        parsed = normalize_paper_slot_order(parsed)
        parsed = repair_paper_questions(
            parsed,
            chapter=locked,
            re_enrich_figures=True,
            paper_template_id=_apply_tmpl.id,
        )
    from app.generation.question_pipeline import finalize_questions_list

    parsed = finalize_questions_list(parsed)
    from app.core.config import settings as app_settings

    if getattr(app_settings, "ENABLE_CHAPTER_PAPER_QUALITY", True):
        from app.generation.chapter_paper_quality import (
            normalize_chapter_paper_marks,
            validate_chapter_paper_quality,
        )

        parsed = normalize_chapter_paper_marks(
            parsed, chapter=locked, full_hard=full_hard
        )
        cq = validate_chapter_paper_quality(parsed, chapter=locked)
        if not cq.get("chapter_quality_ok") and not slot_merge and not force:
            raise HTTPException(
                status_code=400,
                detail=(
                    "rag_response.txt failed chapter quality checks: "
                    + "; ".join(
                        (cq.get("chapter_quality_critical") or cq.get("chapter_quality_flags", []))[:8]
                    )
                ),
            )
        if not cq.get("chapter_quality_ok") and force:
            logger.warning(
                "apply-rag-response: chapter quality warnings (force apply): %s",
                (cq.get("chapter_quality_critical") or cq.get("chapter_quality_flags", []))[:8],
            )
    from app.generation.content_profile import build_content_profile
    from app.generation.gate_benchmark import (
        gate_level_active,
        validate_paper_against_gate,
    )

    _apply_profile = build_content_profile(
        topic_focus=cfg.topic_focus or "",
        filename=doc_row.filename if doc_row else "",
        context=(parsed[0].get("content") or "") if parsed else "",
        subject=cfg.subject or "",
        class_level=cfg.class_level or "",
        instructions=cfg.instructions or "",
        difficulty=difficulty,
        difficulty_distribution=getattr(cfg, "difficulty_distribution", None),
    )
    _gate_active = gate_level_active(
        exam_track=_apply_profile.exam_track,
        ui_difficulty=difficulty,
        difficulty_distribution=getattr(cfg, "difficulty_distribution", None),
        full_hard=full_hard,
        instructions=cfg.instructions or "",
    )
    if _gate_active and not slot_merge:
        from app.generation.author_styles import resolve_author_style
        from app.generation.rd_archetypes import get_slot_metadata

        _gate_meta = get_slot_metadata(
            delivery_n,
            resolve_author_style(instructions=cfg.instructions or ""),
            ui_difficulty=difficulty,
            locked_chapter=locked,
            full_hard=full_hard,
            difficulty_distribution=getattr(cfg, "difficulty_distribution", None),
        )
        _gate_report = validate_paper_against_gate(
            parsed[:delivery_n],
            ui_difficulty=difficulty,
            slot_metadata=_gate_meta,
            exam_track=_apply_profile.exam_track,
            difficulty_distribution=getattr(cfg, "difficulty_distribution", None),
            full_hard=full_hard,
            instructions=cfg.instructions or "",
        )
        if not _gate_report.get("gate_paper_ok") and not force:
            raise HTTPException(
                status_code=400,
                detail=(
                    "GATE paper level: rag_response.txt below GATE benchmark — "
                    f"target ~{int(_gate_report.get('gate_target_words', 90))} words per stem, "
                    "(i)(ii) sub-parts, prove+Hence chains. "
                    + "; ".join((_gate_report.get("gate_paper_flags") or [])[:6])
                ),
            )
        if not _gate_report.get("gate_paper_ok") and force:
            logger.warning(
                "apply-rag-response: GATE level warnings (force apply): %s",
                (_gate_report.get("gate_paper_flags") or [])[:6],
            )

    if full_hard and not slot_merge:
        from app.generation.author_styles import resolve_author_style
        from app.generation.rd_archetypes import get_slot_metadata

        _fh_meta = get_slot_metadata(
            delivery_n,
            resolve_author_style(instructions=cfg.instructions or ""),
            ui_difficulty=difficulty,
            locked_chapter=locked,
            full_hard=True,
            difficulty_distribution=getattr(cfg, "difficulty_distribution", None),
        )
        _fh_rejects: list[str] = []
        for _i, _q in enumerate(parsed[:delivery_n]):
            if not _q.get("content"):
                _q["content"] = _q.get("question") or ""
            _meta = _fh_meta[_i] if _i < len(_fh_meta) else {"full_hard": True, "band": "L5"}
            if gen.quality.should_reject(
                _q, ui_difficulty=difficulty, slot_meta=_meta
            ):
                _stem = (
                    _q.get("content")
                    or _q.get("question")
                    or ""
                )[:140]
                _fh_rejects.append(f"Q{_i + 1}: {_stem}")
        if _fh_rejects and not slot_merge:
            detail = (
                "FULL HARD (100%): rag_response.txt has items below L5 depth — "
                "each stem needs fusion (e.g. without solving + α²+β², word model + reject root, "
                "balanced OR, parameter interval). Ban bare factorise / bare Find k. "
                + "; ".join(_fh_rejects[:6])
            )
            if not force:
                raise HTTPException(status_code=400, detail=detail)
            logger.warning(
                "apply-rag-response: full_hard quality warnings (force apply): %s",
                _fh_rejects[:6],
            )

    from app.generation.assessment_architect_rules import (
        evaluate_architect_compliance,
        validate_paper_architect,
    )

    for _q in parsed:
        evaluate_architect_compliance(
            _q,
            full_hard=full_hard,
            locked_chapter=locked,
            ui_difficulty=difficulty,
        )
    _arch_paper = validate_paper_architect(
        parsed,
        expected_count=delivery_n,
        full_hard=full_hard,
        locked_chapter=locked,
    )
    if not _arch_paper.get("paper_architect_ok"):
        logger.warning(
            "apply-rag-response paper architect flags: %s",
            _arch_paper.get("paper_architect_flags"),
        )
        if not force and not slot_merge:
            raise HTTPException(
                status_code=400,
                detail=(
                    "rag_response.txt failed assessment architect paper checks: "
                    + "; ".join((_arch_paper.get("paper_architect_flags") or [])[:8])
                ),
            )

    parsed = coerce_exportable_question_types(parsed, locked)

    ok_unique_final, uniq_final = validate_unique_vs_priors(parsed, all_prior)
    if not ok_unique_final and not force and not slot_merge:
        raise HTTPException(
            status_code=400,
            detail=(
                "Paper still matches a prior generation after repair. "
                f"Issues: {', '.join(uniq_final[:6])}. "
                "Write a fresh rag_response.txt with new radii and labels."
            ),
        )

    integrity_expected = delivery_n if slot_merge else (
        pool_n if is_oversample_active(delivery_n) else delivery_n
    )
    integrity = validate_paper_integrity(
        parsed,
        chapter=locked,
        expected_count=integrity_expected,
        paper_template_id=_apply_tmpl.id,
    )
    if (
        not integrity.get("paper_integrity_ok")
        and not slot_merge
        and not recover_failed
        and not force
    ):
        logger.error("apply-rag-response paper integrity failed: %s", integrity)
        raise HTTPException(
            status_code=400,
            detail=(
                "rag_response.txt failed paper integrity checks: "
                + "; ".join(integrity.get("paper_integrity_flags", [])[:6])
            ),
        )
    if not integrity.get("paper_integrity_ok") and force:
        logger.warning(
            "apply-rag-response: paper integrity warnings (force apply): %s",
            integrity.get("paper_integrity_flags", [])[:6],
        )
    if not integrity.get("paper_integrity_ok") and (slot_merge or recover_failed):
        logger.warning(
            "apply-rag-response slot merge: integrity flags logged only: %s",
            integrity.get("paper_integrity_flags", [])[:6],
        )
    pre_apply = list(parsed)
    if recover_failed:
        unique = pre_apply[:pool_n]
    else:
        unique = await gen.dedup.filter(
            parsed,
            DEMO_USER_ID,
            cfg.subject or "Mathematics",
            cfg.class_level or "10",
            document_id=cfg.document_id,
            skip_history=False,
        )
    if len(unique) < delivery_n or slot_merge:
        logger.warning(
            "apply-rag-response: dedup reduced %d→%d — keeping repaired paper slots",
            len(pre_apply),
            len(unique),
        )
        unique = pre_apply[:delivery_n] if slot_merge else pre_apply[:pool_n]
    if recover_failed:
        filtered = unique
    else:
        filtered, _ = filter_questions_by_topic(unique, locked_chapter=locked)
        if len(filtered) < delivery_n and unique:
            filtered = unique[:pool_n]
    if not filtered:
        raise HTTPException(
            status_code=400,
            detail="All questions in rag_response.txt failed topic checks for this chapter.",
        )
    # Preserve slot_number order (do not re-pack by enumerate after dedup).
    parsed = sorted(
        filtered,
        key=lambda q: (q.get("slot_number") or 999, q.get("order_index", 0)),
    )[:pool_n]
    if len(parsed) < delivery_n and not slot_merge:
        raise HTTPException(
            status_code=400,
            detail=(
                f"After dedup only {len(parsed)}/{delivery_n} questions remain — "
                "regenerate rag_response.txt with unique slots."
            ),
        )
    from app.generation.author_styles import resolve_author_style
    from app.generation.rd_archetypes import get_slot_bands, get_slot_metadata

    slot_bands = get_slot_bands(
        len(parsed),
        ui_difficulty=difficulty,
        difficulty_distribution=cfg.difficulty_distribution,
    )
    slot_meta = get_slot_metadata(
        len(parsed),
        resolve_author_style(instructions=cfg.instructions or ""),
        ui_difficulty=difficulty,
        locked_chapter=locked,
        difficulty_distribution=cfg.difficulty_distribution,
    )
    if slot_merge:
        oversample_meta = {"slot_merge": True, "slot": regen_slot_number}
    elif recover_failed:
        from app.generation.generation_oversample import select_best_questions

        parsed, oversample_meta = select_best_questions(
            parsed,
            delivery_n,
            quality_gate=None,
            ui_difficulty=difficulty,
            chapter=locked,
        )
        logger.info("apply-rag recover_failed selection: %s", oversample_meta)
    else:
        parsed, oversample_meta = await score_and_select_best(
            parsed,
            delivery_n,
            quality_scorer=gen.quality,
            ui_difficulty=difficulty,
            slot_bands=slot_bands,
            slot_metadata=slot_meta,
            chapter=locked,
        )
        logger.info("apply-rag oversample selection (post-dedup): %s", oversample_meta)

    from app.generation.chapter_paper_quality import validate_all_slots_present

    slots_ok, slot_issues = validate_all_slots_present(parsed, delivery_n)
    if not slots_ok:
        raise HTTPException(
            status_code=400,
            detail=(
                "Final paper missing question text for slots: "
                + ", ".join(slot_issues[:10])
            ),
        )
    validate_cross_question_consistency(parsed, chapter=locked)
    integrity_final = validate_paper_integrity(
        parsed,
        chapter=locked,
        expected_count=delivery_n,
        paper_template_id=_apply_tmpl.id,
    )
    if (
        not integrity_final.get("paper_integrity_ok")
        and not slot_merge
        and not recover_failed
        and not force
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Final paper failed integrity after selection: "
                + "; ".join(integrity_final.get("paper_integrity_flags", [])[:6])
            ),
        )
    if not integrity_final.get("paper_integrity_ok") and (slot_merge or recover_failed):
        logger.warning(
            "apply-rag slot merge: final integrity flags logged only: %s",
            integrity_final.get("paper_integrity_flags", [])[:6],
        )

    if locked == "quadratic" and settings.ENABLE_QUADRATIC_MATH_VERIFY:
        from app.generation.quadratic_math_gate import require_quadratic_pool_math_verified

        try:
            require_quadratic_pool_math_verified(parsed[:delivery_n])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    exporter = PDFExporter(settings.LOCAL_STORAGE_PATH)
    question_ids, total_marks = [], 0.0
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(Question).where(Question.assessment_id == assessment_id))

    from app.generation.question_pipeline import finalize_question_dict

    for qd in parsed[:delivery_n]:
        qd = finalize_question_dict(qd)
        q = Question(
            document_id=cfg.document_id,
            assessment_id=assessment_id,
            content=qd.get("content") or "",
            question_type=qd.get("question_type"),
            difficulty=qd.get("difficulty"),
            bloom_level=qd.get("bloom_level"),
            options=qd.get("options"),
            correct_answer=qd.get("correct_answer") or "",
            explanation=qd.get("explanation") or "",
            marks=qd.get("marks", 1.0),
            figure_url=qd.get("figure_url"),
            figure_type=qd.get("figure_type"),
            figure_spec=qd.get("figure_spec"),
            source_chunks=qd.get("source_chunks"),
            content_hash=qd.get("content_hash"),
            quality_score=qd.get("quality_score", 0.0),
        )
        db.add(q)
        await db.flush()
        question_ids.append(q.id)
        total_marks += qd.get("marks", 1.0)

    doc_r = await db.execute(select(Document).where(Document.id == cfg.document_id))
    doc_row = doc_r.scalar_one_or_none()
    cfg_dict = cfg.model_dump(mode="json")
    cfg_dict["title"] = a.title or cfg.title or "Assessment"
    cfg_dict["subject"] = cfg.subject or (doc_row.subject if doc_row else "") or "Mathematics"
    from app.generation.content_profile import parse_filename_hints

    hints = parse_filename_hints(doc_row.filename if doc_row else "")
    cls = (cfg.class_level or (doc_row.class_level if doc_row else "") or "").strip()
    if hints.get("class_num") and not re.search(r"\d", cls):
        cls = f"Class {hints['class_num']}"
    cfg_dict["class_level"] = cls or "10"
    a.question_ids = question_ids
    await db.flush()
    qr_export = await db.execute(
        select(Question).where(Question.assessment_id == assessment_id)
    )
    export_payload = _questions_for_export(a, qr_export.scalars().all(), polish=True)
    for i, qd in enumerate(export_payload):
        qd["order_index"] = i
        qd["slot_number"] = i + 1
    export_urls = exporter.export_assessment(
        questions=export_payload,
        config=cfg_dict,
        assessment_id=assessment_id,
    )
    a.total_marks = total_marks
    a.pdf_url = export_urls["pdf_url"]
    a.answer_key_url = export_urls["answer_key_url"]
    a.status = "ready" if question_ids else "failed"
    prior_log = list(a.generation_log or [])
    note = (
        f"Slot {regen_slot_number} updated from rag_response.txt (quality regen)."
        if slot_merge
        else (
            "Final paper saved from rag_response.txt in correct slot order. "
            "Earlier trace steps above are from the auto-generation run."
        )
    )
    prior_log.append(
        {
            "step": "applied_rag",
            "source": "rag_response.txt",
            "questions_applied": len(question_ids),
            "total_marks": total_marks,
            "slot_merge": slot_merge,
            "regen_slot": regen_slot_number,
            "note": note,
        }
    )
    a.generation_log = prior_log
    await db.commit()
    await db.refresh(a)
    if slot_merge:
        from app.generation.rag_file_bridge import clear_regen_pending

        clear_regen_pending()
    out = await _assessment_out_with_questions(a, db)
    logger.info("Applied rag_response.txt to assessment %s (%s questions)", assessment_id, len(question_ids))
    return out


def _ordered_questions(
    assessment: Assessment,
    questions: List[Question],
) -> List[Question]:
    """Return questions in assessment.question_ids order (stable Q1..Qn)."""
    by_id = {q.id: q for q in questions}
    ordered: List[Question] = []
    for qid in assessment.question_ids or []:
        if qid in by_id:
            ordered.append(by_id[qid])
    seen = {q.id for q in ordered}
    for q in questions:
        if q.id not in seen:
            ordered.append(q)
    return ordered


def _questions_for_export(
    assessment: Assessment,
    questions: List[Question],
    *,
    polish: bool = False,
) -> List[dict]:
    """Build export payloads in assessment order, including figure URLs for PDF embed."""
    from app.generation.figure_spec_builder import enrich_figure_spec
    from app.generation.idiomatic_geometry_patterns import apply_idiomatic_fix
    from app.generation.question_pipeline import finalize_question_dict
    ordered = _ordered_questions(assessment, questions)
    out: List[dict] = []
    for i, q in enumerate(ordered):
        content = (q.content or "")
        figure_spec = q.figure_spec
        if polish:
            fixed, _ = apply_idiomatic_fix(content)
            content = fixed
            if q.question_type == "FigureBased":
                figure_spec = enrich_figure_spec(content, q.figure_spec)
        out.append(
            finalize_question_dict(
                {
                    "content": content,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "bloom_level": q.bloom_level,
                    "options": q.options,
                    "correct_answer": q.correct_answer or "",
                    "explanation": q.explanation or "",
                    "marks": q.marks or 1.0,
                    "figure_url": q.figure_url,
                    "figure_type": q.figure_type,
                    "figure_spec": figure_spec,
                    "figure_number": i + 1,
                }
            )
        )
    return out


@router.post("/{assessment_id}/regenerate-export", response_model=AssessmentOut)
async def regenerate_export(assessment_id: str, db: AsyncSession = Depends(get_db)):
    """
    Rebuild assessment + answer-key PDFs from stored questions (e.g. after figure_url was added).
    """
    r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    qr = await db.execute(select(Question).where(Question.assessment_id == assessment_id))
    questions = qr.scalars().all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions to export")

    cfg_dict = dict(a.config or {})
    cfg_dict["title"] = a.title or cfg_dict.get("title") or "Assessment"
    doc_r = await db.execute(select(Document).where(Document.id == a.document_id))
    doc_row = doc_r.scalar_one_or_none()
    if doc_row:
        if not (cfg_dict.get("subject") or "").strip():
            cfg_dict["subject"] = doc_row.subject or "Mathematics"
        if doc_row:
            from app.generation.content_profile import parse_filename_hints

            _rh = parse_filename_hints(doc_row.filename or "")
            _rcls = (cfg_dict.get("class_level") or doc_row.class_level or "").strip()
            if _rh.get("class_num") and not re.search(r"\d", _rcls):
                _rcls = f"Class {_rh['class_num']}"
            cfg_dict["class_level"] = _rcls or "10"
    cfg_dict.setdefault("subject", "Mathematics")
    cfg_dict.setdefault("class_level", "10")
    cfg_dict["subject"] = (cfg_dict.get("subject") or "").strip() or "Mathematics"
    cfg_dict["class_level"] = (cfg_dict.get("class_level") or "").strip() or "10"

    export_payload = _questions_for_export(a, questions, polish=True)
    for i, qd in enumerate(export_payload):
        qd["order_index"] = i
        qd["slot_number"] = i + 1

    from app.generation.chapter_concept_classifier import resolve_locked_chapter
    from app.generation.paper_repair import repair_paper_questions

    locked, _, _ = resolve_locked_chapter(
        filename=doc_row.filename if doc_row else "",
        topic_focus=(cfg_dict.get("topic_focus") or ""),
        context=(export_payload[0].get("content") or "") if export_payload else "",
    )
    export_payload = repair_paper_questions(
        export_payload,
        chapter=locked or "circles",
        re_enrich_figures=True,
    ) if (locked or "").strip().lower() == "circles" else export_payload
    from app.generation.question_pipeline import finalize_questions_list

    export_payload = finalize_questions_list(export_payload)

    from app.generation.figures import FigureGenerator

    fig_gen = FigureGenerator()
    ordered = _ordered_questions(a, questions)

    for q_row, qd in zip(ordered, export_payload):
        if qd.get("content") and q_row.content != qd["content"]:
            q_row.content = qd["content"]
        if qd.get("correct_answer") and q_row.correct_answer != qd.get("correct_answer"):
            q_row.correct_answer = qd["correct_answer"]
        if qd.get("figure_spec"):
            q_row.figure_spec = qd["figure_spec"]
        if qd.get("question_type") != "FigureBased":
            continue
        spec = qd.get("figure_spec")
        if not spec:
            from app.generation.figure_spec_builder import enrich_figure_spec

            spec = enrich_figure_spec(qd.get("content") or "", None)
            if spec.get("type") == "unit_circle" or spec.get("elements"):
                qd["figure_spec"] = spec
                q_row.figure_spec = spec
        if not spec:
            continue
        fig_type = (
            qd.get("figure_type")
            or spec.get("type")
            or "labeled_diagram"
        )
        try:
            new_url = await fig_gen.generate(spec, fig_type)
            if new_url:
                qd["figure_url"] = new_url
                q_row.figure_url = new_url
        except Exception as exc:
            logger.warning("Figure re-render skipped: %s", exc)

    missing = [
        i + 1
        for i, qd in enumerate(export_payload)
        if qd.get("question_type") == "FigureBased" and not qd.get("figure_url")
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Questions {missing} have no figure_url. "
                "Use apply-rag-response (with figures enabled) or regenerate the assessment."
            ),
        )

    exporter = PDFExporter(settings.LOCAL_STORAGE_PATH)
    export_urls = exporter.export_assessment(
        questions=export_payload,
        config=cfg_dict,
        assessment_id=assessment_id,
        teacher_name="Teacher",
        institution="Assessment Engine",
    )
    a.pdf_url = export_urls["pdf_url"]
    a.answer_key_url = export_urls["answer_key_url"]
    await db.commit()
    await db.refresh(a)
    out = _to_out(a)
    qr2 = await db.execute(select(Question).where(Question.assessment_id == assessment_id))
    out.questions = [_q_to_out(q) for q in _ordered_questions(a, qr2.scalars().all())]
    logger.info("Regenerated PDF export for assessment %s", assessment_id)
    return out


@router.delete("/{assessment_id}")
async def delete_assessment(assessment_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(a)
    return {"message": "Deleted"}


def _to_list_item(a: Assessment) -> AssessmentListItemOut:
    return AssessmentListItemOut(
        id=a.id,
        title=a.title,
        total_marks=a.total_marks or 0.0,
        status=a.status,
        pdf_url=a.pdf_url,
        answer_key_url=a.answer_key_url,
        generation_num=a.generation_num,
        created_at=a.created_at,
    )


def _to_out(a: Assessment) -> AssessmentOut:
    return AssessmentOut(
        id=a.id, title=a.title, config=a.config or {},
        total_marks=a.total_marks or 0.0, status=a.status,
        pdf_url=a.pdf_url, answer_key_url=a.answer_key_url,
        generation_num=a.generation_num, created_at=a.created_at,
        generation_log=a.generation_log or [],
    )


def _normalize_mcq_options(
    options: Any, correct_answer: str = ""
) -> Optional[List[Dict[str, Any]]]:
    """Groq/LLM often returns options as {A: ..., B: ...}; API schema expects a list."""
    if not options:
        return None
    if isinstance(options, list):
        return options
    if isinstance(options, dict):
        key = (correct_answer or "").strip().upper()[:1]
        return [
            {
                "label": str(label),
                "text": str(text),
                "is_correct": str(label).strip().upper()[:1] == key,
            }
            for label, text in options.items()
        ]
    return None


def _q_to_out(q: Question) -> QuestionOut:
    from app.generation.question_pipeline import finalize_question_dict

    opts = _normalize_mcq_options(q.options, q.correct_answer or "")
    qd = finalize_question_dict(
        {
            "content": q.content or "",
            "correct_answer": q.correct_answer or "",
            "explanation": q.explanation or "",
            "options": opts,
        }
    )
    return QuestionOut(
        id=q.id, content=qd.get("content") or "",
        question_type=q.question_type or "",
        difficulty=q.difficulty or "",
        bloom_level=q.bloom_level,
        options=qd.get("options", q.options),
        correct_answer=qd.get("correct_answer") or q.correct_answer,
        explanation=qd.get("explanation") or q.explanation,
        marks=q.marks or 1.0,
        figure_url=q.figure_url,
        figure_type=q.figure_type,
        quality_score=q.quality_score or 0.0,
        created_at=q.created_at,
    )
