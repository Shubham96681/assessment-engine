"""
Jinja2 templates for canonical rag_response.txt (ANSWER JSON + SOURCES USED).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "templates"

_REQUIRED_KEYS = ("id", "type", "question", "marks", "correct_answer")


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _normalize_question_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    from app.generation.question_text import ensure_plain_text

    qtext = (
        raw.get("question")
        or raw.get("content")
        or raw.get("stem")
        or ""
    )
    ans = raw.get("correct_answer") or raw.get("answer") or ""
    out: Dict[str, Any] = {
        "id": str(raw.get("id") or raw.get("slot_number") or ""),
        "type": str(raw.get("type") or raw.get("question_type") or "LongAnswer"),
        "question": ensure_plain_text(str(qtext)),
        "marks": float(raw.get("marks") or 1),
        "correct_answer": ensure_plain_text(str(ans)),
    }
    if raw.get("explanation"):
        out["explanation"] = ensure_plain_text(str(raw["explanation"]))
    if raw.get("options"):
        out["options"] = raw["options"]
    if raw.get("theorem_tags"):
        out["theorem_tags"] = raw["theorem_tags"]
    if raw.get("cognitive_type"):
        out["cognitive_type"] = raw["cognitive_type"]
    return out


def extract_json_array(raw: str) -> List[Dict[str, Any]]:
    """Parse JSON array from ANSWER section or bare array text."""
    text = raw or ""
    if "ANSWER:" in text:
        text = text.split("ANSWER:", 1)[1]
        if "SOURCES USED:" in text:
            text = text.split("SOURCES USED:", 1)[0]
    text = text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end <= start:
        return []
    data = json.loads(text[start:end])
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def parse_rag_response_structured(raw: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Parse rag_response.txt → normalized question dicts + sources line.
    Uses Jinja round-trip when RAG_USE_JINJA_JSON is enabled.
    """
    sources = ""
    body = raw or ""
    if "ANSWER:" in body:
        parts = body.split("SOURCES USED:", 1)
        answer_part = parts[0].replace("ANSWER:", "", 1).strip()
        if len(parts) > 1:
            sources = parts[1].strip()
        body = answer_part

    items = extract_json_array(body if body.startswith("[") else raw)
    if not items:
        items = extract_json_array(raw)
    normalized = [_normalize_question_item(it) for it in items]
    for key in _REQUIRED_KEYS:
        for i, q in enumerate(normalized):
            if not q.get(key) and key != "marks":
                logger.warning("rag item %d missing %s", i + 1, key)
    return normalized, sources


def render_rag_response_file(
    questions: List[Dict[str, Any]],
    *,
    sources: str = "",
) -> str:
    """Render full rag_response.txt (ANSWER + JSON + SOURCES) via Jinja2."""
    normalized = [_normalize_question_item(q) for q in questions]
    env = _jinja_env()
    answer_json = env.get_template("rag/response.json.j2").render(
        questions=normalized
    ).strip()
    return env.get_template("rag/response_wrapper.txt.j2").render(
        answer_json=answer_json,
        sources=sources or "Assessment Engine (Jinja2 canonical JSON)",
    ).strip() + "\n"


def canonicalize_rag_response_raw(raw: str) -> str:
    """Re-format existing rag_response.txt through Jinja templates."""
    items, sources = parse_rag_response_structured(raw)
    if not items:
        return raw
    return render_rag_response_file(items, sources=sources)
