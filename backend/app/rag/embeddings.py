"""
Embedding generation — supports OpenAI + Google Gemini + local sentence-transformers
"""
import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


def _target_embedding_dim() -> int:
    """FAISS uses native model size; Qdrant collections expect 1536."""
    if settings.VECTOR_STORE_BACKEND.lower() == "faiss":
        return settings.EMBEDDING_DIMENSION
    return 1536


def _fit_dim(emb: List[float]) -> List[float]:
    dim = _target_embedding_dim()
    if len(emb) < dim:
        return emb + [0.0] * (dim - len(emb))
    return emb[:dim]

_local_model = None


async def preload_local_embedding_model() -> None:
    """Load sentence-transformers once at startup (avoids 1–2 min delay on first quiz)."""
    if settings.has_cloud_llm() and settings.VECTOR_STORE_BACKEND.lower() != "faiss":
        return
    global _local_model
    if _local_model is not None:
        return
    import asyncio
    from sentence_transformers import SentenceTransformer

    loop = asyncio.get_event_loop()
    logger.info("Preloading local embedding model (one-time, ~1–2 min)...")
    _local_model = await loop.run_in_executor(
        None, lambda: SentenceTransformer("all-MiniLM-L6-v2")
    )
    logger.info("Local embedding model ready")


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings — local model for FAISS; cloud only with real API keys."""
    backend = (settings.VECTOR_STORE_BACKEND or "faiss").lower()
    if backend == "faiss" or not settings.has_cloud_llm():
        return await _embed_local(texts)
    if settings.OPENAI_API_KEY:
        try:
            return await _embed_openai(texts)
        except Exception as e:
            logger.warning("OpenAI embed failed (%s); using local model", e)
            return await _embed_local(texts)
    if settings.GOOGLE_GEMINI_API_KEY:
        try:
            return await _embed_gemini(texts)
        except Exception as e:
            logger.warning("Gemini embed failed (%s); using local model", e)
            return await _embed_local(texts)
    return await _embed_local(texts)


async def _embed_openai(texts: List[str]) -> List[List[float]]:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # Batch in groups of 100
    all_embeddings = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


async def _embed_gemini(texts: List[str]) -> List[List[float]]:
    import google.generativeai as genai
    genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
    all_embeddings = []
    for text in texts:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
        emb = _fit_dim(result["embedding"])
        all_embeddings.append(emb)
    return all_embeddings


async def _embed_local(texts: List[str]) -> List[List[float]]:
    """Local fallback using sentence-transformers (no API key needed)."""
    global _local_model
    from sentence_transformers import SentenceTransformer
    import asyncio

    loop = asyncio.get_event_loop()
    if _local_model is None:
        logger.info("Loading local embedding model (first run may take a minute)...")
        _local_model = await loop.run_in_executor(
            None, lambda: SentenceTransformer("all-MiniLM-L6-v2")
        )
    embeddings = await loop.run_in_executor(
        None, lambda: _local_model.encode(texts, normalize_embeddings=True).tolist()
    )
    return [_fit_dim(list(emb)) for emb in embeddings]


async def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    results = await embed_texts([text])
    return results[0]
