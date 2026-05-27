import json

from app.generation.rag_response_jinja import (
    canonicalize_rag_response_raw,
    parse_rag_response_structured,
    render_rag_response_file,
)


def test_render_and_roundtrip_rag_json():
    items = [
        {
            "id": "1",
            "type": "LongAnswer",
            "question": "Let p_n = s·p_{n-1} − t·p_{n-2}. Find p_4 when x² − 7x + 12 = 0.",
            "marks": 8,
            "correct_answer": "p_4 = 337",
        }
    ]
    raw = render_rag_response_file(items, sources="Unit test")
    assert raw.startswith("ANSWER:")
    assert "SOURCES USED:" in raw
    parsed, sources = parse_rag_response_structured(raw)
    assert len(parsed) == 1
    assert parsed[0]["id"] == "1"
    assert "p_{n-1}" in parsed[0]["question"] or "p_n" in parsed[0]["question"]
    assert sources == "Unit test"
    data = json.loads(raw.split("ANSWER:", 1)[1].split("SOURCES USED:")[0].strip())
    assert isinstance(data, list)


def test_canonicalize_existing_response():
    messy = """ANSWER:
[{"id":"2","type":"LongAnswer","question":"x^2 - 5x + 6 = 0","marks":6,"correct_answer":"roots 2,3"}]
SOURCES USED: prior paper
"""
    out = canonicalize_rag_response_raw(messy)
    parsed, src = parse_rag_response_structured(out)
    assert len(parsed) == 1
    assert parsed[0]["id"] == "2"
    assert "x²" in parsed[0]["question"] or "x^2" in parsed[0]["question"]
    assert src == "prior paper"
