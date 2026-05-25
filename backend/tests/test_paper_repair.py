"""Auto-repair pipeline — Q2 dedup, concentric radii, LaTeX."""
from app.generation.paper_repair import (
    repair_concentric_stem_radii,
    repair_paper_questions,
    strip_q2_duplicate_chord_part,
)
from app.generation.paper_integrity import validate_paper_integrity


def test_strip_q2_part_i():
    stem = (
        "In the same concentric circles as in Question 1. (i) Find chord AB touching inner at T. "
        "(ii) Hence, tangent PQ = 12 cm, secant PR = 4 cm. Find RT."
    )
    out = strip_q2_duplicate_chord_part(stem)
    assert "(i)" not in out.lower() or "chord" not in out.split("hence")[0].lower()
    assert out.lower().startswith("in the same") or out.lower().startswith("hence")


def test_repair_concentric_radii():
    stem = "Two concentric circles centre O radii 18 cm and 8 cm. Chord AB touches inner at T. Find AB."
    new, ch = repair_concentric_stem_radii(stem)
    assert ch
    assert "17 cm and 8 cm" in new


def test_repair_paper_q2_duplicate():
    qs = [
        {
            "id": "1",
            "slot_number": 1,
            "order_index": 0,
            "content": "Two concentric circles centre O radii 18 cm and 8 cm. Chord AB touches inner at T. Find AB.",
            "question_type": "FigureBased",
        },
        {
            "id": "2",
            "slot_number": 2,
            "order_index": 1,
            "content": (
                "In the same concentric circles as in Question 1. (i) Find chord AB touching inner at T. "
                "(ii) Hence, tangent PQ = 12 cm, secant PR = 4 cm. Find RT."
            ),
            "question_type": "FigureBased",
        },
    ]
    fixed = repair_paper_questions(qs, chapter="circles", re_enrich_figures=False)
    r = validate_paper_integrity(fixed, chapter="circles", expected_count=2)
    assert not any("q2_part_i" in f for f in r["paper_integrity_flags"])
    assert "17 cm and 8 cm" in fixed[0]["content"]


def test_repair_duplicate_common_tangent_slot3_slot4():
    dup = (
        "Two circles have centres A and B, radii 7 cm and 2 cm respectively, and AB = 25 cm. "
        "Find the length of a direct common external tangent touching both circles."
    )
    qs = [
        {
            "slot_number": 1,
            "content": "Two concentric circles centre O radii 17 cm and 8 cm. Chord EF touches inner at G. Find EF.",
            "question_type": "FigureBased",
        },
        {
            "slot_number": 2,
            "content": "Using the configuration in Question 1. Hence tangent UV = 10 cm, secant UPQ, UP = 4 cm.",
            "question_type": "FigureBased",
        },
        {
            "slot_number": 3,
            "content": dup,
            "question_type": "FigureBased",
            "archetype_id": "common_tangent",
        },
        {
            "slot_number": 4,
            "content": dup,
            "question_type": "FigureBased",
            "archetype_id": "common_tangent",
        },
        {
            "slot_number": 5,
            "content": "In the configuration of Question 1, with UV from Question 2. (i) Find OU. (ii) Hence fusion.",
            "question_type": "FigureBased",
        },
    ]
    fixed = repair_paper_questions(qs, chapter="circles", re_enrich_figures=False)
    s3 = fixed[2]["content"].lower()
    s4 = fixed[3]["content"].lower()
    assert s3 != s4
    assert "prove" in s3 and "only at" in s3 or "meets the circle only" in s3
    r = validate_paper_integrity(fixed, chapter="circles", expected_count=5)
    flags = " ".join(r["paper_integrity_flags"])
    assert "duplicate_stem:slot3_slot4" not in flags
    assert "canonical_signature_duplicates" not in flags
