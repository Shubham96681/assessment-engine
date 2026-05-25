"""Assessments API — No Auth, synchronous generation"""
import logging
from typing import List
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

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=AssessmentOut)
async def generate_assessment(
    config: GenerationConfig,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
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
            cfg_dict["class_level"] = config.class_level or (doc_row.class_level if doc_row else "") or "10"
            export_urls = exporter.export_assessment(
                questions=questions_data,
                config=cfg_dict,
                assessment_id=assessment_id,
                teacher_name="Teacher",
                institution="Assessment Engine",
            )

            r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
            a = r.scalar_one()
            a.question_ids = question_ids
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
                merged["failure_hint"] = fail_hint.strip() or (
                    "Ensure rag_response.txt exists and backend was restarted. "
                    "Or click 'finish now' after filling rag_response.txt."
                )
                a.config = merged
                await db.commit()
                logger.error(f"Assessment {assessment_id}: generation produced 0 questions — {fail_hint}")
                return

            a.status = "ready"
            await db.commit()
            logger.info(f"Assessment {assessment_id}: {len(question_ids)} questions, {total_marks} marks")

        except Exception as e:
            logger.error(f"Generation failed {assessment_id}: {e}", exc_info=True)
            r = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
            a = r.scalar_one_or_none()
            if a:
                a.status = "failed"
                merged = dict(a.config or {})
                hint = (
                    f"Generation error: {type(e).__name__}: {e}. "
                    "Restart backend after code updates; ensure rag_response.txt has "
                    f"{config.total_questions} questions if using the file agent."
                )
                from app.generation.rag_file_bridge import RagAgentResponseMissing

                if isinstance(e, RagAgentResponseMissing):
                    hint = (
                        f"{e} "
                        "Enable Cursor Hooks (Settings → Hooks), open an Agent chat for this repo, "
                        "and let the stop hook write rag_response.txt when rag_query.txt updates. "
                        "Or click 'I filled rag_response.txt — finish now' on the assessment page."
                    )
                merged["failure_hint"] = hint
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
    if a.status == "ready" and not force:
        return _to_out(a)

    raw = read_rag_response()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="rag_response.txt not found at project root. Fill it first.",
        )
    answer, _ = parse_rag_response(raw)
    cfg = GenerationConfig(**(a.config or {}))
    gen = QuestionGenerator()
    difficulty, bloom_level = QuestionGenerator._resolve_generation_profile(cfg)
    task = {
        "type": cfg.question_types[0] if cfg.question_types else "FigureBased",
        "difficulty": difficulty,
        "bloom_level": bloom_level,
        "count": cfg.total_questions,
    }
    parsed = gen._parse_llm_output(answer, task, cfg, [])
    if not parsed:
        raise HTTPException(status_code=400, detail="rag_response.txt has no valid JSON array")

    from app.generation.canonical_question_signature import (
        filter_zero_duplicate_signatures,
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
    if not ok_unique and not force:
        raise HTTPException(
            status_code=400,
            detail=(
                "rag_response.txt repeats a prior paper for this document. "
                f"Issues: {', '.join(uniq_issues[:6])}. "
                "Regenerate with new numbers/labels (see UNIQUENESS MANDATE in rag_query.txt)."
            ),
        )

    parsed = filter_zero_duplicate_signatures(parsed)
    parsed = filter_structural_duplicates(parsed, min_keep=cfg.total_questions)
    parsed = filter_theorem_equivalence_duplicates(parsed)

    if cfg.question_types and any(
        str(t) == "FigureBased" or (hasattr(t, "value") and t.value == "FigureBased")
        for t in cfg.question_types
    ):
        parsed = gen._prepare_figure_questions(parsed)
        if settings.ENABLE_FIGURE_GENERATION:
            parsed = await gen._attach_figures(parsed)

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
    )
    locked = topic_state.get("locked_chapter", "generic")
    full_hard = is_full_hard_paper(getattr(cfg, "difficulty_distribution", None))
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

    parsed = repair_paper_questions(parsed, chapter=locked, re_enrich_figures=True)
    from app.generation.question_pipeline import finalize_questions_list

    parsed = finalize_questions_list(parsed)

    ok_unique_final, uniq_final = validate_unique_vs_priors(parsed, all_prior)
    if not ok_unique_final and not force:
        raise HTTPException(
            status_code=400,
            detail=(
                "Paper still matches a prior generation after repair. "
                f"Issues: {', '.join(uniq_final[:6])}. "
                "Write a fresh rag_response.txt with new radii and labels."
            ),
        )

    integrity = validate_paper_integrity(
        parsed,
        chapter=locked,
        expected_count=cfg.total_questions,
    )
    if not integrity.get("paper_integrity_ok"):
        logger.error("apply-rag-response paper integrity failed: %s", integrity)
        raise HTTPException(
            status_code=400,
            detail=(
                "rag_response.txt failed paper integrity checks: "
                + "; ".join(integrity.get("paper_integrity_flags", [])[:6])
            ),
        )
    validate_cross_question_consistency(parsed, chapter=locked)

    pre_apply = list(parsed)
    unique = await gen.dedup.filter(
        parsed,
        DEMO_USER_ID,
        cfg.subject or "Mathematics",
        cfg.class_level or "10",
        document_id=cfg.document_id,
        skip_history=False,
    )
    if len(unique) < cfg.total_questions:
        logger.warning(
            "apply-rag-response: dedup reduced %d→%d — keeping repaired paper slots",
            len(pre_apply),
            len(unique),
        )
        unique = pre_apply[: cfg.total_questions]
    filtered, _ = filter_questions_by_topic(unique, locked_chapter=locked)
    if len(filtered) < cfg.total_questions and unique:
        filtered = unique[: cfg.total_questions]
    if not filtered:
        raise HTTPException(
            status_code=400,
            detail="All questions in rag_response.txt failed topic checks for this chapter.",
        )
    # Preserve slot_number order (do not re-pack by enumerate after dedup).
    parsed = sorted(
        filtered,
        key=lambda q: (q.get("slot_number") or 999, q.get("order_index", 0)),
    )[: cfg.total_questions]
    if len(parsed) < cfg.total_questions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"After dedup only {len(parsed)}/{cfg.total_questions} questions remain — "
                "regenerate rag_response.txt with unique slots."
            ),
        )

    exporter = PDFExporter(settings.LOCAL_STORAGE_PATH)
    question_ids, total_marks = [], 0.0
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(Question).where(Question.assessment_id == assessment_id))

    from app.generation.question_pipeline import finalize_question_dict

    for qd in parsed[: cfg.total_questions]:
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
    cfg_dict["class_level"] = cfg.class_level or (doc_row.class_level if doc_row else "") or "10"
    export_urls = exporter.export_assessment(
        questions=parsed[: cfg.total_questions],
        config=cfg_dict,
        assessment_id=assessment_id,
    )
    a.question_ids = question_ids
    a.total_marks = total_marks
    a.pdf_url = export_urls["pdf_url"]
    a.answer_key_url = export_urls["answer_key_url"]
    a.status = "ready" if question_ids else "failed"
    prior_log = list(a.generation_log or [])
    prior_log.append(
        {
            "step": "applied_rag",
            "source": "rag_response.txt",
            "questions_applied": len(question_ids),
            "total_marks": total_marks,
            "note": (
                "Final paper saved from rag_response.txt in correct slot order (Q1 anchor → Q5 fusion). "
                "Earlier trace steps above are from the broken auto-generation run."
            ),
        }
    )
    a.generation_log = prior_log
    await db.commit()
    await db.refresh(a)
    qr = await db.execute(select(Question).where(Question.assessment_id == assessment_id))
    out = _to_out(a)
    out.questions = [_q_to_out(q) for q in _ordered_questions(a, qr.scalars().all())]
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
                figure_spec = enrich_figure_spec(content, None)
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
        if not (cfg_dict.get("class_level") or "").strip():
            cfg_dict["class_level"] = doc_row.class_level or "10"
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
        export_payload, chapter=locked or "circles", re_enrich_figures=True
    )
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
            continue
        fig_type = qd.get("figure_type") or "labeled_diagram"
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


def _q_to_out(q: Question) -> QuestionOut:
    from app.generation.question_pipeline import finalize_question_dict

    qd = finalize_question_dict(
        {
            "content": q.content or "",
            "correct_answer": q.correct_answer or "",
            "explanation": q.explanation or "",
            "options": q.options,
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
