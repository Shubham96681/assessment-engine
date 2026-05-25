"""Vector store — FAISS (local, default) or Qdrant (optional, Docker)."""
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

VECTOR_SIZE = settings.EMBEDDING_DIMENSION

if settings.VECTOR_STORE_BACKEND.lower() == "qdrant":
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        OptimizersConfigDiff,
        HnswConfigDiff,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
    )

    qdrant_client = AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
    )
    VECTOR_SIZE = 1536

    async def init_vector_store():
        collections = [
            (settings.QDRANT_COLLECTION_DOCUMENTS, VECTOR_SIZE),
            (settings.QDRANT_COLLECTION_QUESTIONS, VECTOR_SIZE),
            (settings.QDRANT_COLLECTION_HISTORY, VECTOR_SIZE),
        ]
        existing = {c.name for c in (await qdrant_client.get_collections()).collections}
        for name, size in collections:
            if name not in existing:
                await qdrant_client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=size, distance=Distance.COSINE),
                    optimizers_config=OptimizersConfigDiff(indexing_threshold=20000),
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                )
                logger.info("Created Qdrant collection: %s", name)
            else:
                logger.info("Collection exists: %s", name)

else:
    from app.core.faiss_store import (
        faiss_client as qdrant_client,
        init_faiss_store as init_vector_store,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
    )

# Backwards-compatible alias
init_qdrant_collections = init_vector_store


def get_vector_client():
    return qdrant_client
