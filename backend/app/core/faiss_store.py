"""
Local FAISS vector store — Qdrant-compatible API for document/history search.
Persists indexes under FAISS_DATA_PATH (no Docker).
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


# --- Qdrant-compatible filter / point types ---------------------------------

@dataclass
class MatchValue:
    value: Any


@dataclass
class FieldCondition:
    key: str
    match: MatchValue


@dataclass
class Filter:
    must: List[FieldCondition] = field(default_factory=list)
    must_not: List[FieldCondition] = field(default_factory=list)


@dataclass
class PointStruct:
    id: str
    vector: List[float]
    payload: Dict[str, Any]


@dataclass
class ScoredPoint:
    id: str
    score: float
    payload: Dict[str, Any]


@dataclass
class _StoredPoint:
    id: str
    vector: np.ndarray
    payload: Dict[str, Any]


def _matches_filter(payload: Dict[str, Any], filt: Optional[Filter]) -> bool:
    if not filt:
        return True
    for cond in filt.must or []:
        if payload.get(cond.key) != cond.match.value:
            return False
    for cond in filt.must_not or []:
        if payload.get(cond.key) == cond.match.value:
            return False
    return True


class _FaissCollection:
    """One named collection (documents, generation_history, questions)."""

    def __init__(self, name: str, root: Path, dim: int):
        self.name = name
        self.root = root / name
        self.root.mkdir(parents=True, exist_ok=True)
        self.dim = dim
        self._points: Dict[str, _StoredPoint] = {}
        self._load()

    def _meta_path(self) -> Path:
        return self.root / "points.json"

    def _vectors_path(self) -> Path:
        return self.root / "vectors.npy"

    def _load(self) -> None:
        meta_path = self._meta_path()
        if not meta_path.exists():
            return
        try:
            raw = json.loads(meta_path.read_text(encoding="utf-8"))
            vec_path = self._vectors_path()
            if not vec_path.exists():
                return
            matrix = np.load(vec_path)
            for i, entry in enumerate(raw):
                pid = entry["id"]
                payload = entry.get("payload") or {}
                vec = matrix[i].astype(np.float32)
                self._points[pid] = _StoredPoint(id=pid, vector=vec, payload=payload)
            logger.info("Loaded FAISS collection %s (%d points)", self.name, len(self._points))
        except Exception as e:
            logger.warning("Could not load FAISS collection %s: %s", self.name, e)

    def _save(self) -> None:
        if not self._points:
            self._meta_path().write_text("[]", encoding="utf-8")
            return
        ids = list(self._points.keys())
        meta = [{"id": pid, "payload": self._points[pid].payload} for pid in ids]
        matrix = np.vstack([self._points[pid].vector for pid in ids]).astype(np.float32)
        self._meta_path().write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        np.save(self._vectors_path(), matrix)

    def upsert(self, points: List[PointStruct]) -> None:
        for pt in points:
            pid = str(pt.id)
            vec = np.array(pt.vector, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            if vec.shape[0] != self.dim:
                if vec.shape[0] < self.dim:
                    padded = np.zeros(self.dim, dtype=np.float32)
                    padded[: vec.shape[0]] = vec
                    vec = padded
                else:
                    vec = vec[: self.dim]
            self._points[pid] = _StoredPoint(id=pid, vector=vec, payload=dict(pt.payload or {}))
        self._save()

    def search(
        self,
        query_vector: List[float],
        *,
        query_filter: Optional[Filter] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None,
    ) -> List[ScoredPoint]:
        if not self._points:
            return []
        q = np.array(query_vector, dtype=np.float32)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm
        if q.shape[0] != self.dim:
            if q.shape[0] < self.dim:
                padded = np.zeros(self.dim, dtype=np.float32)
                padded[: q.shape[0]] = q
                q = padded
            else:
                q = q[: self.dim]

        scored: List[ScoredPoint] = []
        for pt in self._points.values():
            if not _matches_filter(pt.payload, query_filter):
                continue
            score = float(np.dot(q, pt.vector))
            if score_threshold is not None and score < score_threshold:
                continue
            scored.append(ScoredPoint(id=pt.id, score=score, payload=pt.payload))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def scroll(
        self,
        *,
        scroll_filter: Optional[Filter] = None,
        limit: int = 100,
    ) -> Tuple[List[ScoredPoint], None]:
        items = [
            ScoredPoint(id=pt.id, score=1.0, payload=pt.payload)
            for pt in self._points.values()
            if _matches_filter(pt.payload, scroll_filter)
        ]
        return items[:limit], None


class FaissVectorClient:
    """Async wrapper — runs FAISS work in a thread pool."""

    def __init__(self, storage_path: str, dim: int):
        self._root = Path(storage_path)
        self._root.mkdir(parents=True, exist_ok=True)
        self._dim = dim
        self._collections: Dict[str, _FaissCollection] = {}
        self._lock = asyncio.Lock()

    def _collection(self, name: str) -> _FaissCollection:
        if name not in self._collections:
            self._collections[name] = _FaissCollection(name, self._root, self._dim)
        return self._collections[name]

    async def upsert(self, collection_name: str, points: List[PointStruct]) -> None:
        async with self._lock:
            await asyncio.to_thread(self._collection(collection_name).upsert, points)

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        *,
        query_filter: Optional[Filter] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        with_payload: bool = True,
    ) -> List[ScoredPoint]:
        return await asyncio.to_thread(
            self._collection(collection_name).search,
            query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

    async def scroll(
        self,
        collection_name: str,
        *,
        scroll_filter: Optional[Filter] = None,
        limit: int = 100,
        with_payload: bool = True,
    ) -> Tuple[List[ScoredPoint], None]:
        return await asyncio.to_thread(
            self._collection(collection_name).scroll,
            scroll_filter=scroll_filter,
            limit=limit,
        )


faiss_client = FaissVectorClient(
    storage_path=settings.FAISS_DATA_PATH,
    dim=settings.EMBEDDING_DIMENSION,
)


async def init_faiss_store() -> None:
    """Ensure collection directories exist (indexes load on first use)."""
    for name in (
        settings.QDRANT_COLLECTION_DOCUMENTS,
        settings.QDRANT_COLLECTION_QUESTIONS,
        settings.QDRANT_COLLECTION_HISTORY,
    ):
        faiss_client._collection(name)
    logger.info("FAISS vector store ready at %s", settings.FAISS_DATA_PATH)
