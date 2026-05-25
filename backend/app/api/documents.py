"""Documents API — No Auth, synchronous ingestion"""
import asyncio
import os, shutil, logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Document
from app.schemas import DocumentOut, TopicProfileOut
from app.core.config import settings
from app.core.demo_user import DEMO_USER_ID
from app.rag.ingestion import PDFIngestionPipeline

router = APIRouter()
logger = logging.getLogger(__name__)
UPLOAD_DIR = os.path.join(settings.LOCAL_STORAGE_PATH, "pdfs")


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject: str = Form(""),
    class_level: str = Form(""),
    page_start: int | None = Form(None),
    page_end: int | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{file.filename.replace(' ', '_')}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = Document(
        user_id=DEMO_USER_ID,
        filename=safe_name,
        original_filename=file.filename,
        file_path=file_path,
        subject=subject,
        class_level=class_level,
        status="processing",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    doc_id = doc.id

    background_tasks.add_task(_ingest, file_path, doc_id, subject, class_level, page_start, page_end)
    return doc


def _run_ingest_pipeline(
    file_path, document_id, subject, class_level, page_start, page_end
):
    """Run ingestion in a worker thread so /documents and /health stay responsive."""
    import asyncio
    pipeline = PDFIngestionPipeline()
    return asyncio.run(
        pipeline.process(
            file_path=file_path,
            document_id=document_id,
            user_id=DEMO_USER_ID,
            metadata={"subject": subject, "class_level": class_level},
            page_start=page_start,
            page_end=page_end,
        )
    )


async def _ingest(file_path, document_id, subject, class_level, page_start, page_end):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            result = await asyncio.to_thread(
                _run_ingest_pipeline,
                file_path,
                document_id,
                subject,
                class_level,
                page_start,
                page_end,
            )
            r = await db.execute(select(Document).where(Document.id == document_id))
            doc = r.scalar_one()
            doc.status = result["status"]
            doc.total_chunks = result["total_chunks"]
            doc.total_pages = result["total_pages"]
            await db.commit()
            logger.info(f"Document {document_id} ingested: {result['total_chunks']} chunks")
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            r = await db.execute(select(Document).where(Document.id == document_id))
            doc = r.scalar_one_or_none()
            if doc:
                doc.status = "failed"
                doc.error_message = str(e)[:500]
                await db.commit()


@router.get("", response_model=List[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=12)
    r = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = list(r.scalars().all())
    changed = False
    for doc in docs:
        if doc.status != "processing":
            continue
        created = doc.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created < cutoff:
            doc.status = "failed"
            doc.error_message = (
                "Indexing timed out (>12 min). Re-upload with a page range (e.g. 10 pages only)."
            )
            changed = True
    if changed:
        await db.commit()
    return docs


@router.get("/{document_id}/topic-profile", response_model=TopicProfileOut)
async def get_document_topic_profile(
    document_id: str,
    topic_focus: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Extract primary topic and subtopics from indexed PDF chunks (multi-agent topic agent)."""
    from app.generation.topic_extractor import extract_document_topic_profile

    r = await db.execute(select(Document).where(Document.id == document_id))
    doc = r.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in database")
    if doc.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready (status={doc.status}). Wait for indexing to finish.",
        )
    try:
        profile = await extract_document_topic_profile(
            document_id,
            filename=doc.filename or "",
            topic_focus=topic_focus,
            subject=doc.subject or "Mathematics",
            class_level=doc.class_level or "",
        )
    except Exception as e:
        logger.exception("topic-profile extract failed for %s", document_id)
        raise HTTPException(
            status_code=503,
            detail=f"Topic extraction failed: {str(e)[:200]}. Upload/index the PDF first, then restart the backend.",
        ) from e

    from app.generation.retrieval_confidence import compute_retrieval_confidence
    from app.rag.retriever import HybridRetriever
    from app.generation.content_profile import build_content_profile, build_rag_retrieval_query

    locked = profile.get("locked_chapter", "generic")
    try:
        cp = build_content_profile(
            topic_focus=topic_focus,
            filename=doc.filename or "",
            context="",
            subject=doc.subject or "Mathematics",
            class_level=doc.class_level or "",
        )
        cp.chapter_key = locked
        q = build_rag_retrieval_query(
            task={"type": "MCQ", "difficulty": "medium"},
            profile=cp,
            config_topic_focus=topic_focus,
        )
        chunks = await HybridRetriever().retrieve(
            q, document_id, locked_chapter=locked
        )
        rmeta = compute_retrieval_confidence(chunks)
        profile["retrieval_confidence"] = rmeta["score"]
        profile["generation_mode"] = rmeta["mode"]
    except Exception as e:
        logger.warning("topic-profile retrieval probe failed: %s", e)
        profile["retrieval_confidence"] = 0.0
        profile["generation_mode"] = "curriculum_fallback"

    profile["total_chunks_db"] = doc.total_chunks or 0
    try:
        return TopicProfileOut(**profile)
    except Exception as e:
        logger.exception("topic-profile response validation failed")
        raise HTTPException(status_code=500, detail=str(e)[:300]) from e


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Document).where(Document.id == document_id))
    doc = r.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Document).where(Document.id == document_id))
    doc = r.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await db.delete(doc)
    return {"message": "Deleted"}
