"""Paper template registry and resolution."""
from app.generation.paper_dependency_graph import build_paper_dependency_plan
from app.generation.paper_templates import (
    resolve_paper_template,
    template_slot_assignments_block,
)
from app.generation.rag_query_builder import build_rag_slot_query


def test_auto_resolves_chained_concentric_for_circles_hard():
    tmpl = resolve_paper_template(
        chapter="circles",
        ui_difficulty="hard",
        question_count=5,
        full_hard=True,
    )
    assert tmpl.id == "chained_concentric"
    assert tmpl.enables_dependency_chain is True


def test_mixed_independent_disables_dependency_chain():
    tmpl = resolve_paper_template(
        override="mixed_independent",
        chapter="circles",
        ui_difficulty="hard",
        question_count=5,
    )
    plan = build_paper_dependency_plan(
        chapter="circles",
        question_count=5,
        slots=[],
        ui_difficulty="hard",
        full_hard=True,
        paper_template_id=tmpl.id,
    )
    assert plan.enabled is False


def test_template_slot_block_uses_roles():
    tmpl = resolve_paper_template(override="mixed_independent", chapter="circles")
    block = template_slot_assignments_block(tmpl, 5, chapter="circles")
    assert "role=anchor" not in block.lower() or "independent" in block
    assert "FORBIDDEN" in block or "standalone" in block.lower()


def test_rag_slot_query_anchor():
    q = build_rag_slot_query("anchor", topic="Circles", chapter="circles")
    assert "shared figure" in q.lower() or "establish" in q.lower()
