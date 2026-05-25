"""Chapter detection and prompt dominance for trigonometry / triangles."""
from app.generation.author_imperfections import chapter_imperfection_prompt_block
from app.generation.chapter_concept_classifier import resolve_locked_chapter
from app.generation.paper_uniqueness import build_rag_uniqueness_block
from app.generation.rd_archetypes import detect_chapter_key
from app.generation.semantic_section_weight import validate_section_dominance


def test_trigonometry_archetype_pool_not_empty_after_filter():
    from app.generation.rd_archetypes import pick_weighted_archetypes
    from app.generation.archetype_registry import filter_archetype_dicts

    arch = pick_weighted_archetypes(5, "trigonometry", ui_difficulty="hard", full_hard=True)
    filtered = filter_archetype_dicts(arch, "trigonometry")
    assert len(filtered) == 5
    assert all(a["id"] in {"standard_angle", "identity_prove", "quadrant_reduction", "ratio_find", "radian_degree", "hots_trig"} for a in filtered)


def test_trigonometric_filename_not_arithmetic():
    fn = "Class_11_Maths_Chapter_3_Trigonometric_Functions.pdf"
    assert detect_chapter_key("", fn, "") == "trigonometry"
    ch, source, _ = resolve_locked_chapter(filename=fn, context="")
    assert ch == "trigonometry"
    assert source in ("filename_hint", "pdf_content", "topic_focus")


def test_class11_chapter3_subtopics_not_triangles():
    from app.generation.topic_extractor import build_topic_profile
    from app.generation.chapter_concept_classifier import refine_locked_chapter

    fn = "Class_11_Maths_Chapter_3_Trigonometric_Functions.pdf"
    subs = [
        "EXERCISE 3.2",
        "1. cos x – 1",
        "2. sin x 3",
        "8. tan 19π",
    ]
    blob = "\n".join(subs) + "\n sin cos tan radian degree measure"
    ch, src, conf = refine_locked_chapter(
        "triangles",
        "pdf_content",
        0.5,
        filename=fn,
        context=blob,
        subtopics=subs,
    )
    assert ch == "trigonometry"
    assert src in ("pdf_content", "filename_hint", "topic_focus")

    profile = build_topic_profile(
        document_id="test",
        filename=fn,
        chunks=[{"text": blob}],
    )
    assert profile["locked_chapter"] == "trigonometry"
    assert "pythagoras" not in [t["id"] for t in profile["required_theorems"]]
    assert "Trigonometric" in profile["primary_topic"] or "trigonometric" in profile[
        "primary_topic"
    ].lower()


def test_triangles_prompt_dominance_with_only_ban_lines():
    prompt = """
LOCKED CHAPTER: triangles (key=triangles).
CHAPTER RULES — Triangles ONLY:
Do NOT use in any stem, figure, or answer: circle, tangent, secant, radius, concentric, discriminant, quadratic.
HARD MODE — Triangles / similarity only:
- Spread: similarity ratio, congruence (RHS/SAS), Pythagoras, area ratio, proof+Hence.
REASONING DIVERSITY — Triangles:
- Spread similarity, congruence, Pythagoras, area ratio — not circle or quadratic graphs.
In triangle ABC, DE is parallel to BC. If AD = 3 cm and DB = 6 cm, find AE : EC.
Prove that triangles PQR and PST are similar when ST is parallel to QR.
"""
    report = validate_section_dominance(prompt, "triangles", max_foreign_ratio=0.1)
    assert report["section_dominance_ok"], report.get("section_dominance_flags")


def test_trig_prompt_dominance_with_chapter_aware_blocks():
    ub = build_rag_uniqueness_block(
        generation_num=1,
        prior_stems=[],
        chapter="trigonometry",
        question_count=5,
        full_hard=True,
    )
    imp = chapter_imperfection_prompt_block("trigonometry", question_count=5)
    prompt = f"""
LOCKED CHAPTER: trigonometry (key=trigonometry).
CHAPTER RULES — Trigonometry ONLY:
Do NOT use in any stem, figure, or answer: circle, tangent, secant, radius, concentric, discriminant, quadratic.
HARD MODE — Trigonometry only:
- Spread: radian conversion, ratio find, reduction, standard angle, identity prove.
{ub}
{imp}
Convert 315° to radians. If cos φ = −3/5 and φ lies in QIII, find sin φ and tan φ.
Find tan(19π/3). Prove that (1 + cot²λ) = cosec²λ. Hence find cot λ when sin λ = 3/5.
"""
    report = validate_section_dominance(prompt, "trigonometry", max_foreign_ratio=0.1)
    assert report["section_dominance_ok"], report.get("section_dominance_flags")


def test_trig_dominance_ignores_prior_circle_stems_in_never_repeat():
    from app.generation.prompts import _format_exclude_prior_block
    from app.generation.semantic_section_weight import validate_section_dominance

    priors = [
        "Express 315° in radian measure.",
        "In a circle with centre O, prove the line is tangent at S.",
        "Circles with centres G and H have radii 3 cm and 8 cm.",
    ]
    block = _format_exclude_prior_block(priors, locked_chapter="trigonometry")
    prompt = (
        "LOCKED CHAPTER: trigonometry\n"
        "CHAPTER RULES — Trigonometry ONLY:\n"
        "Do NOT use: circle, secant, concentric.\n"
        f"{block}\n"
        "Convert 510° to radians. Find sin 765°."
    )
    report = validate_section_dominance(prompt, "trigonometry", max_foreign_ratio=0.1)
    assert report["section_dominance_ok"], report.get("section_dominance_flags")
