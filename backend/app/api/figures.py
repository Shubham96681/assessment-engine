"""Figures API — on-demand figure generation"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.core.security import get_current_user
from app.models import User
from app.generation.figures import FigureGenerator

router = APIRouter()
generator = FigureGenerator()


class FigureRequest(BaseModel):
    figure_type: str
    spec: Dict[str, Any]


@router.post("/generate")
async def generate_figure(
    req: FigureRequest,
    current_user: User = Depends(get_current_user),
):
    valid_types = [
        "flowchart", "bar_graph", "line_graph", "mind_map",
        "venn_diagram", "table", "labeled_diagram", "process_diagram",
    ]
    if req.figure_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Unknown figure type. Valid: {valid_types}")

    url = await generator.generate(req.spec, req.figure_type)
    if not url:
        raise HTTPException(status_code=500, detail="Figure generation failed")
    return {"figure_url": url, "figure_type": req.figure_type}
