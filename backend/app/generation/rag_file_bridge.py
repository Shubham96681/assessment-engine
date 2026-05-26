"""
RAG file bridge — writes rag_query.txt, waits for rag_response.txt (Cursor / local agent).

Project root files:
  rag_query.txt   — CONTEXT + QUESTION
  rag_response.txt — ANSWER + SOURCES USED
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class RagAgentResponseMissing(RuntimeError):
    """Raised when RAG file agent mode is on but rag_response.txt was not produced in time."""


# assessment/ (repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
QUERY_FILE = PROJECT_ROOT / "rag_query.txt"
RESPONSE_FILE = PROJECT_ROOT / "rag_response.txt"
REGEN_PENDING_FILE = PROJECT_ROOT / "rag_regen_pending.json"
PENDING_SIGNAL_FILE = PROJECT_ROOT / ".cursor" / "rag_pending.json"

# Windows mtime can be same-second as query write
MTIME_TOLERANCE_SEC = 2.0


def _has_json_array(text: str) -> bool:
    if not text or "[" not in text or "]" not in text:
        return False
    start = text.find("[")
    end = text.rfind("]") + 1
    try:
        data = json.loads(text[start:end])
        return isinstance(data, list) and len(data) > 0
    except json.JSONDecodeError:
        return False


def write_rag_query(
    context: str,
    question: str,
    *,
    document_meta: Optional[dict] = None,
    retrieval_query: str = "",
    exclude_prior_stems: Optional[list] = None,
    topic_state: Optional[dict] = None,
    uniqueness_block: str = "",
    compact_query: bool = False,
) -> None:
    """Write query file; invalidates stale rag_response when topic_state marks a chapter change."""
    t0 = time.time()
    parts: list[str] = []
    if topic_state:
        from app.generation.topic_isolation import locked_chapter_header

        parts.append(locked_chapter_header(topic_state))
        if topic_state.get("topic_changed"):
            parts.append(
                "TOPIC CHANGED: previous rag_response.txt was cleared — write a NEW response.\n"
            )
    if document_meta and topic_state:
        meta_id = str(document_meta.get("document_id") or "").strip()
        state_id = str(topic_state.get("document_id") or "").strip()
        if meta_id and state_id and meta_id != state_id:
            parts.append(
                "DOCUMENT MISMATCH WARNING: rag_query document_id does not match "
                f"current topic state ({state_id}). Use the SELECTED DOCUMENT below only "
                "if this assessment was created for that PDF.\n"
            )
    if document_meta:
        parts.append("SELECTED DOCUMENT:")
        for key in (
            "document_id",
            "filename",
            "subject",
            "class_level",
            "topic_focus",
            "exclude_topics",
        ):
            val = document_meta.get(key)
            if val:
                parts.append(f"{key}: {val}")
        parts.append("")
    if retrieval_query.strip() and not compact_query:
        parts.append(f"RETRIEVAL QUERY:\n{retrieval_query.strip()}\n")
    if compact_query:
        parts.append(
            "COMPACT PROMPT MODE: follow the QUESTION block only. "
            "Prior stems and rejection corpus are omitted; backend dedup still applies after parse.\n"
        )
    if exclude_prior_stems and not compact_query:
        parts.append("PRIOR QUESTIONS — DO NOT REPEAT OR PARAPHRASE:")
        for stem in exclude_prior_stems[:25]:
            if stem:
                parts.append(f"- {str(stem)[:220]}")
        parts.append("")
        try:
            from app.generation.cognitive_graph_validator import prior_graphs_from_stems

            graphs = prior_graphs_from_stems(exclude_prior_stems)
            if graphs:
                parts.append(
                    "PRIOR REASONING GRAPHS — DO NOT REUSE (new labels still forbidden):"
                )
                for g in graphs[:15]:
                    parts.append(f"- {g}")
                parts.append("")
        except Exception:
            pass
    if uniqueness_block and uniqueness_block.strip() and not compact_query:
        parts.append(uniqueness_block.strip())
        parts.append("")
    if compact_query:
        ctx_body = (context or "").strip()
        if ctx_body:
            parts.append(f"CONTEXT:\n{ctx_body[:4000]}\n")
        else:
            parts.append(
                "CONTEXT:\nCurriculum mode — use the QUESTION blueprint only; "
                "invent fresh Class 10 quadratic stems.\n"
            )
    else:
        parts.append(f"CONTEXT:\n{context.strip()}\n")
    parts.append(f"QUESTION:\n{question.strip()}\n")
    content = "\n".join(parts)
    QUERY_FILE.write_text(content, encoding="utf-8")
    _signal_rag_pending()
    logger.info("Wrote %s in %.0f ms", QUERY_FILE.name, (time.time() - t0) * 1000)


def _signal_rag_pending() -> None:
    """Notify Cursor hooks / watcher that a response is required."""
    try:
        PENDING_SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        PENDING_SIGNAL_FILE.write_text(
            json.dumps(
                {
                    "pending": True,
                    "query_file": str(QUERY_FILE),
                    "written_at": time.time(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as e:
        logger.debug("Could not write rag pending signal: %s", e)


def _clear_rag_pending() -> None:
    try:
        if PENDING_SIGNAL_FILE.exists():
            PENDING_SIGNAL_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def read_rag_response() -> Optional[str]:
    if not RESPONSE_FILE.exists():
        return None
    return RESPONSE_FILE.read_text(encoding="utf-8").strip()


def parse_rag_response(raw: str) -> tuple[str, str]:
    """Extract ANSWER and SOURCES USED sections."""
    answer = raw
    sources = ""
    if "ANSWER:" in raw:
        parts = raw.split("SOURCES USED:", 1)
        answer = parts[0].replace("ANSWER:", "", 1).strip()
        if len(parts) > 1:
            sources = parts[1].strip()
    return answer, sources


def _try_read_valid_response(query_mtime: float) -> Optional[str]:
    if not RESPONSE_FILE.exists():
        return None
    resp_mtime = RESPONSE_FILE.stat().st_mtime
    if resp_mtime < query_mtime - MTIME_TOLERANCE_SEC:
        return None
    raw = read_rag_response()
    if raw and len(raw) > 20 and _has_json_array(raw):
        return raw
    return None


def _wait_for_response_sync(
    timeout: float,
    poll: float,
    query_mtime: float,
    *,
    allow_stale_fallback: bool = True,
) -> Optional[str]:
    # Immediate check — response already saved after rag_query.txt appeared
    immediate = _try_read_valid_response(query_mtime)
    if immediate:
        return immediate

    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = _try_read_valid_response(query_mtime)
        if raw:
            return raw
        time.sleep(poll)

    strict = settings.RAG_FILE_AGENT_ONLY
    if allow_stale_fallback and not strict:
        from app.generation.topic_isolation import response_matches_current_topic

        if response_matches_current_topic():
            raw = read_rag_response()
            if raw and _has_json_array(raw):
                logger.info("Using existing rag_response.txt after wait timeout")
                return raw
        else:
            logger.warning(
                "Stale rag_response.txt ignored — file is older than rag_query.txt; "
                "write a new rag_response.txt after the query updates"
            )
    elif strict:
        logger.error(
            "RAG file agent timeout — Cursor must write rag_response.txt (enable Hooks, keep Agent chat open)"
        )
    return None


def extract_single_question_json(raw: str, slot_id: str) -> Optional[str]:
    """Return JSON array string with one item matching slot id (or first item)."""
    answer, _ = parse_rag_response(raw)
    start = answer.find("[")
    end = answer.rfind("]") + 1
    if start == -1 or end <= start:
        return None
    try:
        items = json.loads(answer[start:end])
    except json.JSONDecodeError:
        return None
    if not isinstance(items, list) or not items:
        return None
    target = str(slot_id)
    for item in items:
        if str(item.get("id")) == target:
            return json.dumps([item], ensure_ascii=False)
    # Never reuse another slot's question when id does not match
    logger.warning(
        "rag_response has no item with id=%s (have ids %s) — slot regen must not reuse wrong slot",
        target,
        [str(it.get("id")) for it in items],
    )
    return None


def write_regen_pending(slot_index: int, reject_feedback: str, rejected_stem: str) -> None:
    """Signal to UI/Cursor that a slot regen is waiting."""
    payload = {
        "status": "pending",
        "slot_index": slot_index,
        "slot_number": slot_index + 1,
        "reject_feedback": reject_feedback,
        "rejected_stem_preview": (rejected_stem or "")[:300],
    }
    REGEN_PENDING_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clear_regen_pending() -> None:
    if REGEN_PENDING_FILE.exists():
        REGEN_PENDING_FILE.unlink(missing_ok=True)


async def request_rag_file_response(
    context: str,
    question: str,
    *,
    document_meta: Optional[dict] = None,
    retrieval_query: str = "",
    exclude_prior_stems: Optional[list] = None,
    topic_state: Optional[dict] = None,
    generation_attempt: int = 1,
    generation_num: int = 1,
    uniqueness_block: str = "",
) -> Optional[str]:
    """
    Write rag_query.txt and poll rag_response.txt until the agent fills it in.
    Returns parsed JSON answer string, or None if missing/invalid.
    """
    ts = topic_state or {}
    compact = bool(ts.get("compact_rag_query"))
    ub = uniqueness_block
    if not compact and not ub and exclude_prior_stems:
        try:
            from app.generation.paper_uniqueness import build_rag_uniqueness_block

            ub = build_rag_uniqueness_block(
                generation_num=generation_num,
                prior_stems=list(exclude_prior_stems),
                chapter=str(ts.get("locked_chapter") or "circles"),
                question_count=int(ts.get("question_count") or 5),
                full_hard=bool(ts.get("full_hard", True)),
            )
        except Exception:
            ub = ""
    write_rag_query(
        context,
        question,
        document_meta=document_meta,
        retrieval_query=retrieval_query,
        exclude_prior_stems=None if compact else exclude_prior_stems,
        topic_state=topic_state,
        uniqueness_block="" if compact else ub,
        compact_query=compact,
    )
    query_mtime = QUERY_FILE.stat().st_mtime
    if generation_attempt > 1:
        timeout = getattr(
            settings,
            "RAG_FILE_RETRY_TIMEOUT_SECONDS",
            min(45, settings.RAG_FILE_TIMEOUT_SECONDS),
        )
    else:
        timeout = settings.RAG_FILE_TIMEOUT_SECONDS
    poll = settings.RAG_FILE_POLL_INTERVAL_SECONDS

    logger.info(
        "Waiting for rag_response.txt (timeout %ss, attempt %d) — save AFTER rag_query.txt updates",
        timeout,
        generation_attempt,
    )
    allow_stale = not settings.RAG_FILE_AGENT_ONLY
    raw = await asyncio.to_thread(
        _wait_for_response_sync,
        timeout,
        poll,
        query_mtime,
        allow_stale_fallback=allow_stale,
    )
    if raw:
        _clear_rag_pending()
        answer, sources = parse_rag_response(raw)
        start = answer.find("[")
        end = answer.rfind("]") + 1
        if start != -1 and end > start:
            try:
                items = json.loads(answer[start:end])
                if isinstance(items, list) and len(items) == 1 and items[0].get("id"):
                    logger.warning(
                        "rag_response has 1 item (id=%s) — full papers need ids 1..N; "
                        "other slots need per-slot Cursor regen or a full rag_response with all ids",
                        items[0].get("id"),
                    )
            except json.JSONDecodeError:
                pass
        logger.info("Received rag_response.txt (%d chars answer)", len(answer))
        if sources:
            logger.debug("Sources: %s", sources[:200])
        locked = str(ts.get("locked_chapter") or "").strip().lower()
        if locked == "quadratic":
            from app.core.config import settings as app_settings
            from app.generation.quadratic_math_gate import validate_rag_answer_json

            if app_settings.ENABLE_QUADRATIC_MATH_VERIFY:
                try:
                    validate_rag_answer_json(answer, chapter=locked)
                except ValueError as exc:
                    logger.error(
                        "rag_response.txt failed quadratic math verification — "
                        "fix rag_response.txt before apply: %s",
                        exc,
                    )
                    if app_settings.QUADRATIC_MATH_VERIFY_BLOCK_DELIVERY:
                        return None
        return answer
    if settings.RAG_FILE_AGENT_ONLY:
        logger.error(
            "No valid rag_response.txt after %.0fs — Cursor agent required (no local fallback)",
            timeout,
        )
    else:
        logger.warning("No valid rag_response.txt — will use local question builder")
    return None


async def request_rag_slot_regeneration(
    context: str,
    question: str,
    *,
    slot_index: int,
    document_meta: Optional[dict] = None,
    retrieval_query: str = "",
    exclude_prior_stems: Optional[list] = None,
    reject_feedback: str = "",
    rejected_stem: str = "",
    topic_state: Optional[dict] = None,
) -> Optional[str]:
    """
    Write rag_query.txt for ONE rejected slot; wait for Cursor to update rag_response.txt.
    Returns JSON array string with a single question object, or None.
    """
    write_regen_pending(slot_index, reject_feedback, rejected_stem)
    write_rag_query(
        context,
        question,
        document_meta=document_meta,
        retrieval_query=retrieval_query or "QUALITY REGENERATION slot fix",
        exclude_prior_stems=exclude_prior_stems,
        topic_state=topic_state,
    )
    query_mtime = QUERY_FILE.stat().st_mtime
    timeout = getattr(
        settings,
        "RAG_FILE_SLOT_REGEN_TIMEOUT_SECONDS",
        settings.RAG_FILE_TIMEOUT_SECONDS,
    )
    poll = settings.RAG_FILE_POLL_INTERVAL_SECONDS

    logger.info(
        "Waiting for Cursor to regenerate slot %d in rag_response.txt (timeout %ss)",
        slot_index + 1,
        timeout,
    )
    raw = await asyncio.to_thread(
        _wait_for_response_sync,
        timeout,
        poll,
        query_mtime,
        allow_stale_fallback=False,
    )
    clear_regen_pending()
    if not raw:
        logger.warning("No fresh rag_response.txt for slot %d regen", slot_index + 1)
        return None
    _clear_rag_pending()
    slot_id = str(slot_index + 1)
    single = extract_single_question_json(raw, slot_id)
    if single:
        logger.info("Cursor regen: parsed slot %s from rag_response.txt", slot_id)
        return single
    logger.warning("rag_response.txt had no valid single-question JSON for slot %s", slot_id)
    return None
