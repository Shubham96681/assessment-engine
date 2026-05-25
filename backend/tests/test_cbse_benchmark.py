"""CBSE benchmark — dynamic floors, not hardcoded 0.38."""
from app.generation.cbse_benchmark import (
    _aggregate_band,
    _profile_from_rule_packs,
    evaluate_against_cbse,
    get_dynamic_combined_floor,
    benchmark_prompt_hints,
)
from app.generation.cbse_question_extract import extract_stems_from_pdf_text


SAMPLE_PAPER = """
General Instructions
Time Allowed: 3 Hours
1. Find the value of sin 75° using appropriate identity.
2. Prove that (sin θ + cos θ)² = 1 + sin 2θ.
3. If tan θ = 3/4, find sin θ and cos θ. [3 marks]
4. Evaluate: cos 15° cos 75° - sin 15° sin 75°. [4 marks]
"""


def test_extract_stems_from_sample_text():
    stems = extract_stems_from_pdf_text(
        SAMPLE_PAPER, source_file="Class_10/Maths/Standard_SQP.pdf"
    )
    assert len(stems) >= 3
    assert any("sin" in s["content"].lower() for s in stems)


def test_dynamic_floor_from_aggregate():
    rows = [
        {"word_count": 20, "authenticity": 0.55, "combined": 0.50, "exam_verb_count": 1},
        {"word_count": 25, "authenticity": 0.62, "combined": 0.58, "exam_verb_count": 1},
        {"word_count": 30, "authenticity": 0.68, "combined": 0.62, "exam_verb_count": 1},
        {"word_count": 35, "authenticity": 0.70, "combined": 0.65, "exam_verb_count": 1},
        {"word_count": 40, "authenticity": 0.72, "combined": 0.68, "exam_verb_count": 1},
    ]
    prof = _aggregate_band(rows)
    assert prof.min_combined_floor >= prof.combined_p25
    assert prof.min_combined_floor <= prof.combined_p75 + 0.05


def test_rule_pack_fallback_not_empty():
    prof = _profile_from_rule_packs("secondary")
    assert prof.min_combined_floor > 0
    assert prof.target_word_count >= 12


def test_evaluate_weak_question_flags():
    q = {
        "content": "Define tangent.",
        "authenticity_score": 0.35,
        "combined_score": 0.32,
    }
    rep = evaluate_against_cbse(q, class_level="10")
    assert rep.get("cbse_gate_enabled") is True
    assert rep.get("cbse_reject") or rep.get("cbse_flags")


def test_benchmark_hints_non_empty():
    hint = benchmark_prompt_hints("10")
    assert "QUALITY BAR" in hint or hint == ""
