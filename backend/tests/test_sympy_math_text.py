from app.generation.question_text import ensure_plain_text
from app.generation.sympy_math_text import (
    apply_sympy_math_symbols,
    normalize_angle_notation,
    sympy_available,
)


def test_sympy_available():
    assert sympy_available()


def test_trig_spaced_theta():
    out = apply_sympy_math_symbols("Prove sin 5 theta = 16 sin theta cos theta.")
    assert "θ" in out
    assert "sin(5" in out or "sin(5θ)" in out.replace(" ", "")


def test_angle_vertex_unicode():
    out = normalize_angle_notation("If angle ATB = 60°, find angle AOB.")
    assert "∠ATB" in out
    assert "∠AOB" in out


def test_ensure_plain_uses_sympy():
    out = ensure_plain_text("In triangle ABC, angle A = pi/2. sin 5theta for 0 <= theta <= 90.")
    assert "∠A" in out
    assert "π" in out
    assert "θ" in out


def test_strip_hr_still_works():
    out = ensure_plain_text("90°. <hr/>Hence, find sin theta.")
    assert "hr/" not in out.lower()
    assert "Hence" in out
