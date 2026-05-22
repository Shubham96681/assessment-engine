"""Qdrant vector store initialization and client"""
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, CreateCollection,
    OptimizersConfigDiff, HnswConfigDiff
)
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

qdrant_client = AsyncQdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY or None,
)

VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small / Google textembedding-gecko


async def init_qdrant_collections():
    """Create all required collections if they don't exist."""
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
            logger.info(f"Created Qdrant collection: {name}")
        else:
            logger.info(f"✓ Collection exists: {name}")


def get_qdrant():
    return qdrant_client
