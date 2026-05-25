"""
Exercise-aware PDF chunking (phyEngine-style) for NCERT / board textbooks.

Splits on Example / Exercise / Theorem boundaries instead of only character windows.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class StructuredChunk:
    text: str
    page_num: int
    chunk_index: int
    section_type: str = "paragraph"
    section_label: str = ""
    exercise_id: str = ""
    chunk_id: str = ""
    metadata: dict = field(default_factory=dict)


# NCERT / RD Sharma style boundaries
_EXERCISE_HEAD = re.compile(
    r"(?:^|\n)\s*(EXERCISE\s+[\d.]+|Exercise\s+[\d.]+)\b",
    re.I | re.M,
)
_EXAMPLE_HEAD = re.compile(
    r"(?:^|\n)\s*Example\s+(\d+(?:\.\d+)?)\s*[:\.]",
    re.I | re.M,
)
_THEOREM_HEAD = re.compile(
    r"(?:^|\n)\s*(Theorem\s+[\d.]+|THEOREM\s+[\d.]+)\b",
    re.I | re.M,
)
_NUMBERED_ITEM = re.compile(
    r"(?:^|\n)\s*(\d{1,3})[\.\)]\s+(?=[A-Za-z(])",
    re.M,
)
_JEE_Q = re.compile(
    r"(?:^|\n)\s*(?:Q\.|Question)\s*(\d+)[\.\):]",
    re.I | re.M,
)


def _make_chunk_id(document_id: str, label: str, seq: int) -> str:
    raw = f"{document_id}_{label}_{seq}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _split_by_pattern(
    text: str,
    pattern: re.Pattern,
    *,
    label_prefix: str,
    section_type: str,
    page_num: int,
    document_id: str,
    start_index: int,
) -> List[StructuredChunk]:
    matches = list(pattern.finditer(text))
    if not matches:
        return []
    chunks: List[StructuredChunk] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) < 30:
            continue
        label = match.group(1) if match.lastindex else match.group(0).strip()[:40]
        label = re.sub(r"\s+", "_", str(label).lower())[:48] or f"{label_prefix}_{i}"
        chunks.append(
            StructuredChunk(
                text=body,
                page_num=page_num,
                chunk_index=start_index + len(chunks),
                section_type=section_type,
                section_label=str(label),
                exercise_id=f"{label_prefix}_{label}",
                chunk_id=_make_chunk_id(document_id, f"{label_prefix}_{label}", i),
            )
        )
    return chunks


def chunk_page_text(
    text: str,
    *,
    page_num: int,
    document_id: str,
    base_index: int = 0,
    filename: str = "",
) -> List[StructuredChunk]:
    """Prefer exercise/example splits; fall back to paragraph windows."""
    if not text or len(text.strip()) < 30:
        return []

    low_name = (filename or "").lower()
    combined = text

    for pattern, prefix, stype in (
        (_EXERCISE_HEAD, "ex", "exercise"),
        (_EXAMPLE_HEAD, "example", "example"),
        (_THEOREM_HEAD, "thm", "theorem"),
        (_JEE_Q, "jee_q", "question"),
    ):
        if "jee" in low_name or "advanced" in low_name or stype == "question":
            if stype != "question" and "jee" not in low_name:
                continue
        rows = _split_by_pattern(
            combined,
            pattern,
            label_prefix=prefix,
            section_type=stype,
            page_num=page_num,
            document_id=document_id,
            start_index=base_index,
        )
        if len(rows) >= 2:
            return rows

    # Numbered exercise items (1. Find … 2. Prove …)
    rows = _split_by_pattern(
        combined,
        _NUMBERED_ITEM,
        label_prefix="item",
        section_type="exercise_item",
        page_num=page_num,
        document_id=document_id,
        start_index=base_index,
    )
    if len(rows) >= 3:
        return rows

    return _chunk_paragraphs(
        combined,
        page_num=page_num,
        document_id=document_id,
        base_index=base_index,
    )


def _chunk_paragraphs(
    text: str,
    *,
    page_num: int,
    document_id: str,
    base_index: int,
) -> List[StructuredChunk]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[StructuredChunk] = []
    buf: List[str] = []
    target = 480

    def flush() -> None:
        if not buf:
            return
        body = "\n\n".join(buf).strip()
        if len(body) < 40:
            buf.clear()
            return
        seq = len(chunks)
        chunks.append(
            StructuredChunk(
                text=body,
                page_num=page_num,
                chunk_index=base_index + seq,
                section_type="paragraph",
                section_label=f"p{page_num}_{seq}",
                chunk_id=_make_chunk_id(document_id, f"p{page_num}_{seq}", seq),
            )
        )
        buf.clear()

    for para in parts:
        if buf and sum(len(x) for x in buf) + len(para) > target:
            flush()
        buf.append(para)
    flush()
    return chunks


def chunk_document_pages(
    pages: List[dict],
    *,
    document_id: str,
    filename: str = "",
) -> List[StructuredChunk]:
    all_chunks: List[StructuredChunk] = []
    for page_info in pages:
        page_chunks = chunk_page_text(
            page_info.get("text") or "",
            page_num=int(page_info.get("page_num") or 0),
            document_id=document_id,
            base_index=len(all_chunks),
            filename=filename,
        )
        all_chunks.extend(page_chunks)
    return all_chunks
