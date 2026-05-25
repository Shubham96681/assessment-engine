"""Q5 fusion — clean GK / feasible secant given Q1 outer radius."""
from app.generation.fusion_q5_values import (
    find_best_fusion_givens,
    fusion_values_are_clean,
    repair_fusion_q5_stem,
)


def test_find_best_for_r29():
    og, gj, gh, gk = find_best_fusion_givens(29)
    assert og > 29
    diff = og * og - 29 * 29
    assert diff % gj == 0
    assert gk == diff // gj
    assert gk > gj
    assert gk - gj <= 58


def test_repair_messy_q5_stem():
    stem = (
        "In the configuration of Question 1, with PA = 15 cm from Question 2. "
        "(i) Find OP. (ii) Hence point G is 32 cm from O; tangent GH at H. "
        "Secant GJK with GJ = 6 cm. Find GK and verify GH^2 = GJ x GK."
    )
    assert not fusion_values_are_clean(29, 32, 6)
    new, ch = repair_fusion_q5_stem(stem, 29)
    assert ch
    assert "GJ = 6" not in new
    assert fusion_values_are_clean(29, *parse_og_gj(new))


def parse_og_gj(stem: str):
    import re

    og = int(re.search(r"point G is (\d+)", stem, re.I).group(1))
    gj = int(re.search(r"GJ = (\d+)", stem, re.I).group(1))
    return og, gj


def test_clean_triple_r24():
    og, gj, gh, gk = find_best_fusion_givens(24)
    assert gh * gh == og * og - 24 * 24
    assert gk == (og * og - 24 * 24) // gj
