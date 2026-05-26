"""Quadratic math gate must block bad questions on all scorer paths."""
from app.generation.quality import QualityScorer


def test_quality_scorer_rejects_speed_time_mismatch():
    q = {
        "content": "A cyclist rides 120 km at s km/h and returns at (s + 6) km/h; return takes ½ h less.",
        "correct_answer": "s² + 6s − 1080 = 0. s = 30 km/h.",
        "locked_chapter": "quadratic",
    }
    scorer = QualityScorer()
    assert scorer.should_reject(q, ui_difficulty="hard", slot_meta={"full_hard": True})


def test_filter_drops_bad_math_keeps_good():
    from app.generation.quadratic_math_gate import filter_quadratic_math_verified

    bad = {
        "question": "A cyclist rides 120 km at s km/h and returns at (s + 6) km/h; return takes ½ h less.",
        "correct_answer": "s² + 6s − 1080 = 0. s = 30 km/h.",
    }
    good = {
        "question": "A cyclist rides 90 km at s km/h and returns at (s + 6) km/h, taking ½ hour less on the return.",
        "correct_answer": "s² + 6s − 1080 = 0. s = 30 km/h.",
    }
    kept, rejected = filter_quadratic_math_verified([bad, good], drop=True)
    assert len(rejected) == 1
    assert len(kept) == 1
    assert kept[0].get("math_verification_ok")


def test_validate_rag_json_raises_on_bad_pool():
    from app.generation.quadratic_math_gate import validate_rag_answer_json

    raw = """[
      {"id": "1", "question": "By factorisation only, solve 22x² − 59x + 28 = 0.",
       "correct_answer": "(11x − 4)(2x − 7) = 0."}
    ]"""
    try:
        validate_rag_answer_json(raw, chapter="quadratic")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "math verification" in str(e).lower()


def test_require_pool_raises_on_bad_factorisation():
    from app.generation.quadratic_math_gate import require_quadratic_pool_math_verified

    bad = [
        {
            "question": "By factorisation only, solve 22x² − 59x + 28 = 0.",
            "correct_answer": "(11x − 4)(2x − 7) = 0.",
        }
    ]
    try:
        require_quadratic_pool_math_verified(bad)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "math verification" in str(e).lower()
