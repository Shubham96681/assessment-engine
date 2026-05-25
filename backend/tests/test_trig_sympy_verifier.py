"""Paper 8 — SymPy trigonometry verification."""
from app.generation.math_stem_validator import should_reject_math_stem
from app.generation.trig_sympy_verifier import evaluate_trig_sympy, should_reject_trig_sympy


def _q(stem: str, answer: str = "Step 1: work. Hence result.") -> dict:
    return {"content": stem, "correct_answer": answer}


def test_paper8_q1_quadrant_tan():
    stem = (
        "If tan θ = 1/3 and θ lies in quadrant II, find sin θ cos θ. "
        "Answer claims sin θ cos θ = √10/3."
    )
    assert should_reject_trig_sympy(_q(stem), locked_chapter="trigonometry")


def test_paper8_q1_sin_cos_value():
    stem = "If tan θ = 1/3, find sin θ cos θ. Model answer: sin θ cos θ = √10/3."
    r = evaluate_trig_sympy(_q(stem), locked_chapter="trigonometry")
    assert "sin_cos_theta_value_inconsistent" in r["trig_sympy_critical"]


def test_paper8_q1_self_referential():
    stem = "Prove tan(A+B) formula. find tan A given tan A = 2 and tan B = 3."
    assert should_reject_trig_sympy(_q(stem), locked_chapter="trigonometry")


def test_paper8_q2_sin_cos_not_unit():
    stem = "If tan A = 2 and tan B = 3, find cos(A+B) and sin(A+B)."
    ans = "(i) cos(A+B) = -7/13 (ii) sin(A+B) = -24/13"
    r = evaluate_trig_sympy(_q(stem, ans), locked_chapter="trigonometry")
    assert "sin_cos_ab_not_unit" in r["trig_sympy_critical"]


def test_paper8_q2_false_tan_product():
    stem = "Prove tan A tan B = (tan A + tan B)/(tan A - tan B) for A ≠ B."
    assert should_reject_math_stem(_q(stem), locked_chapter="trigonometry")


def test_paper8_q3_trivial_tan5():
    stem = "Prove tan(5θ) = tan(2θ + 3θ). Hence proved."
    assert should_reject_trig_sympy(_q(stem), locked_chapter="trigonometry")


def test_paper8_q4_right_triangle():
    stem = (
        "In triangle ABC, ∠A = 90°. If tan B = 3 and tan C = 1/4, find tan A."
    )
    assert should_reject_trig_sympy(_q(stem), locked_chapter="trigonometry")


def test_paper8_q4_find_tan_a():
    stem = "In triangle ABC, angle A = 90°. find tan A if tan(A+B) = 3/2."
    assert should_reject_trig_sympy(_q(stem), locked_chapter="trigonometry")


def test_paper8_q5_false_sin5():
    stem = "Prove sin(5θ) = 16 sin θ cos θ (1 - 10 sin²θ cos²θ)."
    assert should_reject_trig_sympy(_q(stem), locked_chapter="trigonometry")


def test_paper9_q3_tan_vs_cos():
    stem = (
        "Given cos A cos B - sin A sin B = 1/7, prove tan(A + B) = 287/290. "
        "sin(A + B) = 36/155, cos(A + B) = 6/155."
    )
    r = evaluate_trig_sympy(_q(stem), locked_chapter="trigonometry")
    assert "tan_ab_inconsistent_with_cos_ab" in r["trig_sympy_critical"] or (
        "sin_cos_ab_not_unit" in r["trig_sympy_critical"]
    )


def test_paper9_q4_false_cos_sum():
    stem = (
        "cos(A + B + C) = cos A cos B cos C + sin A sin B sin C. "
        "prove cos(5θ) expansion."
    )
    assert should_reject_trig_sympy(_q(stem), locked_chapter="trigonometry")


def test_paper9_q5_sin_ac():
    stem = (
        "In ΔABC, ∠A = 30°, ∠C = 60°. "
        "Calculate sin(A + C) using tan(A + B) = (tan A + tan B)/(1 - tan A tan B)."
    )
    ans = (
        "tan(90) = (tan 30° + tan 60°)/(1 - tan 30° tan 60°). "
        "sin(90) = (sin 30° cos 60° + cos 30° sin 60°)/cos 60°."
    )
    r = evaluate_trig_sympy(_q(stem, ans), locked_chapter="trigonometry")
    assert "tan_90_undefined_used" in r["trig_sympy_critical"]
    assert "sin_90_wrong_formula_divide_cos60" in r["trig_sympy_critical"]


def test_valid_question_passes():
    stem = (
        "(i) Prove tan(A+B) = (tan A + tan B)/(1 - tan A tan B). "
        "(ii) If tan θ = 1/2, θ acute, find tan 2θ."
    )
    ans = "Step 1: Addition formula. Step 2: tan 2θ = 4/3. Hence tan 2θ = 4/3."
    assert not should_reject_trig_sympy(_q(stem, ans), locked_chapter="trigonometry")
