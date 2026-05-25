"""
Topic isolation — reset RAG file agent state when document/chapter changes.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from app.generation.chapter_concept_classifier import resolve_locked_chapter
from app.generation.rag_file_bridge import (
    PROJECT_ROOT,
    QUERY_FILE,
    RESPONSE_FILE,
    REGEN_PENDING_FILE,
)

logger = logging.getLogger(__name__)

TOPIC_STATE_FILE = PROJECT_ROOT / "rag_topic_state.json"
ARCHIVE_DIR = PROJECT_ROOT / ".rag_archive"


def _read_state() -> dict:
    if not TOPIC_STATE_FILE.exists():
        return {}
    try:
        return json.loads(TOPIC_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_state(state: dict) -> None:
    TOPIC_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def clear_topic_cache(
    *,
    document_id: str,
    filename: str = "",
    topic_focus: str = "",
    context: str = "",
    force_invalidate_response: bool = True,
) -> dict:
    """
    On document/chapter switch: invalidate stale rag_response, archive old pair,
    reset regen pending. Returns new topic state dict.
    """
    locked_chapter, source, confidence = resolve_locked_chapter(
        filename=filename,
        topic_focus=topic_focus,
        context=context,
    )
    prev = _read_state()
    changed = (
        prev.get("document_id") != document_id
        or prev.get("locked_chapter") != locked_chapter
    )

    if changed and force_invalidate_response:
        ARCHIVE_DIR.mkdir(exist_ok=True)
        if RESPONSE_FILE.exists():
            tag = prev.get("locked_chapter", "unknown")
            archive_path = ARCHIVE_DIR / f"rag_response_{tag}_{document_id[:8]}.txt"
            try:
                archive_path.write_text(
                    RESPONSE_FILE.read_text(encoding="utf-8"), encoding="utf-8"
                )
            except OSError:
                pass
            RESPONSE_FILE.unlink(missing_ok=True)
            logger.info(
                "Invalidated stale rag_response.txt (was chapter=%s, now=%s)",
                prev.get("locked_chapter"),
                locked_chapter,
            )
        if REGEN_PENDING_FILE.exists():
            REGEN_PENDING_FILE.unlink(missing_ok=True)

    state = {
        "document_id": document_id,
        "filename": filename,
        "topic_focus": topic_focus,
        "locked_chapter": locked_chapter,
        "locked_chapter_source": source,
        "confidence": confidence,
        "topic_changed": changed,
    }
    _write_state(state)
    return state


def get_current_topic_state() -> dict:
    return _read_state()


def persist_paper_template_id(template_id: str) -> None:
    """Keep semantic-plan template id for integrity/finalize (survives save_topic_map)."""
    tid = (template_id or "").strip()
    if not tid:
        return
    state = _read_state()
    state["paper_template_id"] = tid
    _write_state(state)


def save_topic_map(topic_map: dict) -> None:
    """Merge extracted topic/subtopics into rag_topic_state.json."""
    state = _read_state()
    state["topic_map"] = topic_map
    state["primary_topic"] = topic_map.get("primary_topic", "")
    state["subtopics"] = topic_map.get("subtopics", [])
    state["required_theorems"] = topic_map.get("required_theorems", [])
    state["retrieval_confidence"] = topic_map.get("retrieval_confidence")
    state["generation_mode"] = topic_map.get("generation_mode", "pdf_rich")
    state["use_curriculum_archetypes"] = topic_map.get("use_curriculum_archetypes", False)
    if topic_map.get("memory_prompt"):
        state["memory_prompt"] = topic_map["memory_prompt"]
    if topic_map.get("student_skill_block"):
        state["student_skill_block"] = topic_map["student_skill_block"]
    state["locked_chapter"] = topic_map.get(
        "locked_chapter", state.get("locked_chapter", "generic")
    )
    if topic_map.get("paper_template_id"):
        state["paper_template_id"] = str(topic_map["paper_template_id"]).strip()
    _write_state(state)


def locked_subtopics_header(state: dict) -> str:
    subs = state.get("subtopics") or (state.get("topic_map") or {}).get("subtopics") or []
    if not subs:
        return ""
    lines = "\n".join(f"  - {s}" for s in subs[:12])
    return f"LOCKED SUBTOPICS (cover these from CONTEXT only):\n{lines}\n"


def response_matches_current_topic() -> bool:
    """False only when rag_response is older than the current rag_query."""
    if not RESPONSE_FILE.exists():
        return True
    if not QUERY_FILE.exists():
        return True
    try:
        query_mtime = QUERY_FILE.stat().st_mtime
        resp_mtime = RESPONSE_FILE.stat().st_mtime
        return resp_mtime >= query_mtime - 2.0
    except OSError:
        return False


def locked_chapter_header(state: dict) -> str:
    ch = state.get("locked_chapter", "generic")
    primary = state.get("primary_topic") or (state.get("topic_map") or {}).get(
        "primary_topic", ""
    )
    block = (
        f"LOCKED CHAPTER: {ch} (source: {state.get('locked_chapter_source', '')}, "
        f"confidence: {state.get('confidence', 0):.2f})\n"
        f"document_id: {state.get('document_id', '')}\n"
    )
    if primary:
        block += f"PRIMARY TOPIC: {primary}\n"
    block += locked_subtopics_header(state)
    return block
