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
from app.core.vector_store import init_qdrant_collections
from app.api.router import api_router
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Assessment Engine (No-Auth Mode)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(
            "ALTER TABLE assessments ADD COLUMN IF NOT EXISTS generation_log JSONB DEFAULT '[]'::jsonb"
        ))
    logger.info("Database tables ready")
    await ensure_demo_user()
    logger.info("Demo user ready")
    try:
        await init_qdrant_collections()
        logger.info("Qdrant collections ready")
    except Exception as e:
        logger.warning(f"Qdrant not available (will use local fallback): {e}")
    for d in ["pdfs", "figures", "exports"]:
        os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, d), exist_ok=True)
    logger.info("Storage directories ready")
    logger.info(
        "LLM: RAG_FILE_AGENT=%s RAG_ONLY=%s GROQ=%s model=%s",
        settings.RAG_FILE_AGENT_ENABLED,
        settings.RAG_FILE_AGENT_ONLY,
        bool(settings.GROQ_API_KEY),
        settings.GROQ_MODEL,
    )

    async def _preload_embeddings():
        try:
            from app.rag.embeddings import preload_local_embedding_model
            await preload_local_embedding_model()
        except Exception as e:
            logger.warning(f"Embedding preload skipped: {e}")

    asyncio.create_task(_preload_embeddings())
    asyncio.create_task(_repair_stale_generating_assessments())
    yield
    logger.info("Shutting down...")


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="uploads")
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "mode": "no-auth"}
