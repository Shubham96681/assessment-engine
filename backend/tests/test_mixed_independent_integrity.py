"""Mixed-independent paper integrity — slot roles and gap fill."""
from app.generation.paper_integrity import (
    question_matches_slot_role,
    validate_paper_integrity,
)
from app.generation.paper_repair import fill_missing_paper_slots, repair_duplicate_signatures
from app.generation.paper_templates import resolve_paper_template


def test_mixed_independent_accepts_secant_slot4():
    q = {
        "content": (
            "From external point P, tangent PT = 6 cm touches at T; "
            "secant PQR has PQ = 4 cm. Find PR."
        ),
    }
    assert question_matches_slot_role(
        q, 4, chapter="circles", paper_template_id="mixed_independent"
    )


def test_mixed_independent_proof_slot3():
    q = {"content": "Prove that tangents from X to a circle are equal."}
    assert question_matches_slot_role(
        q, 3, chapter="circles", paper_template_id="mixed_independent"
    )


def test_persist_paper_template_id(tmp_path, monkeypatch):
    from app.generation import topic_isolation as ti

    state_file = tmp_path / "rag_topic_state.json"
    monkeypatch.setattr(ti, "TOPIC_STATE_FILE", state_file)
    ti.persist_paper_template_id("mixed_independent")
    assert ti.get_current_topic_state().get("paper_template_id") == "mixed_independent"


def test_plan_template_id_wins_over_hard_auto():
    """Finalize must not re-tier mixed_independent → chained when plan says mixed."""
    tmpl = resolve_paper_template(
        chapter="circles",
        ui_difficulty="hard",
        question_count=5,
        full_hard=True,
        plan_template_id="mixed_independent",
    )
    assert tmpl.id == "mixed_independent"


def test_mixed_paper_passes_integrity_with_secant_and_case_study():
    qs = [
        {
            "slot_number": 1,
            "content": "Circles with centres P and Q, radii 5 cm and 3 cm, PQ = 10 cm. Find direct common external tangent length.",
        },
        {
            "slot_number": 2,
            "content": "From external point T, tangent TA = 9 cm; secant TBC, TB = 4 cm. Find TC.",
        },
        {
            "slot_number": 3,
            "content": "Prove that tangents drawn from an external point to a circle are equal in length.",
        },
        {
            "slot_number": 4,
            "content": "Tangents PM and PN from P to a circle with centre O, radius 9 cm. If angle MPN = 52°, find angle MON.",
        },
        {
            "slot_number": 5,
            "content": "A circle has centre O, radius 10 cm. Chord CD = 16 cm. (i) Find OM where M is midpoint of CD. (ii) Hence tangent from E, OE = 13 cm.",
        },
    ]
    r = validate_paper_integrity(
        qs, chapter="circles", expected_count=5, paper_template_id="mixed_independent"
    )
    assert r["paper_integrity_ok"] is True
    assert not any("slot_role_mismatch" in f for f in r["paper_integrity_flags"])


def test_fill_missing_slot():
    qs = [
        {"slot_number": 1, "content": "Concentric find AB.", "question_type": "FigureBased"},
        {"slot_number": 2, "content": "Tangent secant from P.", "question_type": "FigureBased"},
        {"slot_number": 3, "content": "Prove that PA = PB.", "question_type": "FigureBased"},
        {"slot_number": 4, "content": "Common external tangent find.", "question_type": "FigureBased"},
    ]
    filled = fill_missing_paper_slots(qs, 5, chapter="circles")
    assert len(filled) == 5
    assert filled[4].get("slot_gap_filled")


def test_repair_duplicate_secant_signatures():
    dup = (
        "From external point P, tangent PT = 6 cm; secant PQR, PQ = 4 cm. Find PR."
    )
    qs = [
        {"slot_number": 1, "content": "Two concentric radii 17 and 8 chord AB.", "question_type": "FigureBased"},
        {"slot_number": 2, "content": "Tangent from K length 9.", "question_type": "FigureBased"},
        {"slot_number": 3, "content": "Prove that RC = RD.", "question_type": "FigureBased"},
        {"slot_number": 4, "content": dup, "question_type": "FigureBased"},
        {"slot_number": 5, "content": dup, "question_type": "FigureBased"},
    ]
    fixed = repair_duplicate_signatures(qs, chapter="circles")
    r = validate_paper_integrity(
        fixed, chapter="circles", expected_count=5, paper_template_id="mixed_independent"
    )
    flags = " ".join(r["paper_integrity_flags"])
    assert "canonical_signature_duplicates" not in flags
