"""Tests for math_stem_validator — Paper 7 failure modes."""
from app.generation.math_stem_validator import (
    evaluate_math_stem,
    should_reject_math_stem,
)


def test_rejects_false_tan_formula():
    q = {
        "content": (
            "Prove tan(A+B) = (tan A + tan B - tan A tan B) / (1 + tan A tan B)."
        ),
        "correct_answer": "Step 1: hence formula.",
    }
    r = evaluate_math_stem(q, locked_chapter="trigonometry")
    assert not r["math_stem_ok"]
    assert "false_tan_a_plus_b_formula" in r["math_stem_critical"]


def test_rejects_calculus_in_trigonometry():
    q = {
        "content": "Prove that ∫(sin 2x / cos x) dx = -cos 2x + 2cos x + ∑ + C.",
        "correct_answer": "Step 1: substitute sin 2x.",
    }
    assert should_reject_math_stem(q, locked_chapter="trigonometry")


def test_rejects_unicode_garbage_answer():
    q = {
        "content": "In ΔABC, right-angled at C, prove ωA = π + π/2.",
        "correct_answer": "[('Step 1': '0394 ABC'), ('Hence': '03 c9 A')]",
    }
    r = evaluate_math_stem(q, locked_chapter="trigonometry")
    assert not r["math_stem_ok"]


def test_rejects_missing_angle_b():
    q = {
        "content": "If sin A = 5/13 and cos A = 12/13, find the value of tan(A + B).",
        "correct_answer": "Step 1: use formula.",
    }
    assert should_reject_math_stem(q, locked_chapter="trigonometry")


def test_rejects_false_tan_4theta():
    q = {
        "content": "Prove that tan(4θ) = (tan θ + sec²θ)/(1 + tan θ sec²θ).",
        "correct_answer": "Step 1: expand.",
    }
    assert should_reject_math_stem(q, locked_chapter="trigonometry")


def test_accepts_valid_tan_identity():
    q = {
        "content": (
            "(i) Prove tan(A+B) = (tan A + tan B)/(1 - tan A tan B). "
            "(ii) If tan θ = 1/2, θ acute, find tan 2θ."
        ),
        "correct_answer": (
            "Step 1: Standard addition formula. "
            "Step 2: tan 2θ = 2(1/2)/(1-1/4) = 4/3. Hence tan 2θ = 4/3."
        ),
    }
    r = evaluate_math_stem(q, locked_chapter="trigonometry")
    assert r["math_stem_ok"]
