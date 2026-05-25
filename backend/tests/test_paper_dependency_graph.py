"""Tests for paper-level theorem dependency graph."""
from app.generation.paper_dependency_graph import (
    apply_paper_dependency_enforcement,
    build_paper_dependency_plan,
    enforce_slot_stem,
    validate_slot_dependency,
)
from app.generation.paper_dependency_graph import SlotDependency


def test_build_circles_hard_plan_enabled():
    plan = build_paper_dependency_plan(
        chapter="circles",
        question_count=5,
        slots=[],
        ui_difficulty="hard",
        full_hard=True,
    )
    assert plan.enabled
    assert len(plan.slots) == 5
    assert plan.slot_dep(2).depends_on_slots == [1]
    assert plan.slot_dep(5).depends_on_slots == [1, 2]


def test_enforce_q2_reference_and_parts():
    dep = SlotDependency(
        slot=2,
        depends_on_slots=[1],
        must_reference_questions=[1],
        required_parts=("(i)", "(ii)"),
        ban_scaffolded_chord=True,
    )
    q = {
        "content": (
            "Concentric circles with centre O have outer radius 13 cm and inner radius 4 cm; "
            "a chord of the outer circle touching the inner circle has length 2√153 cm. "
            "From P, tangent PA = 6 cm and PB = 4 cm. Find BC."
        ),
    }
    stem, changed = enforce_slot_stem(q, dep, slot_index=1)
    assert changed
    assert "Question 1" in stem or "question 1" in stem.lower()
    assert "2√" not in stem and "sqrt" not in stem.lower()


def test_validate_missing_reference_flags():
    dep = SlotDependency(slot=2, depends_on_slots=[1], must_reference_questions=[1])
    q = {"content": "Find BC given PA = 6 and PB = 4.", "correct_answer": "BC = 5 cm."}
    report = validate_slot_dependency(q, dep)
    assert "stem_missing_ref_Q1" in report["paper_dependency_flags"]
    assert report["paper_dependency_score"] < 0.8


def test_apply_enforcement_cites_answer():
    plan = build_paper_dependency_plan(
        chapter="circles",
        question_count=3,
        slots=[],
        ui_difficulty="hard",
    )
    assert plan.enabled
    questions = [
        {
            "content": "Find chord UV.",
            "correct_answer": "UV = 2√153 cm.",
            "slot_number": 1,
            "order_index": 0,
        },
        {
            "content": "Tangent PA = 6, PB = 4. Find BC.",
            "correct_answer": "BC = 5 cm.",
            "slot_number": 2,
            "order_index": 1,
        },
        {
            "content": "Hence find fusion length.",
            "correct_answer": "5 cm.",
            "slot_number": 3,
            "order_index": 2,
        },
    ]
    out = apply_paper_dependency_enforcement(questions, plan)
    q2 = next(q for q in out if int(q.get("slot_number") or 0) == 2)
    assert "Question 1" in q2["content"] or "question 1" in q2["content"].lower()
    assert "Question 1" in q2["correct_answer"]
