"""Answer formatting — labels, list/dict blobs, fractions."""
from app.generation.answer_format import (
    ensure_answer_text,
    format_structured_answer,
    strip_subpart_prefixes,
)


def test_no_duplicate_labels():
    raw = "['(i) sin θ cos θ = √10/3,', '(ii) tan(A+B) = (tan A + tan B)/(1 - tan A tan B)', '(iii) tan A = 25/23']"
    out = format_structured_answer(raw)
    assert "(i) (i)" not in out
    assert out.startswith("(i)")
    assert "(ii)" in out
    assert "(j)" not in out


def test_dict_blob():
    raw = "('prove': 'sin(2θ) = 2 sin θ cos θ', 'hence': 'Hence proved.')"
    out = format_structured_answer(raw)
    assert "(i)" in out
    assert "prove" not in out.lower() or "sin(2" in out


def test_strip_double_prefix():
    assert strip_subpart_prefixes("(j) (ii) cos(A+B) = -7/13") == "cos(A+B) = -7/13"


def test_remove_empty_mno():
    raw = "(i) Given ∠A = 90°.\n(m),\n(n),\n(o),"
    out = format_structured_answer(raw)
    assert "(m)" not in out
    assert "(n)" not in out


def test_trailing_comma():
    raw = "(i) sin θ cos θ = √10/3,"
    out = format_structured_answer(raw)
    assert not out.endswith(",")


def test_gibberish_q5_placeholder():
    raw = "('prove': 'B ) cos| A---| \\\\2/ ', 'hence': 'x')"
    out = format_structured_answer(raw)
    assert "incomplete" in out.lower() or len(out) < 20


def test_unglue_subparts():
    from app.generation.answer_format import unglue_subparts

    raw = "(i) sin θ cos θ = √10/3(ii) tan(A+B) = (tan A + tan B)/(1 - tan A tan B)"
    out = unglue_subparts(raw)
    assert "(ii)" in out
    assert "3(ii)" not in out.replace(" ", "")


def test_split_answer_subparts():
    from app.generation.answer_format import split_answer_subparts

    raw = "(i) sin θ cos θ = √10/3(ii) tan(A+B) = x (iii) tan A = 25/23"
    parts = split_answer_subparts(raw)
    assert len(parts) >= 3
    assert parts[0][0] == "(i)"
    assert "√10" in parts[0][1] or "10" in parts[0][1]


def test_ensure_answer_preserves_math():
    out = ensure_answer_text("(i) cos(A+B) = -7/13")
    assert "cos" in out.lower()
    assert "-7" in out or "7/13" in out
