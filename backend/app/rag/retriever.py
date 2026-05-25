"""
Hybrid RAG Retriever — Dense (FAISS/Qdrant) + Sparse (BM25) search
Returns ranked, deduplicated chunks for question generation context.
"""
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.vector_store import qdrant_client, Filter, FieldCondition, MatchValue
from app.rag.embeddings import embed_query

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Retrieves relevant document chunks using:
    1. Dense vector search (semantic)
    2. BM25 keyword search
    3. Reciprocal Rank Fusion (RRF) for final ranking
    """

    async def retrieve(
        self,
        query: str,
        document_id: str,
        top_k: int = None,
        subject: Optional[str] = None,
        *,
        locked_chapter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        top_k = top_k or settings.MAX_RETRIEVAL_CHUNKS

        # 1. Dense search
        dense_results = await self._dense_search(query, document_id, top_k * 3)

        # 2. BM25 sparse search on the same candidates
        bm25_results = self._bm25_rerank(query, dense_results)

        # 3. RRF fusion
        fused = self._reciprocal_rank_fusion(dense_results, bm25_results, top_k * 2)

        if locked_chapter and locked_chapter != "generic":
            from app.rag.chapter_chunk_filter import filter_chunks_by_chapter

            fused = filter_chunks_by_chapter(fused, locked_chapter)[:top_k]
        else:
            fused = fused[:top_k]

        logger.debug(f"Retrieved {len(fused)} chunks for: {query[:60]}...")
        return fused

    async def _dense_search(
        self,
        query: str,
        document_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        query_vector = await embed_query(query)
        results = await qdrant_client.search(
            collection_name=settings.QDRANT_COLLECTION_DOCUMENTS,
            query_vector=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
            limit=limit,
            with_payload=True,
        )
        return [
            {
                "text": r.payload.get("text", ""),
                "page_num": r.payload.get("page_num"),
                "score": r.score,
                "qdrant_id": r.id,
                "payload": r.payload,
            }
            for r in results
        ]

    def _bm25_rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        corpus = [c["text"].split() for c in candidates]
        bm25 = BM25Okapi(corpus)
        query_tokens = query.split()
        scores = bm25.get_scores(query_tokens)
        ranked = sorted(
            enumerate(candidates), key=lambda x: scores[x[0]], reverse=True
        )
        return [item for _, item in ranked]

    def _reciprocal_rank_fusion(
        self,
        dense: List[Dict],
        sparse: List[Dict],
        top_k: int,
        k: int = 60,
    ) -> List[Dict]:
        """RRF: combine ranked lists."""
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict] = {}

        for rank, item in enumerate(dense):
            cid = item.get("qdrant_id", str(rank))
            scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
            chunk_map[cid] = item

        for rank, item in enumerate(sparse):
            cid = item.get("qdrant_id", str(rank))
            scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
            chunk_map[cid] = item

        sorted_ids = sorted(scores, key=scores.__getitem__, reverse=True)[:top_k]
        return [chunk_map[cid] for cid in sorted_ids]
