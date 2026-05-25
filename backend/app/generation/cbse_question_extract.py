"""
Extract question stems from CBSE sample / board PDF text (no fixed question bank).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Board paper patterns (SQP, CBE, marking scheme prose)
_Q_HEAD = re.compile(
    r"(?im)(?:^|\n)\s*(?:question\s*)?(\d{1,2})[\.\):]\s+"
    r"(?=[A-Za-z(])",
)
_SECTION = re.compile(
    r"(?im)^\s*(?:section\s+[A-D]|part\s+[A-D])\s*[:\-]?\s*",
)
_MARKS = re.compile(
    r"\[\s*(\d+(?:\.\d+)?)\s*marks?\s*\]|\(\s*(\d+(?:\.\d+)?)\s*marks?\s*\)",
    re.I,
)
_SUBPART = re.compile(r"\(\s*([ivx]+|[a-d]|[i]{1,3})\s*\)", re.I)
_EXAM_VERB = re.compile(
    r"(?i)\b(?:find|prove|show\s+that|calculate|evaluate|solve|verify|"
    r"determine|hence|if\s|draw|construct|simplify|factorise|factorize)\b",
)


def _clean_stem(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    t = re.sub(r"^\d+[\.\)]\s*", "", t)
    return t[:500]


def parse_class_from_path(path: str) -> str:
    m = re.search(r"class[_\s\-]*(\d{1,2})", path, re.I)
    if m:
        return m.group(1)
    return ""


def class_to_band(class_num: str) -> str:
    try:
        n = int(class_num)
    except (TypeError, ValueError):
        return "all"
    if n <= 8:
        return "middle"
    if n <= 10:
        return "secondary"
    return "senior"


def extract_stems_from_pdf_text(
    text: str,
    *,
    source_file: str = "",
) -> List[Dict[str, Any]]:
    """Split PDF text into question-like stems with metadata."""
    if not text or len(text.strip()) < 80:
        return []

    stems: List[Dict[str, Any]] = []
    class_num = parse_class_from_path(source_file)
    band = class_to_band(class_num)

    # Block split by question headers
    parts: List[tuple[str, str]] = []
    matches = list(_Q_HEAD.finditer(text))
    for i, m in enumerate(matches):
        qnum = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) > 15:
            parts.append((qnum, body))

    if not parts:
        # Fallback: numbered list items
        for m in re.finditer(
            r"(?im)^\s*(\d{1,2})[\.\)]\s+([^\n]{20,280})",
            text,
        ):
            parts.append((m.group(1), m.group(2)))

    for qnum, body in parts:
        stem = _clean_stem(body)
        if len(stem.split()) < 6:
            continue
        if re.search(r"marking\s+scheme|general\s+instructions|time\s+allowed", stem, re.I):
            continue
        marks_m = _MARKS.search(body)
        marks = None
        if marks_m:
            marks = float(marks_m.group(1) or marks_m.group(2) or 0)
        verbs = _EXAM_VERB.findall(stem)
        stems.append(
            {
                "content": stem,
                "slot_number": int(qnum) if qnum.isdigit() else 0,
                "marks": marks,
                "class_num": class_num,
                "class_band": band,
                "source_file": source_file,
                "word_count": len(stem.split()),
                "subpart_count": len(_SUBPART.findall(stem)),
                "exam_verb_count": len(verbs),
                "has_or": bool(re.search(r"\bOR\b", stem)),
            }
        )
    return stems
