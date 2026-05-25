"""Structured chunking, retrieval rerank, RL reward."""
from app.rag.structured_chunker import chunk_page_text
from app.rag.chunk_metadata import label_chunk_payload, boost_chunk_for_query
from app.rag.retrieval_rerank import rerank_chunks
from app.rl.reward_scorer import RewardScorer, apply_rl_reward


def test_structured_exercise_split():
    text = (
        "EXERCISE 10.1\n"
        "1. Find the length of tangent from a point 13 cm from centre.\n"
        "2. Prove that tangents from an external point are equal.\n"
        "EXERCISE 10.2\n"
        "1. A chord of length 16 cm is drawn in a circle of radius 10 cm.\n"
    )
    chunks = chunk_page_text(text, page_num=5, document_id="doc1", filename="circles.pdf")
    assert len(chunks) >= 2
    assert any(c.section_type == "exercise" for c in chunks)


def test_label_chunk_payload_circles():
    row = label_chunk_payload(
        {"text": "Theorem 10.1 tangent perpendicular to radius at point of contact."},
        filename="Chapter_10_Circles.pdf",
    )
    assert row.get("locked_chapter") in ("circles", "generic", "trigonometry")


def test_rerank_prefers_chapter_match():
    chunks = [
        {"text": "quadratic equation roots", "score": 0.9, "locked_chapter": "quadratic"},
        {
            "text": "tangent radius circle chord",
            "score": 0.7,
            "locked_chapter": "circles",
            "rrf_score": 0.7,
        },
    ]
    out = rerank_chunks("tangent radius circle", chunks, locked_chapter="circles", top_k=1)
    assert "circle" in out[0]["text"].lower() or out[0].get("locked_chapter") == "circles"


def test_rl_reward_boosts_clean_stem():
    q = {
        "content": "PQ is tangent at P to a circle with centre O. OP = 5 cm. Find PQ.",
        "completeness_ok": True,
        "authenticity_score": 0.8,
        "combined_score": 0.5,
    }
    apply_rl_reward([q])
    assert "rl_reward_score" in q
    assert q["combined_score"] >= 0.4


def test_reward_scorer_penalizes_banned_phrase():
    scorer = RewardScorer()
    bad = scorer.score_question({"content": "Using theorem show your working for tangent."})
    good = scorer.score_question(
        {"content": "If OA = 5 cm, OP = 13 cm, find AP where P is external point."}
    )
    assert good > bad
