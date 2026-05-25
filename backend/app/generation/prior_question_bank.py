"""
Load prior question stems from SQLite (ready assessments) for uniqueness enforcement.

Qdrant history may be empty in dev; DB always has saved papers.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment, Question


async def fetch_prior_stems_from_db(
    db: AsyncSession,
    document_id: str,
    *,
    exclude_assessment_id: Optional[str] = None,
    limit: int = 50,
) -> List[str]:
    """Stems from prior ready assessments on the same document (newest first)."""
    if not document_id:
        return []
    r = await db.execute(
        select(Assessment)
        .where(Assessment.document_id == document_id)
        .where(Assessment.status == "ready")
        .order_by(Assessment.created_at.desc())
        .limit(20)
    )
    assessments = r.scalars().all()
    stems: List[str] = []
    seen: set[str] = set()
    for a in assessments:
        if exclude_assessment_id and a.id == exclude_assessment_id:
            continue
        if not a.question_ids:
            continue
        qr = await db.execute(
            select(Question).where(Question.assessment_id == a.id)
        )
        by_id = {q.id: q for q in qr.scalars().all()}
        for qid in a.question_ids:
            q = by_id.get(qid)
            if not q or not (q.content or "").strip():
                continue
            text = (q.content or "").strip()
            key = text[:120].lower()
            if key in seen:
                continue
            seen.add(key)
            stems.append(text[:220])
            if len(stems) >= limit:
                return stems
    return stems


def merge_prior_stem_lists(*lists: List[str], limit: int = 50) -> List[str]:
    """Dedupe while preserving order (first list highest priority)."""
    out: List[str] = []
    seen: set[str] = set()
    for lst in lists:
        for s in lst or []:
            t = (s or "").strip()
            if not t:
                continue
            key = t[:120].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t[:220])
            if len(out) >= limit:
                return out
    return out
