"""
Assessment Engine — Simplified FastAPI (No Auth, No Redis/Celery)
All operations run synchronously in-process.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import asyncio
import logging
import os

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base
from app.core.demo_user import ensure_demo_user
from app.core.vector_store import init_vector_store
from app.api.router import api_router
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Assessment Engine (No-Auth Mode)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.DATABASE_URL.startswith("postgresql"):
            await conn.execute(text(
                "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS generation_log JSONB DEFAULT '[]'::jsonb"
            ))
    logger.info("Database tables ready (%s)", settings.DATABASE_URL.split("://", 1)[0])
    await ensure_demo_user()
    logger.info("Demo user ready")
    try:
        from app.core.cbse_curriculum_doc import ensure_cbse_curriculum_document

        await ensure_cbse_curriculum_document()
    except Exception as e:
        logger.warning("CBSE curriculum document setup skipped: %s", e)
    try:
        await init_vector_store()
        logger.info("Vector store ready (%s)", settings.VECTOR_STORE_BACKEND)
    except Exception as e:
        logger.warning("Vector store init failed: %s", e)
    for d in ["pdfs", "figures", "exports"]:
        os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, d), exist_ok=True)
    logger.info("Storage directories ready")
    logger.info(
        "LLM: RAG_FILE_AGENT=%s RAG_ONLY=%s LOCAL_FALLBACK=%s poll=%.2fs timeout=%ss retries=%s",
        settings.RAG_FILE_AGENT_ENABLED,
        settings.RAG_FILE_AGENT_ONLY,
        getattr(settings, "ENABLE_LOCAL_LLM_FALLBACK", False),
        settings.RAG_FILE_POLL_INTERVAL_SECONDS,
        settings.RAG_FILE_TIMEOUT_SECONDS,
        settings.RAG_FILE_MAX_RETRIES,
    )
    if settings.RAG_FILE_AGENT_ENABLED:
        logger.info(
            "Cursor: enable Hooks in Settings; keep Agent chat open; rules at .cursor/rules/rag-response-agent.mdc"
        )

    async def _preload_embeddings():
        try:
            from app.rag.embeddings import preload_local_embedding_model
            await preload_local_embedding_model()
        except Exception as e:
            logger.warning(f"Embedding preload skipped: {e}")

    asyncio.create_task(_preload_embeddings())
    asyncio.create_task(_repair_stale_generating_assessments())
    if settings.RAG_FILE_AGENT_ENABLED and settings.RAG_AUTO_APPLY_ON_CAPTURE:
        asyncio.create_task(_rag_capture_auto_apply_loop())
    if settings.ENABLE_CBSE_REFERENCE and settings.CBSE_REFERENCE_AUTO_BUILD:
        asyncio.create_task(_build_cbse_reference_if_needed())
    if settings.ENABLE_GATE_REFERENCE and settings.GATE_REFERENCE_AUTO_BUILD:
        asyncio.create_task(_build_gate_reference_if_needed())
    if settings.ENABLE_GATE_BENCHMARK and settings.GATE_BENCHMARK_AUTO_BUILD:
        asyncio.create_task(_build_gate_benchmark_if_needed())
    yield
    logger.info("Shutting down...")


async def _build_cbse_reference_if_needed():
    """Background index of CBSE_QuestionPapers by chapter (first startup or stale PDFs)."""
    await asyncio.sleep(3)
    try:
        from app.generation.cbse_reference_ingest import build_cbse_reference_index

        man = await build_cbse_reference_index(force=False)
        if man.get("status") == "built":
            logger.info(
                "CBSE reference index ready: %s stems, chapters=%s",
                man.get("stem_count", 0),
                list((man.get("chapters") or {}).keys())[:8],
            )
    except Exception as e:
        logger.warning("CBSE reference auto-build skipped: %s", e)


async def _build_gate_reference_if_needed():
    await asyncio.sleep(5)
    try:
        from app.generation.gate_reference_ingest import build_gate_reference_index

        man = await build_gate_reference_index(force=False)
        if man.get("status") == "built":
            logger.info(
                "GATE reference index ready: %s stems, chapters=%s",
                man.get("stem_count", 0),
                list((man.get("chapters") or {}).keys())[:8],
            )
    except Exception as e:
        logger.warning("GATE reference auto-build skipped: %s", e)


async def _build_gate_benchmark_if_needed():
    await asyncio.sleep(4)
    try:
        from app.generation.gate_benchmark import load_gate_benchmark

        snap = load_gate_benchmark(rebuild_if_stale=True)
        logger.info(
            "GATE benchmark ready: %s PDFs, %s stems",
            snap.pdf_count,
            snap.stem_count,
        )
    except Exception as e:
        logger.warning("GATE benchmark auto-build skipped: %s", e)


async def _rag_capture_auto_apply_loop():
    """When rag_response.txt validates, finish the generating/failed assessment automatically."""
    from app.generation.rag_capture import auto_apply_capture_if_ready

    await asyncio.sleep(3)
    while True:
        try:
            await auto_apply_capture_if_ready()
        except Exception as e:
            logger.debug("rag capture auto-apply tick: %s", e)
        await asyncio.sleep(2.0)


async def _repair_stale_generating_assessments():
    """Mark assessments stuck in 'generating' (e.g. server reload) as failed."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models import Assessment

    await asyncio.sleep(2)
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=8)
        async with AsyncSessionLocal() as db:
            r = await db.execute(
                select(Assessment).where(Assessment.status == "generating")
            )
            stale = []
            for a in r.scalars().all():
                created = a.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created < cutoff:
                    stale.append(a)
            for a in stale:
                a.status = "failed"
            if stale:
                await db.commit()
                logger.warning("Marked %s stale 'generating' assessments as failed", len(stale))
    except Exception as e:
        logger.warning("Stale assessment repair skipped: %s", e)


app = FastAPI(
    title="Assessment Engine API",
    description="AI-Powered RAG Assessment Generation — No-Auth Dev Mode",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
_cors_kwargs: dict = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.DEBUG:
    # Next.js may use 3000–3002+ when ports are busy
    _cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    _cors_kwargs["allow_origins"] = _cors_origins
else:
    _cors_kwargs["allow_origins"] = _cors_origins

app.add_middleware(CORSMiddleware, **_cors_kwargs)

os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="uploads")
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "mode": "no-auth",
        "database": settings.DATABASE_URL.split("://", 1)[0],
        "vector_store": settings.VECTOR_STORE_BACKEND,
    }
