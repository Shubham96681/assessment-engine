"""
RAG capture automation — ties Generate → rag_query.txt → rag_response.txt → apply.

Writes assessment_id into `.cursor/rag_pending.json` so the Cursor agent and
background auto-apply know which quiz to finish.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings
from app.generation.rag_file_bridge import (
    ARCHIVE_DIR,
    PENDING_SIGNAL_FILE,
    PROJECT_ROOT,
    QUERY_FILE,
    RESPONSE_FILE,
    parse_rag_response,
    read_rag_response,
)

logger = logging.getLogger(__name__)

_CAPTURE: Dict[str, Any] = {}


def set_capture_context(
    *,
    assessment_id: str,
    delivery_count: int = 5,
    locked_chapter: str = "",
    title: str = "",
) -> None:
    """Called when background generation starts — links query/response to this assessment."""
    _CAPTURE.clear()
    _CAPTURE.update(
        {
            "assessment_id": str(assessment_id),
            "delivery_count": int(delivery_count),
            "locked_chapter": (locked_chapter or "").strip().lower(),
            "title": (title or "").strip(),
            "started_at": time.time(),
        }
    )
    _write_pending_signal()


def read_capture_signal() -> Dict[str, Any]:
    if PENDING_SIGNAL_FILE.exists():
        try:
            data = json.loads(PENDING_SIGNAL_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_CAPTURE)


def clear_capture_context() -> None:
    _CAPTURE.clear()
    try:
        if PENDING_SIGNAL_FILE.exists():
            PENDING_SIGNAL_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _write_pending_signal() -> None:
    from app.generation.rag_file_bridge import _signal_rag_pending

    try:
        PENDING_SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pending": True,
            "query_file": str(QUERY_FILE),
            "written_at": time.time(),
            **{k: v for k, v in _CAPTURE.items() if v is not None},
        }
        if QUERY_FILE.exists():
            payload["query_mtime"] = QUERY_FILE.stat().st_mtime
        PENDING_SIGNAL_FILE.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        logger.debug("Could not write rag pending signal: %s", e)
    else:
        _signal_rag_pending()


def archive_rejected_response(reason: str) -> None:
    """Move invalid rag_response.txt aside so the wait loop does not re-read it."""
    if not RESPONSE_FILE.exists():
        return
    try:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        tag = int(time.time())
        dest = ARCHIVE_DIR / f"rag_response_rejected_{tag}.txt"
        raw = RESPONSE_FILE.read_text(encoding="utf-8")
        dest.write_text(
            f"# REJECTED: {reason}\n\n{raw}",
            encoding="utf-8",
        )
        RESPONSE_FILE.unlink(missing_ok=True)
        logger.info("Archived rejected rag_response.txt → %s", dest.name)
    except OSError as e:
        logger.warning("Could not archive rejected rag_response: %s", e)
    _write_pending_signal()


def is_rag_response_ready_for_apply(
    locked_chapter: str = "",
) -> Tuple[bool, str]:
    """
    True when rag_response.txt exists, is newer than rag_query, has JSON,
    and passes quadratic math verification when applicable.
    """
    from app.generation.topic_isolation import response_matches_current_topic

    if not RESPONSE_FILE.exists():
        return False, "rag_response.txt missing"
    if not response_matches_current_topic():
        return False, "rag_response older than rag_query"
    raw = read_rag_response()
    if not raw or len(raw) < 20:
        return False, "rag_response empty"
    answer, _ = parse_rag_response(raw)
    if "[" not in answer or "]" not in answer:
        return False, "no JSON array in ANSWER"
    chapter = (locked_chapter or read_capture_signal().get("locked_chapter") or "").lower()
    if chapter == "quadratic" and settings.ENABLE_QUADRATIC_MATH_VERIFY:
        from app.generation.quadratic_math_gate import validate_rag_answer_json

        try:
            validate_rag_answer_json(answer, chapter=chapter)
        except ValueError as exc:
            return False, str(exc)
    return True, ""


async def auto_apply_capture_if_ready() -> Optional[Dict[str, Any]]:
    """
    POST apply-rag-response for the assessment in the capture signal when response is valid.
    Returns API JSON on success, None if nothing to do.
    """
    if not settings.RAG_AUTO_APPLY_ON_CAPTURE:
        return None
    sig = read_capture_signal()
    aid = sig.get("assessment_id")
    if not aid:
        return None
    ok, reason = is_rag_response_ready_for_apply(sig.get("locked_chapter") or "")
    if not ok:
        return None

    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models import Assessment

    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Assessment).where(Assessment.id == aid))
        a = r.scalar_one_or_none()
        if not a:
            return None
        if a.status not in ("generating", "failed"):
            return None

    import httpx

    base = settings.API_INTERNAL_BASE_URL.rstrip("/")
    url = f"{base}/api/v1/assessments/{aid}/apply-rag-response"
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, params={"force": "true"})
            if resp.status_code >= 400:
                logger.warning(
                    "auto-apply capture failed %s: %s",
                    resp.status_code,
                    resp.text[:300],
                )
                return None
            data = resp.json()
            logger.info(
                "auto-apply capture: assessment %s → status=%s questions=%s",
                aid[:8],
                data.get("status"),
                len(data.get("questions") or []),
            )
            if data.get("status") == "ready":
                clear_capture_context()
            return data
    except Exception as e:
        logger.warning("auto-apply capture HTTP error: %s", e)
        return None
