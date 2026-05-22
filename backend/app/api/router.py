"""Simplified API Router — No Auth"""
from fastapi import APIRouter
from app.api import documents, assessments, feedback, analytics, figures

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(figures.router, prefix="/figures", tags=["Figures"])
