"""Chapter / topic catalog — selectable after CBSE ingestion."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.core.cbse_curriculum_doc import CBSE_CURRICULUM_DOCUMENT_ID
from app.generation.chapter_catalog import (
    build_chapter_topic_profile,
    list_available_chapters,
    _relevant_question_types,
)
from app.schemas import TopicProfileOut

router = APIRouter(prefix="/chapters", tags=["Chapters"])


@router.get("")
async def list_chapters():
    """All topics available after CBSE ingestion (with stem counts)."""
    chapters = list_available_chapters()
    return {
        "chapters": chapters,
        "count": len(chapters),
        "curriculum_document_id": CBSE_CURRICULUM_DOCUMENT_ID,
    }


@router.get("/{chapter_key}/profile", response_model=TopicProfileOut)
async def get_chapter_profile(
    chapter_key: str,
    topic_focus: Optional[str] = None,
    class_level: Optional[str] = None,
):
    """Topic profile without uploading a PDF."""
    key = chapter_key.strip().lower()
    chapters = {c["chapter_key"] for c in list_available_chapters()}
    if key not in chapters:
        raise HTTPException(status_code=404, detail=f"Unknown chapter: {chapter_key}")
    profile = build_chapter_topic_profile(
        key,
        class_level=class_level or "",
        topic_focus=topic_focus or "",
    )
    return TopicProfileOut(**profile)


@router.get("/{chapter_key}/question-types")
async def get_chapter_question_types(chapter_key: str):
    """Question types relevant to the selected topic."""
    key = chapter_key.strip().lower()
    types = _relevant_question_types(key)
    return {"chapter_key": key, "question_types": types}
