"""
Anti-Repetition Engine — exact hash + within-batch + cross-generation semantic dedup.

Questions must never repeat for the same user/subject (and document when scoped).
"""
import hashlib
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.vector_store import (
    qdrant_client,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from app.rag.embeddings import embed_texts

logger = logging.getLogger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    import numpy as np
    if not a or not b or len(a) != len(b):
        return 0.0
    va, vb = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
    dot = float(np.dot(va, vb))
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _normalize_stem(text: str) -> str:
    import re

    t = (text or "").lower().strip()
    t = re.sub(r"\d+(?:\.\d+)?", "#", t)
    t = re.sub(r"\s+", " ", t)
    return t


class DedupEngine:
    def __init__(
        self,
        history_threshold: Optional[float] = None,
        batch_threshold: Optional[float] = None,
    ):
        self.history_threshold = history_threshold or settings.DEDUP_SIMILARITY_THRESHOLD
        self.batch_threshold = batch_threshold or getattr(
            settings, "DEDUP_BATCH_SIMILARITY_THRESHOLD", 0.90
        )

    async def get_recent_stem_previews(
        self,
        user_id: str,
        subject: str,
        class_level: str,
        *,
        document_id: Optional[str] = None,
        limit: int = 30,
    ) -> List[str]:
        """Stems already used in prior generations (for prompt exclusion)."""
        previews: List[str] = []
        try:
            must = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="subject", match=MatchValue(value=subject or "Mathematics")),
            ]
            if document_id:
                must.append(
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                )
            results, _ = await qdrant_client.scroll(
                collection_name=settings.QDRANT_COLLECTION_HISTORY,
                scroll_filter=Filter(must=must),
                limit=limit,
                with_payload=True,
            )
            for point in results or []:
                payload = point.payload or {}
                preview = payload.get("question_preview") or payload.get("stem_normalized")
                if preview and preview not in previews:
                    previews.append(str(preview)[:220])
        except Exception as e:
            logger.warning("Could not load generation history previews: %s", e)
        return previews[:limit]

    def _is_similar_to_batch(
        self,
        embedding: List[float],
        accepted: List[Tuple[List[float], str]],
    ) -> bool:
        for prev_emb, _ in accepted:
            if _cosine_similarity(embedding, prev_emb) >= self.batch_threshold:
                return True
        return False

    async def filter(
        self,
        questions: List[Dict[str, Any]],
        user_id: str,
        subject: str,
        class_level: str,
        *,
        document_id: Optional[str] = None,
        skip_history: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Return only questions unique in this batch and vs generation history.
        skip_history=True: batch dedup only (used when user explicitly applies rag_response.txt).
        """
        if not questions:
            return []

        unique: List[Dict[str, Any]] = []
        hashes_seen: set[str] = set()
        norms_seen: set[str] = set()
        accepted_embeddings: List[Tuple[List[float], str]] = []
        pending_points: List[PointStruct] = []

        texts = [q["content"] for q in questions]
        batch_size = getattr(settings, "INGEST_EMBED_BATCH_SIZE", 32)
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = await embed_texts(batch)
            embeddings.extend(batch_embeddings)

        for q, embedding in zip(questions, embeddings):
            content = (q.get("content") or "").strip()
            if not content:
                continue

            content_hash = q.get("content_hash") or hashlib.sha256(
                content.encode()
            ).hexdigest()
            q["content_hash"] = content_hash
            norm = _normalize_stem(content)

            if content_hash in hashes_seen or norm in norms_seen:
                logger.info("Skipped exact duplicate in batch: %s", content[:60])
                q["dedup_reason"] = "exact_batch_duplicate"
                continue

            if self._is_similar_to_batch(embedding, accepted_embeddings):
                logger.info("Skipped paraphrase in batch: %s", content[:60])
                q["dedup_reason"] = "semantic_batch_duplicate"
                continue

            if not skip_history and await self._check_semantic_similarity(
                embedding, user_id, subject, class_level, document_id=document_id
            ):
                logger.info("Skipped repeat vs history: %s", content[:60])
                q["dedup_reason"] = "semantic_history_duplicate"
                continue

            hashes_seen.add(content_hash)
            norms_seen.add(norm)
            q["embedding"] = embedding
            accepted_embeddings.append((embedding, content_hash))
            unique.append(q)
            if not skip_history:
                point = self._build_history_point(
                    q,
                    embedding,
                    user_id,
                    subject,
                    class_level,
                    document_id=document_id,
                    stem_normalized=norm,
                )
                if point:
                    pending_points.append(point)

        await self._flush_history_points(pending_points)

        if unique:
            from app.generation.canonical_question_signature import (
                filter_zero_duplicate_signatures,
            )
            from app.generation.structural_dedup import filter_structural_duplicates

            unique = filter_zero_duplicate_signatures(unique)
            post = filter_structural_duplicates(unique)
            if len(post) < len(unique):
                logger.info(
                    "Structural/theorem dedup: %d → %d",
                    len(unique),
                    len(post),
                )
            unique = post

        dropped = len(questions) - len(unique)
        logger.info(
            "Dedup: %d → %d unique (%d rejected, skip_history=%s)",
            len(questions),
            len(unique),
            dropped,
            skip_history,
        )
        if not unique and questions:
            from app.generation.structural_dedup import filter_structural_duplicates

            structural = filter_structural_duplicates(questions)
            if structural:
                logger.warning(
                    "Dedup removed all — keeping %d after structural collapse",
                    len(structural),
                )
                return structural
            logger.warning("Dedup removed every question — empty batch")
            return []
        return unique

    async def _check_semantic_similarity(
        self,
        embedding: List[float],
        user_id: str,
        subject: str,
        class_level: str,
        *,
        document_id: Optional[str] = None,
    ) -> bool:
        """True if a similar question already exists in history."""
        try:
            must = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="subject", match=MatchValue(value=subject or "Mathematics")),
            ]
            if document_id:
                must.append(
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                )
            # Rejected corpus points must not count as duplicate accepted questions.
            hist_filter = Filter(
                must=must,
                must_not=[
                    FieldCondition(
                        key="record_type",
                        match=MatchValue(value="rejected"),
                    )
                ],
            )
            results = await qdrant_client.search(
                collection_name=settings.QDRANT_COLLECTION_HISTORY,
                query_vector=embedding,
                query_filter=hist_filter,
                limit=5,
                score_threshold=self.history_threshold,
            )
            return len(results) > 0
        except Exception as e:
            logger.warning(f"Dedup search error: {e}")
            return False

    def _build_history_point(
        self,
        question: Dict,
        embedding: List[float],
        user_id: str,
        subject: str,
        class_level: str,
        *,
        document_id: Optional[str] = None,
        stem_normalized: str = "",
    ) -> Optional[PointStruct]:
        """Build a Qdrant PointStruct for an accepted question (does not upsert)."""
        try:
            point_id = str(uuid.uuid4())
            payload: Dict[str, Any] = {
                "record_type": "accepted",
                "user_id": user_id,
                "subject": subject,
                "class_level": class_level,
                "content_hash": question["content_hash"],
                "question_type": question.get("question_type"),
                "question_preview": (question.get("content") or "")[:220],
                "stem_normalized": stem_normalized or _normalize_stem(
                    question.get("content") or ""
                ),
            }
            if document_id:
                payload["document_id"] = document_id
            for key in (
                "theorem_ids",
                "combo_ids",
                "cognitive_type",
                "archetype_id",
                "detected_theorems",
                "reasoning_signature",
                "canonical_graph_id",
            ):
                if question.get(key) is not None:
                    payload[key] = question[key]
            if not payload.get("reasoning_signature"):
                try:
                    from app.generation.reasoning_signature import (
                        reasoning_signature_for_question,
                    )
                    from app.generation.cognitive_graph_validator import (
                        canonical_graph_id,
                    )

                    payload["reasoning_signature"] = reasoning_signature_for_question(
                        question
                    )
                    payload["canonical_graph_id"] = canonical_graph_id(question)
                except Exception:
                    pass
            question["embedding_id"] = point_id
            return PointStruct(id=point_id, vector=embedding, payload=payload)
        except Exception as e:
            logger.error(f"Failed to build history point: {e}")
            return None

    async def _flush_history_points(self, points: List[PointStruct]):
        if not points:
            return
        try:
            await qdrant_client.upsert(
                collection_name=settings.QDRANT_COLLECTION_HISTORY,
                points=points,
            )
            logger.info("Flushed %d history points in single batch", len(points))
        except Exception as e:
            logger.error(f"Failed to batch upsert history: {e}")

    async def record_questions_to_history(
        self,
        questions: List[Dict[str, Any]],
        user_id: str,
        subject: str,
        class_level: str,
        *,
        document_id: Optional[str] = None,
    ) -> None:
        """Persist accepted questions to generation_history (post-delivery)."""
        points: List[PointStruct] = []
        for q in questions:
            content = (q.get("content") or q.get("question") or "").strip()
            if not content:
                continue
            content_hash = q.get("content_hash") or hashlib.sha256(
                content.encode()
            ).hexdigest()
            q["content_hash"] = content_hash
            embedding = q.get("embedding")
            if not embedding:
                embedding = (await embed_texts([content]))[0]
                q["embedding"] = embedding
            point = self._build_history_point(
                q,
                embedding,
                user_id,
                subject,
                class_level,
                document_id=document_id,
                stem_normalized=_normalize_stem(content),
            )
            if point:
                points.append(point)
        await self._flush_history_points(points)
