"""Question type planner — FigureBased floor for geometry."""
from app.generation.chapter_rule_packs import get_chapter_rule_pack
from app.generation.question_type_planner import resolve_effective_question_types


def test_circles_all_figure_based():
    pack = get_chapter_rule_pack("circles")
    types = resolve_effective_question_types(
        chapter="circles",
        pack=pack,
        types=["MCQ", "ShortAnswer"],
        question_count=5,
        ui_difficulty="hard",
    )
    assert types.count("FigureBased") == 5


def test_circles_with_only_mcq_still_gets_figures():
    pack = get_chapter_rule_pack("circles")
    types = resolve_effective_question_types(
        chapter="circles",
        pack=pack,
        types=["MCQ"],
        question_count=5,
        ui_difficulty="medium",
    )
    assert types.count("FigureBased") >= 4
