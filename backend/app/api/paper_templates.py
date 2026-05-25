"""Paper template and exam pattern metadata for UI / clients."""
from fastapi import APIRouter

from app.core.config import settings
from app.generation.exam_patterns import list_exam_patterns
from app.generation.paper_templates import list_paper_templates

router = APIRouter()


@router.get("/paper-templates")
async def get_paper_templates():
    """List registered paper layouts (chained concentric, mixed independent, …)."""
    return {
        "default": settings.DEFAULT_PAPER_TEMPLATE,
        "templates": list_paper_templates(),
    }


@router.get("/exam-patterns")
async def get_exam_patterns():
    """Exam section metadata (CBSE Class 10, JEE Mains stubs)."""
    return {"patterns": list_exam_patterns()}
