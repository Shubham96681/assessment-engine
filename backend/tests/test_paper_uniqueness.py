"""Per-generation uniqueness vs prior papers while keeping slot chain."""
from app.generation.paper_uniqueness import (
    build_rag_uniqueness_block,
    extract_concentric_pairs,
    pick_fresh_concentric_pair,
    pick_label_rotation,
    validate_unique_vs_priors,
)

PRIOR_Q1 = (
    "Two concentric circles have centre O and radii 29 cm and 21 cm. "
    "A chord DE of the larger circle touches the smaller circle at T. Find DE."
)
NEW_Q1 = (
    "Two concentric circles have centre O and radii 20 cm and 12 cm. "
    "A chord CD of the larger circle touches the smaller circle at T. Find CD."
)


def test_pick_fresh_concentric_avoids_used():
    used = extract_concentric_pairs([PRIOR_Q1])
    assert (29, 21) in used
    R, r, chord = pick_fresh_concentric_pair(2, used)
    assert (R, r) != (29, 21)
    assert chord > 0


def test_uniqueness_block_mentions_forbidden_pairs():
    block = build_rag_uniqueness_block(
        generation_num=3,
        prior_stems=[PRIOR_Q1],
        chapter="circles",
        question_count=5,
        full_hard=True,
    )
    assert "UNIQUENESS MANDATE" in block
    assert "Q1" in block and "Q5" in block
    assert "(29,21)" in block or "29" in block


def test_validate_accepts_different_skeleton():
    questions = [{"content": NEW_Q1, "slot_number": 1}]
    ok, issues = validate_unique_vs_priors(questions, [PRIOR_Q1])
    assert ok, issues


def test_validate_rejects_same_skeleton():
    questions = [{"content": PRIOR_Q1, "slot_number": 1}]
    ok, issues = validate_unique_vs_priors(questions, [PRIOR_Q1])
    assert not ok
    assert issues


def test_trig_uniqueness_block_avoids_circle_vocabulary():
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    block = build_rag_uniqueness_block(
        generation_num=1,
        prior_stems=[],
        chapter="trigonometry",
        question_count=5,
        full_hard=True,
    )
    low = block.lower()
    assert "concentric" not in low
    assert "tangent–secant" not in low and "tangent-secant" not in low
    pack = get_chapter_rule_pack("trigonometry")
    assert pack.cognitive_blueprint_5[0].lower() in low


def test_quadratic_role_chain_from_rule_pack():
    from app.generation.chapter_prompt_config import uniqueness_role_chain
    from app.generation.chapter_rule_packs import get_chapter_rule_pack

    chain = uniqueness_role_chain("quadratic", full_hard=False, ui_difficulty="hard")
    assert "discriminant" in chain.lower() or "factorisation" in chain.lower()
    assert "concentric" not in chain.lower()
    assert get_chapter_rule_pack("quadratic").cognitive_blueprint_5[0].lower() in chain.lower()


def test_label_rotation_changes_with_generation_num():
    r1 = pick_label_rotation(1, [])
    r2 = pick_label_rotation(2, [])
    assert r1["q2_ext"] != r2["q2_ext"] or r1["fusion_ext"] != r2["fusion_ext"]
