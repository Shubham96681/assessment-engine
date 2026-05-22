"""
Retrieval confidence — detect sparse RAG and switch to curriculum-archetype generation.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings


def compute_retrieval_confidence(
    chunks: List[Dict[str, Any]],
    *,
    min_chunks: int | None = None,
    min_mean_score: float | None = None,
) -> Dict[str, Any]:
    """
    Composite score in [0, 1] from chunk count, mean similarity score, and text volume.

    Returns dict with score, mode (pdf_rich | curriculum_fallback), and diagnostics.
    """
    min_chunks = min_chunks if min_chunks is not None else settings.RETRIEVAL_MIN_CHUNKS
    min_mean = min_mean_score if min_mean_score is not None else settings.RETRIEVAL_MIN_MEAN_SCORE
    threshold = settings.RETRIEVAL_CONFIDENCE_THRESHOLD

    if not chunks:
        return {
            "score": 0.0,
            "mode": "curriculum_fallback",
            "chunk_count": 0,
            "mean_similarity": 0.0,
            "total_text_chars": 0,
            "reason": "no_chunks",
            "use_curriculum_archetypes": True,
        }

    scores = [float(c.get("score") or 0.0) for c in chunks]
    mean_score = sum(scores) / len(scores) if scores else 0.0
    count = len(chunks)
    text_chars = sum(len((c.get("text") or "")) for c in chunks[:8])

    # Normalize Qdrant cosine scores (often 0.3–0.9) into [0,1]
    score_component = min(1.0, max(0.0, (mean_score - 0.25) / 0.55))
    count_component = min(1.0, count / max(min_chunks, 1))
    text_component = min(1.0, text_chars / 2400)

    composite = round(
        0.45 * score_component + 0.35 * count_component + 0.20 * text_component,
        3,
    )

    sparse = (
        count < min_chunks
        or mean_score < min_mean
        or composite < threshold
    )
    mode = "curriculum_fallback" if sparse else "pdf_rich"
    reasons: List[str] = []
    if count < min_chunks:
        reasons.append(f"chunk_count<{min_chunks}")
    if mean_score < min_mean:
        reasons.append(f"mean_score<{min_mean}")
    if composite < threshold:
        reasons.append(f"composite<{threshold}")

    return {
        "score": composite,
        "mode": mode,
        "chunk_count": count,
        "mean_similarity": round(mean_score, 4),
        "total_text_chars": text_chars,
        "reason": ",".join(reasons) if reasons else "ok",
        "use_curriculum_archetypes": sparse,
    }
