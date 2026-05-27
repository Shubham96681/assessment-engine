"""RAG file agent status — for UI + debugging."""
from fastapi import APIRouter, HTTPException

import json

from app.generation.rag_file_bridge import (
    QUERY_FILE,
    PENDING_SIGNAL_FILE,
    REGEN_PENDING_FILE,
    RESPONSE_FILE,
)
from app.generation.rag_capture import (
    auto_apply_capture_if_ready,
    is_rag_response_ready_for_apply,
    read_capture_signal,
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
    capture = read_capture_signal()
    ready, ready_reason = is_rag_response_ready_for_apply(
        capture.get("locked_chapter") or ""
    )
    return {
        "pending": pending,
        "ready_for_apply": ready and not pending,
        "ready_reason": ready_reason if not ready else "",
        "assessment_id": capture.get("assessment_id"),
        "regen_slot": regen_slot,
        "regen_feedback": regen_feedback,
        "query_file": str(QUERY_FILE),
        "response_file": str(RESPONSE_FILE),
        "signal_file": str(PENDING_SIGNAL_FILE),
        "hint": (
            "Say **go capture** in Cursor Agent (or wait — auto-apply runs when rag_response.txt is valid)."
            if pending
            else (
                "rag_response.txt ready — auto-apply will finish the quiz."
                if ready
                else "No pending RAG query."
            )
        ),
    }


@router.post("/finish-capture")
async def finish_rag_capture():
    """
    Validate rag_response.txt and apply to the assessment from the capture signal.
    Used by Cursor agent / scripts after writing rag_response.txt.
    """
    ok, reason = is_rag_response_ready_for_apply()
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"rag_response.txt not ready: {reason}",
        )
    data = await auto_apply_capture_if_ready()
    if not data:
        sig = read_capture_signal()
        aid = sig.get("assessment_id")
        if not aid:
            raise HTTPException(
                status_code=400,
                detail="No assessment_id in capture signal — click Generate first.",
            )
        raise HTTPException(
            status_code=409,
            detail=(
                f"Assessment {aid} is not in generating/failed state, or apply failed. "
                "Check backend logs."
            ),
        )
    return {
        "ok": True,
        "assessment_id": data.get("id"),
        "status": data.get("status"),
        "questions": len(data.get("questions") or []),
        "total_marks": data.get("total_marks"),
    }
