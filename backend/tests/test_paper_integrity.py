"""Paper integrity — forward refs, self-ref, duplicate stems."""
from app.generation.paper_integrity import validate_paper_integrity


def test_forward_reference_rejected():
    bad = [
        {
            "id": "1",
            "slot_number": 1,
            "order_index": 0,
            "content": "Using outer circle from Question 1 and tangent-secant at Q from Question 2.",
        },
        {"id": "2", "slot_number": 2, "order_index": 1, "content": "Tangent QR = 10 cm."},
    ]
    r = validate_paper_integrity(bad, chapter="circles", expected_count=2)
    assert not r["paper_integrity_ok"]
    assert any("forward_reference" in f or "self_reference" in f for f in r["paper_integrity_flags"])


def test_valid_concentric_chain():
    good = [
        {
            "id": "1",
            "slot_number": 1,
            "order_index": 0,
            "content": "Two concentric circles centre P radii 17 cm and 8 cm. Chord UV touches inner at T. Find UV.",
        },
        {
            "id": "2",
            "slot_number": 2,
            "order_index": 1,
            "content": "In the same concentric circles as in Question 1. (i) Find chord UV. (ii) Hence tangent QR=10.",
        },
        {
            "id": "5",
            "slot_number": 5,
            "order_index": 4,
            "content": "Using the outer circle from Question 1 and tangent-secant at Q from Question 2.",
        },
    ]
    r = validate_paper_integrity(good, chapter="circles", expected_count=3)
    assert r["paper_integrity_ok"], r["paper_integrity_flags"]
