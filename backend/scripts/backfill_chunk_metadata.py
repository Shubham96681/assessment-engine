"""
Re-label FAISS document payloads with locked_chapter / section metadata.

Usage (from backend/):
  python scripts/backfill_chunk_metadata.py [--document-id UUID]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.vector_store import qdrant_client
from app.rag.chunk_metadata import label_chunk_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill(document_id: str | None = None) -> int:
    collection = settings.QDRANT_COLLECTION_DOCUMENTS
    updated = 0
    scroll_filter = None
    if document_id:
        from app.core.vector_store import Filter, FieldCondition, MatchValue

        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id", match=MatchValue(value=document_id)
                )
            ]
        )

    offset = None
    while True:
        points, offset = await qdrant_client.scroll(
            collection_name=collection,
            scroll_filter=scroll_filter,
            limit=64,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if not points:
            break
        batch = []
        for pt in points:
            payload = dict(pt.payload or {})
            labeled = label_chunk_payload(
                payload,
                filename=payload.get("filename", ""),
                subject=payload.get("subject", ""),
            )
            from app.core.vector_store import PointStruct

            batch.append(
                PointStruct(id=pt.id, vector=pt.vector, payload=labeled)
            )
            updated += 1
        if batch:
            await qdrant_client.upsert(collection_name=collection, points=batch)
        if offset is None:
            break
    logger.info("Backfilled %d chunk payloads", updated)
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-id", default=None)
    args = parser.parse_args()
    asyncio.run(backfill(args.document_id))


if __name__ == "__main__":
    main()
