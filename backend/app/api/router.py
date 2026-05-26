"""Simplified API Router — No Auth"""
from fastapi import APIRouter
from app.api import (
    documents,
    assessments,
    feedback,
    analytics,
    figures,
    rag,
    paper_templates,
    cbse,
    chapters,
    llm_health,
)

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(figures.router, prefix="/figures", tags=["Figures"])
api_router.include_router(rag.router)
api_router.include_router(paper_templates.router, tags=["Paper Templates"])
api_router.include_router(cbse.router)
api_router.include_router(chapters.router)
api_router.include_router(llm_health.router)
