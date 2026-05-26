"""Unit circle figure_spec auto-build and render."""
import asyncio

from app.generation.figure_spec_builder import enrich_figure_spec
from app.generation.figures import FigureGenerator


def test_enrich_unit_circle_from_stem():
    stem = (
        "The unit circle shows angle θ = 210° in standard position. "
        "(i) Express 210° as a multiple of π radians."
    )
    spec = enrich_figure_spec(stem, None)
    assert spec.get("type") == "unit_circle"
    assert spec.get("angle_deg") == 210


def test_unit_circle_geometry_stem_not_merged():
    stem = "PQ is tangent at P to a circle with centre O. OP = 5 cm. Find PQ."
    spec = enrich_figure_spec(stem, None)
    assert spec.get("type") != "unit_circle"
    assert any((el.get("shape") or "").lower() == "circle" for el in spec.get("elements", []))


def test_unit_circle_render_produces_url():
    spec = enrich_figure_spec(
        "The unit circle shows θ = 135° in standard position.", None
    )
    gen = FigureGenerator()
    url = asyncio.get_event_loop().run_until_complete(
        gen.generate(spec, spec.get("type", "unit_circle"))
    )
    assert url
    assert "/uploads/figures/" in url
