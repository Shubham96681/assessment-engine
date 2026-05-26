"""Computational verification for quadratic stems and model answers."""
from app.generation.quadratic_math_verify import (
    can_factorise_over_integers,
    expand_binomial_factors,
    parse_quadratic_equation,
    verify_quadratic_question_math,
)
from app.generation.quadratic_paper_quality import should_reject_quadratic_question_quality


def test_parse_quadratic():
    assert parse_quadratic_equation("22x² − 59x + 28 = 0") == (22, -59, 28)
    assert parse_quadratic_equation("10x² − 43x + 18 = 0") == (10, -43, 18)


def test_expand_factors_mismatch():
    assert expand_binomial_factors("(11x − 4)(2x − 7)") == (22, -85, 28)


def test_iteration3_q2_bad():
    q = {
        "question": "By factorisation only, solve 22x² − 59x + 28 = 0.",
        "correct_answer": "(11x − 4)(2x − 7) = 0 ⇒ x = 4/11 or 7/2.",
    }
    ev = verify_quadratic_question_math(q)
    assert not ev["math_verification_ok"]
    assert any("factorisation" in f for f in ev["math_verification_flags"])
    assert should_reject_quadratic_question_quality(q)


def test_iteration3_q2_fixed_stem():
    q = {
        "question": "By factorisation only, solve 22x² − 85x + 28 = 0.",
        "correct_answer": "(11x − 4)(2x − 7) = 0 ⇒ x = 4/11 or 7/2.",
    }
    ev = verify_quadratic_question_math(q)
    assert ev["math_verification_ok"]


def test_iteration3_q3_bad():
    q = {
        "question": "Find the roots by factorisation for 10x² − 43x + 18 = 0.",
        "correct_answer": "(5x − 2)(2x − 9) = 0.",
    }
    ev = verify_quadratic_question_math(q)
    assert not ev["math_verification_ok"]


def test_iteration3_q4_bad_answer():
    q = {
        "question": "Form 17x² − 68x + (p + 51) = 0. For equal real roots, find p from D = 0 and r.",
        "correct_answer": "D = 0 ⇒ p = 68. r = 2. 17(x − 2)² gives p + 51 = 68.",
    }
    ev = verify_quadratic_question_math(q)
    assert not ev["math_verification_ok"]
    assert any("D_nonzero" in f or "contradiction" in f for f in ev["math_verification_flags"])


def test_cannot_factorise_59():
    assert not can_factorise_over_integers(22, -59, 28)


def test_can_factorise_85():
    assert can_factorise_over_integers(22, -85, 28)


def test_rejects_speed_time_mismatch_120km():
    q = {
        "question": "A cyclist rides 120 km at s km/h and returns at (s + 6) km/h; return takes ½ h less.",
        "correct_answer": "s² + 6s − 1080 = 0. s = 30 km/h.",
    }
    ev = verify_quadratic_question_math(q)
    assert not ev["math_verification_ok"]
    assert any("speed_time" in f for f in ev["math_verification_flags"])


def test_accepts_speed_time_90km():
    q = {
        "question": "A cyclist rides 90 km at s km/h and returns at (s + 6) km/h, taking ½ hour less on the return.",
        "correct_answer": "s² + 6s − 1080 = 0. s = 30 km/h.",
    }
    ev = verify_quadratic_question_math(q)
    assert ev["math_verification_ok"]


def test_rejects_wrong_area_dimensions():
    q = {
        "question": "A rectangle has length (4x + 13) m and breadth (3x + 5) m and area 143 m².",
        "correct_answer": "x = 13/12. Length 73/3 m, breadth 11/4 m.",
    }
    ev = verify_quadratic_question_math(q)
    assert not ev["math_verification_ok"]
    assert any("area" in f for f in ev["math_verification_flags"])


def test_accepts_correct_area_dimensions():
    q = {
        "question": "A rectangle has length (4x + 13) m and breadth (3x + 5) m and area 143 m².",
        "correct_answer": "x = 13/12. Length 52/3 m, breadth 33/4 m; product 143 m².",
    }
    ev = verify_quadratic_question_math(q)
    assert ev["math_verification_ok"]


def test_rejects_or_root_difference_bad_q():
    q = {
        "question": "Answer ONE. (b) If x² − 12x + (q + 5) = 0 has roots differing by 6, find q.",
        "correct_answer": "q = 20. Roots 8 and 2.",
    }
    ev = verify_quadratic_question_math(q)
    assert not ev["math_verification_ok"]
    assert any("root_difference" in f for f in ev["math_verification_flags"])


def test_accepts_or_root_difference_good():
    q = {
        "question": "Answer ONE. (b) If x² − 12x + (q + 5) = 0 has roots differing by 6, find q.",
        "correct_answer": "q = 22. Roots 9 and 3.",
    }
    ev = verify_quadratic_question_math(q)
    assert ev["math_verification_ok"]


def test_accepts_correct_alpha_squared_sum():
    q = {
        "question": "The equation 6x² − 61x + 10 = 0 has roots α and β.",
        "correct_answer": "α² + β² = (61/6)² − 2(10/6) = 3721/36 − 20/6 = 3601/36.",
    }
    ev = verify_quadratic_question_math(q)
    assert ev["math_verification_ok"]


def test_rejects_wrong_alpha_squared_sum():
    q = {
        "question": "The equation 6x² − 61x + 10 = 0 has roots α and β.",
        "correct_answer": "α² + β² = (61/6)² − 2(10/6) = 3721/36 − 20/6 = 2921/36.",
    }
    ev = verify_quadratic_question_math(q)
    assert not ev["math_verification_ok"]
    assert any("alpha_squared" in f for f in ev["math_verification_flags"])
