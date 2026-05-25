"""Placeholder document for topic-only (CBSE curriculum) generation."""
from __future__ import annotations

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.demo_user import DEMO_USER_ID
from app.models import Document

CBSE_CURRICULUM_DOCUMENT_ID = "b0000000-0000-4000-8000-00000000cbse01"


async def ensure_cbse_curriculum_document() -> str:
    """Ensure a ready system document exists for topic-only assessments."""
    async with AsyncSessionLocal() as db:
        r = await db.execute(
            select(Document).where(Document.id == CBSE_CURRICULUM_DOCUMENT_ID)
        )
        if r.scalar_one_or_none():
            return CBSE_CURRICULUM_DOCUMENT_ID
        db.add(
            Document(
                id=CBSE_CURRICULUM_DOCUMENT_ID,
                user_id=DEMO_USER_ID,
                filename="CBSE Curriculum (topic-only)",
                original_filename="CBSE Curriculum",
                subject="Mathematics",
                class_level="",
                status="ready",
                total_chunks=0,
                total_pages=0,
                metadata_={"source": "cbse_curriculum", "topic_only": True},
            )
        )
        await db.commit()
    return CBSE_CURRICULUM_DOCUMENT_ID


def is_cbse_curriculum_document(document_id: str | None) -> bool:
    return (document_id or "").strip() == CBSE_CURRICULUM_DOCUMENT_ID
