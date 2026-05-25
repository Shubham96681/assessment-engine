"""CBSE question-paper corpus — build reference index by chapter/topic."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.core.config import settings

router = APIRouter(prefix="/cbse", tags=["CBSE Reference"])


@router.get("/reference/status")
async def cbse_reference_status():
    from app.generation.cbse_reference_ingest import load_cbse_reference_manifest

    man = load_cbse_reference_manifest()
    return {
        "enabled": settings.ENABLE_CBSE_REFERENCE,
        "stem_count": man.get("stem_count", 0),
        "pdf_count": man.get("pdf_count", 0),
        "chapters": man.get("chapters", {}),
        "status": man.get("status", "not_built"),
        "source_root": man.get("source_root", settings.CBSE_BENCHMARK_ROOT),
    }


@router.post("/reference/build")
async def cbse_reference_build(background_tasks: BackgroundTasks, force: bool = False):
    """Index all CBSE_QuestionPapers PDFs by chapter (async background)."""

    async def _run():
        from app.generation.cbse_reference_ingest import build_cbse_reference_index

        await build_cbse_reference_index(force=force)

    background_tasks.add_task(_run)
    return {"status": "building", "force": force}
