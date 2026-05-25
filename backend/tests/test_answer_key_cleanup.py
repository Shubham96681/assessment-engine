"""Answer key cosmetic fixes — Unicode math, no garbage secant line."""
from app.generation.answer_sync import build_fusion_answer, build_tangent_secant_answer
from app.generation.question_text import (
    ensure_plain_text,
    fix_secant_answer_variables,
    to_reportlab_markup,
)


def test_tangent_secant_no_pt_garbage():
    ans = build_tangent_secant_answer(15, 9, outer_r=29)
    assert "secant P to T" not in ans
    assert "PT = 34" not in ans
    assert "PR = 25" in ans


def test_fusion_sqrt_unicode():
    ans = build_fusion_answer(29, 15, 34, 9)
    assert "square root of" not in ans
    assert "√1066" in ans


def test_finalize_digit_superscript_and_sqrt():
    raw = "OP^2 = 29^2 + 15^2; square root of 1066 cm"
    out = ensure_plain_text(raw)
    assert "29²" in out
    assert "√1066" in out
    assert "square root of" not in out


def test_finalize_mathsf_and_models_remnants():
    raw = "inner radius O modelssq Zcm; Gmathsf mathsf H=17cm"
    out = ensure_plain_text(raw)
    assert "mathsf" not in out
    assert "modelssq" not in out
    assert "OF = 21" in out or "OF = 21 cm" in out
    assert "GH" in out and "17" in out


def test_mathsf_pb_becomes_pr_for_secant():
    stem = "secant PQR with PQ = 9 cm. Find PR and verify PA^2 = PQ x PR."
    bad = r"Step 5: Therefore \mathsf{P B}=25cm"
    fixed = fix_secant_answer_variables(stem, ensure_plain_text(bad))
    assert "PR" in fixed
    assert "PB" not in fixed


def test_reportlab_superscript_markup():
    mk = to_reportlab_markup("PA² = PQ × PR")
    assert "<sup>2</sup>" in mk
    assert "PA²" not in mk or "<sup>" in mk


def test_secant_garbage_stripped_from_answer():
    raw = (
        "Therefore PR = 25 cm and the full secant P to T is PT = 34 cm."
    )
    out = ensure_plain_text(raw)
    assert "secant P to T" not in out
    assert "PT = 34" not in out
