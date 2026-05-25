"""RAG file agent status — for UI + debugging."""
from fastapi import APIRouter

from app.generation.rag_file_bridge import QUERY_FILE, RESPONSE_FILE, PENDING_SIGNAL_FILE
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
    return {
        "pending": pending,
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
