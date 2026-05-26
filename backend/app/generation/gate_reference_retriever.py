"""Retrieve GATE exam question stems by locked chapter."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.vector_store import Filter, FieldCondition, MatchValue, qdrant_client
from app.rag.embeddings import embed_query

logger = logging.getLogger(__name__)


async def retrieve_gate_exemplars(
    *,
    query: str,
    locked_chapter: str,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    if not settings.ENABLE_GATE_REFERENCE or not locked_chapter or locked_chapter == "generic":
        return []
    k = top_k or settings.GATE_REFERENCE_TOP_K
    try:
        vec = await embed_query(query or locked_chapter)
        results = await qdrant_client.search(
            collection_name=settings.QDRANT_COLLECTION_GATE_REFERENCE,
            query_vector=vec,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="locked_chapter",
                        match=MatchValue(value=locked_chapter),
                    )
                ]
            ),
            limit=int(k * 2),
        )
    except Exception as exc:
        logger.debug("GATE reference search failed: %s", exc)
        return []

    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for r in results:
        payload = r.payload or {}
        content = (payload.get("content") or payload.get("text") or "").strip()
        if not content or content in seen:
            continue
        seen.add(content)
        rows.append(
            {
                "content": content,
                "marks": payload.get("marks"),
                "source_file": payload.get("source_file", ""),
                "gate_year": payload.get("gate_year", ""),
                "gate_subject": payload.get("gate_subject", ""),
                "score": round(float(r.score), 4),
            }
        )
        if len(rows) >= k:
            break
    return rows
