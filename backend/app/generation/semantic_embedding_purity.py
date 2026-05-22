"""
Semantic embedding purity — detect paraphrased / latent chapter drift in compiled prompts.

Complements lexical prompt_purity (keywords, archetype ids, section markers).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.generation.chapter_rule_packs import CHAPTER_RULES, get_chapter_rule_pack

logger = logging.getLogger(__name__)

_centroids: Dict[str, List[float]] = {}
_model = None

# Chapters with anchor corpora (skip generic)
_SCORING_CHAPTERS: Tuple[str, ...] = tuple(
    k for k in CHAPTER_RULES.keys() if k != "generic"
)


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model for semantic prompt purity...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _encode(text: str) -> List[float]:
    model = _get_model()
    snippet = (text or "")[:6000]
    if not snippet.strip():
        return [0.0] * 384
    return model.encode(snippet, normalize_embeddings=True).tolist()


def _cosine(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    return max(-1.0, min(1.0, dot))


def _mean_vectors(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            out[i] += v[i]
    k = float(len(vectors))
    return [x / k for x in out]


def chapter_centroid(chapter: str) -> List[float]:
    ch = (chapter or "generic").strip().lower()
    if ch in _centroids:
        return _centroids[ch]
    pack = get_chapter_rule_pack(ch)
    anchors = list(pack.embedding_anchors) or [pack.stem_example]
    embs = [_encode(a) for a in anchors if a.strip()]
    centroid = _mean_vectors(embs) if embs else _encode(pack.stem_example)
    _centroids[ch] = centroid
    return centroid


def _scrub_prompt_for_embedding(prompt: str) -> str:
    """Reduce weight of intentional forbidden-term declaration lines."""
    lines = []
    for line in prompt.splitlines():
        low = line.lower()
        if "do not use" in low or low.strip().startswith("forbidden"):
            continue
        lines.append(line)
    return "\n".join(lines)


def semantic_embedding_contamination(
    prompt: str,
    chapter: str,
    *,
    margin: Optional[float] = None,
    min_locked_similarity: Optional[float] = None,
) -> List[str]:
    """
    Compare prompt embedding to chapter centroids.
    Flags when another chapter centroid is closer than locked (within margin).
    """
    ch = (chapter or "generic").strip().lower()
    if ch == "generic" or not prompt.strip():
        return []

    margin = margin if margin is not None else settings.SEMANTIC_PURITY_MARGIN
    min_locked = (
        min_locked_similarity
        if min_locked_similarity is not None
        else settings.SEMANTIC_PURITY_MIN_LOCKED_SIM
    )

    scrubbed = _scrub_prompt_for_embedding(prompt)
    prompt_emb = _encode(scrubbed)
    locked_sim = _cosine(prompt_emb, chapter_centroid(ch))

    hits: List[str] = []
    if locked_sim < min_locked:
        hits.append(f"semantic_low_alignment:{ch}:{locked_sim:.3f}")

    best_other = ""
    best_other_sim = -1.0
    for other in _SCORING_CHAPTERS:
        if other == ch:
            continue
        sim = _cosine(prompt_emb, chapter_centroid(other))
        if sim > best_other_sim:
            best_other_sim = sim
            best_other = other

    # Wrong chapter wins: other similarity exceeds locked by margin
    if best_other and best_other_sim > locked_sim + margin:
        hits.append(
            f"semantic_drift:{best_other}:{best_other_sim:.3f}>locked_{ch}:{locked_sim:.3f}"
        )

    return hits


def validate_semantic_embedding_purity(
    prompt: str,
    chapter: str,
    *,
    strict: bool = True,
) -> List[str]:
    if not settings.ENABLE_SEMANTIC_PROMPT_PURITY:
        return []
    hits = semantic_embedding_contamination(prompt, chapter)
    if hits and strict:
        from app.generation.prompt_purity import PromptContaminationError

        raise PromptContaminationError(chapter, hits)
    return hits
