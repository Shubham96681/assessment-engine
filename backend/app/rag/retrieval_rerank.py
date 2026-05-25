"""
Post-retrieval reranking — metadata boost + optional cross-encoder (phyEngine-style).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.rag.chunk_metadata import boost_chunk_for_query

logger = logging.getLogger(__name__)

_cross_encoder = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder

        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logger.info("Loaded cross-encoder reranker")
    except Exception as exc:
        logger.warning("Cross-encoder reranker unavailable: %s", exc)
        _cross_encoder = False
    return _cross_encoder


def rerank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    *,
    locked_chapter: str = "",
    top_k: int = 6,
    use_cross_encoder: bool = False,
) -> List[Dict[str, Any]]:
    if not chunks:
        return []
    scored: List[tuple[float, Dict[str, Any]]] = []
    ce = _get_cross_encoder() if use_cross_encoder else False
    ce_scores: List[float] = []
    if ce:
        pairs = [(query, c.get("text") or "") for c in chunks]
        try:
            ce_scores = ce.predict(pairs).tolist()
        except Exception as exc:
            logger.warning("Cross-encoder predict failed: %s", exc)
            ce_scores = []

    for i, chunk in enumerate(chunks):
        base = float(chunk.get("rrf_score") or chunk.get("score") or 0.0)
        meta_boost = boost_chunk_for_query(chunk, query, locked_chapter)
        ce_part = 0.0
        if ce_scores and i < len(ce_scores):
            ce_part = float(ce_scores[i]) * 0.15
        final = base * 0.55 + meta_boost * 0.35 + ce_part
        row = dict(chunk)
        row["rerank_score"] = round(final, 4)
        scored.append((final, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]
