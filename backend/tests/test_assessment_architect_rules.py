"""Assessment architect protocol — prompts and quality gates."""
from app.generation.assessment_architect_rules import (
    classify_forbidden_hard_stem,
    classify_forbidden_angles,
    compute_difficulty_score,
    difficulty_label_from_score,
    evaluate_architect_compliance,
    should_reject_architect_violation,
    suggest_marks_from_answer,
    validate_paper_architect,
    variance_matrix_prompt_block,
)
from app.generation.hard_mode_calibration import should_reject_hard_mode
from app.generation.prompt_builder import PromptBuilder


def test_classify_bare_trig_find():
    tags = classify_forbidden_hard_stem("Find sin 765°.")
    assert "bare_periodicity_find" in tags


def test_hence_sin2x_to_sin75_forbidden():
    stem = "(i) Prove sin 2x = 2 sin x cos x. (ii) Hence find sin 75°."
    tags = classify_forbidden_hard_stem(stem)
    assert "hence_wrong_base_double_to_75" in tags


def test_difficulty_score_hard_for_equation():
    stem = "Solve 2 sin²x + sin x - 1 = 0 for x ∈ [0, 2π). (i) Factor. (ii) List solutions. (iii) Count."
    score = compute_difficulty_score(stem, "Step 1: factor. Step 2: roots. Step 3: three.")
    assert score >= 7
    assert difficulty_label_from_score(score) in ("Hard", "Very Hard", "Extreme")


def test_architect_rejects_full_hard_bare_find():
    q = {"content": "Find cos 255° exactly.", "marks": 6}
    assert should_reject_architect_violation(
        q, full_hard=True, locked_chapter="trigonometry", ui_difficulty="hard"
    )


def test_variance_matrix_uses_skill_codes():
    block = variance_matrix_prompt_block("trigonometry", 10)
    assert 'id "1": category C-P' in block
    assert "T-E" in block
    assert "O-E" in block


def test_prompt_builder_architect_section():
    block = PromptBuilder.architect_section(
        chapter="trigonometry", question_count=10, full_hard=True
    )
    assert "STEP-COUNT DIFFICULTY" in block
    assert "ABSOLUTE PROHIBITIONS" in block


def test_forbidden_angle_17_5():
    assert classify_forbidden_angles("Find sin 17.5° in surd form.")


def test_validate_paper_mandatory_categories():
    questions = [
        {
            "content": "Solve sin x = 1/2 for x ∈ R. (i) General solution. (ii) Count in [0,2π).",
            "marks": 6,
            "correct_answer": "Step 1: x = nπ + (-1)^n π/6.",
        },
        {
            "content": "Maximize 3 sin x + 4 cos x. (i) R form. (ii) Max value.",
            "marks": 6,
            "correct_answer": "Step 1: R=5. Step 2: max=5.",
        },
        {
            "content": "Prove tan⁻¹(1/2) + tan⁻¹(1/3) = π/4.",
            "marks": 6,
            "correct_answer": "Step 1: tan sum formula.",
        },
        {
            "content": "(i) Prove sin(A+B). (ii) Hence find sin 75°. (iii) Numeric check.",
            "marks": 6,
            "correct_answer": "Step 1: identity. Step 2: surd.",
        },
    ]
    report = validate_paper_architect(questions, expected_count=4, locked_chapter="trigonometry")
    assert "T-E" in report["category_counts"]
    assert "O-E" in report["category_counts"]


def test_suggest_marks_caps_at_six():
    ans = "Step 1: " * 4 + "Hence result."
    assert suggest_marks_from_answer(ans) <= 6
