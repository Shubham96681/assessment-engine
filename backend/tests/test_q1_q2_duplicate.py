"""Q2 must not repeat Q1 chord-find."""
from app.generation.paper_integrity import validate_paper_integrity


def test_q2_part_i_chord_duplicate_rejected():
    bad = [
        {
            "id": "1",
            "slot_number": 1,
            "order_index": 0,
            "content": "Two concentric circles radii 17 cm and 8 cm. Chord AB touches inner at T. Find AB.",
        },
        {
            "id": "2",
            "slot_number": 2,
            "order_index": 1,
            "content": "In the same concentric circles as in Question 1. (i) Find chord AB touching inner at T. (ii) Hence tangent PQ=12.",
        },
    ]
    r = validate_paper_integrity(bad, chapter="circles", expected_count=2)
    assert not r["paper_integrity_ok"]
    assert any("q2_part_i" in f for f in r["paper_integrity_flags"])


def test_q2_hence_only_accepted():
    good = [
        {
            "id": "1",
            "slot_number": 1,
            "order_index": 0,
            "content": "Two concentric circles centre O radii 17 cm and 8 cm. Chord AB touches smaller at T. Find AB.",
        },
        {
            "id": "2",
            "slot_number": 2,
            "order_index": 1,
            "content": "In the same concentric circles as in Question 1. Hence, tangent PQ=12 cm, secant PR=4 cm. Find RT.",
        },
    ]
    r = validate_paper_integrity(good, chapter="circles", expected_count=2)
    assert not any("q2_part_i" in f for f in r["paper_integrity_flags"])
