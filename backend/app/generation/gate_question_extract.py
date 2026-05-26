"""
Extract question stems from GATE exam PDF text (MA/CS/… papers).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.generation.cbse_question_extract import (
    _clean_stem,
    _EXAM_VERB,
    _MARKS,
    _SUBPART,
    extract_stems_from_pdf_text,
)

_GATE_Q = re.compile(
    r"(?im)(?:^|\n)\s*(?:Q\.?\s*|Question\s+)(\d{1,2})[\.\):]?\s+",
)
_GATE_NAT = re.compile(r"(?im)\b(?:NAT|numerical\s+answer)\b")
_YEAR = re.compile(r"(?i)GATE[_\s\-]*(\d{4})")
_SUBJECT = re.compile(r"(?i)GATE[_\s\-]*\d{4}[_\s\-]*([A-Z]{2,4})")


def parse_gate_year(path: str) -> str:
    m = _YEAR.search(path or "")
    return m.group(1) if m else ""


def parse_gate_subject(path: str) -> str:
    m = _SUBJECT.search(path or "")
    return (m.group(1) or "").upper()


def paper_role_from_path(path: str) -> str:
    low = (path or "").lower()
    if "answer" in low and "key" in low:
        return "answer_key"
    if "solution" in low:
        return "solutions"
    if "question" in low:
        return "question_paper"
    return "other"


def should_index_pdf(path: str) -> bool:
    role = paper_role_from_path(path)
    return role in ("question_paper", "solutions")


def extract_stems_from_gate_pdf_text(
    text: str,
    *,
    source_file: str = "",
) -> List[Dict[str, Any]]:
    """GATE papers: longer stems, MCQ options often inline; skip header boilerplate."""
    if not text or len(text.strip()) < 100:
        return []

    base = extract_stems_from_pdf_text(text, source_file=source_file)
    if base:
        return _tag_gate_rows(base, source_file)

    stems: List[Dict[str, Any]] = []
    matches = list(_GATE_Q.finditer(text))
    for i, m in enumerate(matches):
        qnum = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) < 25:
            continue
        body = re.sub(r"(?is)\boptions?\s*:.*$", "", body[:900]).strip()
        content = _clean_stem(body)
        if len(content.split()) < 8:
            continue
        if not _EXAM_VERB.search(content) and "?" not in content:
            if not re.search(r"(?i)\b(if|let|given|suppose|consider)\b", content):
                continue
        marks_m = _MARKS.search(body)
        marks = float(marks_m.group(1) or marks_m.group(2)) if marks_m else 2.0
        stems.append(
            {
                "content": content,
                "slot_number": int(qnum) if qnum.isdigit() else 0,
                "marks": marks,
                "word_count": len(content.split()),
                "subpart_count": len(_SUBPART.findall(content)),
                "exam_verb_count": len(_EXAM_VERB.findall(content)),
                "source_file": source_file,
                "exam_tier": "gate",
            }
        )
    return _tag_gate_rows(stems, source_file)


def _tag_gate_rows(rows: List[Dict[str, Any]], source_file: str) -> List[Dict[str, Any]]:
    year = parse_gate_year(source_file)
    subject = parse_gate_subject(source_file)
    role = paper_role_from_path(source_file)
    out: List[Dict[str, Any]] = []
    for r in rows:
        content = (r.get("content") or "").strip()
        if len(content.split()) < 8:
            continue
        if re.search(r"(?i)^\s*(option|answer)\s*[:\-]?\s*[A-D]\b", content):
            continue
        out.append(
            {
                **r,
                "content": content[:600],
                "word_count": len(content.split()),
                "gate_year": year,
                "gate_subject": subject,
                "paper_role": role,
                "exam_tier": "gate",
                "class_band": "gate",
            }
        )
    return out
