"""RAG file agent status — for UI + debugging."""
from fastapi import APIRouter

import json

from app.generation.rag_file_bridge import (
    QUERY_FILE,
    PENDING_SIGNAL_FILE,
    REGEN_PENDING_FILE,
    RESPONSE_FILE,
)
from app.generation.topic_isolation import response_matches_current_topic

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/pending")
async def rag_pending_status():
    """Whether rag_query.txt still needs rag_response.txt."""
    query_exists = QUERY_FILE.exists()
    response_exists = RESPONSE_FILE.exists()
    pending = query_exists and (
        not response_exists or not response_matches_current_topic()
    )
    regen_slot = None
    regen_feedback = None
    if REGEN_PENDING_FILE.exists():
        try:
            regen = json.loads(REGEN_PENDING_FILE.read_text(encoding="utf-8"))
            regen_slot = regen.get("slot_number") or (
                int(regen.get("slot_index", -1)) + 1
                if regen.get("slot_index") is not None
                else None
            )
            regen_feedback = regen.get("reject_feedback")
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
    return {
        "pending": pending,
        "regen_slot": regen_slot,
        "regen_feedback": regen_feedback,
        "query_file": str(QUERY_FILE),
        "response_file": str(RESPONSE_FILE),
        "signal_file": str(PENDING_SIGNAL_FILE),
        "hint": (
            "Open a Cursor Agent chat for this repo. Hooks will re-prompt on agent stop "
            "while pending. Or paste: RAG_FILE_AGENT: process rag_query.txt"
            if pending
            else "No pending RAG query."
        ),
    }
