"""
Retrieve CBSE board question stems by locked chapter / class level.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.vector_store import Filter, FieldCondition, MatchValue, qdrant_client
from app.rag.embeddings import embed_query

logger = logging.getLogger(__name__)


async def retrieve_cbse_exemplars(
    *,
    query: str,
    locked_chapter: str,
    class_level: str = "",
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Dense search in cbse_reference filtered by chapter (and optionally class).
    """
    if not settings.ENABLE_CBSE_REFERENCE:
        return []
    if not locked_chapter or locked_chapter == "generic":
        return []

    k = top_k or settings.CBSE_REFERENCE_TOP_K
    must = [
        FieldCondition(key="locked_chapter", match=MatchValue(value=locked_chapter)),
    ]
    cl = str(class_level or "").strip()
    if cl:
        must.append(FieldCondition(key="class_level", match=MatchValue(value=cl)))

    try:
        vec = await embed_query(query or locked_chapter)
        results = await qdrant_client.search(
            collection_name=settings.QDRANT_COLLECTION_CBSE_REFERENCE,
            query_vector=vec,
            query_filter=Filter(must=must),
            limit=int(k * 2),
        )
    except Exception as exc:
        logger.debug("CBSE reference search failed: %s", exc)
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
                "paper_type": payload.get("paper_type", ""),
                "class_level": payload.get("class_level", ""),
                "score": round(float(r.score), 4),
            }
        )
        if len(rows) >= k:
            break

    # Relax class filter if too few hits
    if len(rows) < max(3, k // 2) and cl:
        try:
            vec = await embed_query(query or locked_chapter)
            results = await qdrant_client.search(
                collection_name=settings.QDRANT_COLLECTION_CBSE_REFERENCE,
                query_vector=vec,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="locked_chapter",
                            match=MatchValue(value=locked_chapter),
                        ),
                    ]
                ),
                limit=k * 2,
            )
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
                        "paper_type": payload.get("paper_type", ""),
                        "class_level": payload.get("class_level", ""),
                        "score": round(float(r.score), 4),
                    }
                )
                if len(rows) >= k:
                    break
        except Exception:
            pass

    return rows
