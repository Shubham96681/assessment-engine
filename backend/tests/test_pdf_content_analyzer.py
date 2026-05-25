"""PDF-driven chapter and theorem extraction (no NCERT hardcoding)."""
from app.generation.pdf_content_analyzer import (
    extract_theorems_from_pdf,
    extract_subtopics_from_pdf,
    infer_locked_chapter_from_pdf,
    extract_primary_topic_from_pdf,
)
from app.generation.topic_extractor import build_topic_profile


TRIG_BLOB = """
TRIGONOMETRIC FUNCTIONS
Chapter 3 : Trigonometric Functions
EXERCISE 3.1
1. Find the radian measures corresponding to the following
2. Find the degree measures corresponding to the following
EXERCISE 3.2
1. cos x - 1
2. sin x = 3/5
Theorem 3.1 : sin²θ + cos²θ = 1
Prove that (1 + tan²θ) = sec²θ
"""


def test_trig_filename_wins_over_circle_subtopics():
    """NCERT ch.3 Ex 3.1 includes circle chord drills — filename must still lock trig."""
    subs = [
        "5. In a circle of diameter 40 cm, the length of a chord is",
        "6. If in two circles, arcs of the same length subtend angle",
    ]
    ch, src, _ = infer_locked_chapter_from_pdf(
        blob="\n".join(subs),
        filename="Class_11_Maths_Chapter_3_Trigonometric_Functions.pdf",
        subtopics=subs,
    )
    assert ch == "trigonometry"
    assert src == "filename_hint"


def test_trig_pdf_content_not_triangles():
    ch, src, conf = infer_locked_chapter_from_pdf(
        blob=TRIG_BLOB,
        filename="Class_11_Maths_Chapter_3_Trigonometric_Functions.pdf",
    )
    assert ch == "trigonometry"
    assert src in ("pdf_content", "topic_focus", "filename_hint")
    assert conf > 0.4


def test_extract_theorems_from_pdf_text():
    thms = extract_theorems_from_pdf(TRIG_BLOB)
    assert len(thms) >= 1
    labels = " ".join(t["label"].lower() for t in thms)
    assert "sin" in labels or "prove" in labels or "theorem" in labels
    assert all(t.get("source") == "pdf_extract" for t in thms)


def test_subtopics_from_exercises():
    subs = extract_subtopics_from_pdf(TRIG_BLOB)
    assert any("exercise" in s.lower() for s in subs)
    assert any("radian" in s.lower() or "degree" in s.lower() for s in subs)


def test_primary_topic_from_pdf_not_generic_chapter():
    title = extract_primary_topic_from_pdf(
        blob=TRIG_BLOB,
        filename="Class_11_Maths_Chapter_3_Trigonometric_Functions.pdf",
    )
    assert "trigonometric" in title.lower() or "function" in title.lower()


def test_build_profile_no_pythagoras_catalog_dump():
    profile = build_topic_profile(
        document_id="t",
        filename="Class_11_Maths_Chapter_3_Trigonometric_Functions.pdf",
        chunks=[{"text": TRIG_BLOB}],
    )
    assert profile["locked_chapter"] == "trigonometry"
    ids = [t["id"] for t in profile["required_theorems"]]
    assert "pythagoras" not in ids
    assert "similar_triangles" not in ids
