"""LLM provider connectivity — quick Groq/Gemini/OpenAI probe."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm", tags=["LLM Health"])


async def _probe_groq() -> dict:
    if not settings.GROQ_API_KEY:
        return {"configured": False, "status": "skipped", "error": "GROQ_API_KEY not set"}
    client = AsyncOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    try:
        r = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": "Reply: OK"}],
                max_tokens=8,
                temperature=0,
            ),
            timeout=15.0,
        )
        text = (r.choices[0].message.content or "").strip()
        return {
            "configured": True,
            "status": "ok",
            "model": settings.GROQ_MODEL,
            "sample": text[:40],
        }
    except asyncio.TimeoutError:
        return {"configured": True, "status": "failed", "error": "timeout (15s)"}
    except Exception as e:
        logger.warning("Groq health probe failed: %s", e)
        return {
            "configured": True,
            "status": "failed",
            "model": settings.GROQ_MODEL,
            "error": str(e)[:300],
        }


@router.get("/health")
async def llm_health():
    """Check whether cloud LLMs are configured and Groq responds."""
    groq = await _probe_groq()
    working = groq.get("status") == "ok"
    return {
        "primary_llm": settings.PRIMARY_LLM,
        "fast_llm": settings.FAST_LLM,
        "rag_file_agent_enabled": settings.RAG_FILE_AGENT_ENABLED,
        "rag_file_agent_only": settings.RAG_FILE_AGENT_ONLY,
        "has_cloud_llm": settings.has_cloud_llm(),
        "groq": groq,
        "gemini_configured": bool(settings.GOOGLE_GEMINI_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "generation_mode": (
            "rag_file_agent"
            if settings.RAG_FILE_AGENT_ENABLED
            else "cloud_llm"
            if settings.has_cloud_llm()
            else "none"
        ),
        "ok": working or settings.RAG_FILE_AGENT_ENABLED,
    }
