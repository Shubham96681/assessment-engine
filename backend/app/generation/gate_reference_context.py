"""Format GATE reference exemplars for RAG context and prompts."""
from __future__ import annotations

from typing import Any, Dict, List


def format_gate_exemplar_block(
    exemplars: List[Dict[str, Any]],
    *,
    locked_chapter: str,
) -> str:
    if not exemplars:
        return ""
    lines = [
        "\nGATE EXAM REFERENCE (match depth and compression — do NOT copy stems):",
        f"- Chapter/topic: {locked_chapter} | Tier: GATE MA / postgraduate aptitude",
        "- Multi-step reasoning, exact values, (i)(ii) sub-parts where appropriate.",
        "- Write NEW questions with different numbers and proof routes.",
        "",
    ]
    for i, ex in enumerate(exemplars[:6], 1):
        stem = (ex.get("content") or "")[:300]
        yr = ex.get("gate_year") or ""
        sub = ex.get("gate_subject") or "MA"
        src = ex.get("source_file") or ""
        lines.append(f"{i}. {stem}  (GATE {yr} {sub}; ref: {src})")
    lines.append("")
    return "\n".join(lines)


async def enrich_context_with_gate_reference(
    context: str,
    *,
    query: str,
    locked_chapter: str,
) -> str:
    from app.core.config import settings
    from app.generation.gate_reference_retriever import retrieve_gate_exemplars

    if not settings.ENABLE_GATE_REFERENCE or not locked_chapter or locked_chapter == "generic":
        return context
    exemplars = await retrieve_gate_exemplars(
        query=query,
        locked_chapter=locked_chapter,
    )
    block = format_gate_exemplar_block(exemplars, locked_chapter=locked_chapter)
    if not block:
        return context
    return (context.strip() + "\n\n" + block.strip()).strip()


async def enrich_context_with_exam_references(
    context: str,
    *,
    query: str,
    locked_chapter: str,
    class_level: str = "",
    exam_track: str = "board",
    use_gate: bool = True,
) -> str:
    """CBSE + GATE exemplars when indexed."""
    from app.core.config import settings
    from app.generation.cbse_reference_context import enrich_context_with_cbse_reference

    out = await enrich_context_with_cbse_reference(
        context,
        query=query,
        locked_chapter=locked_chapter,
        class_level=class_level,
    )
    track = (exam_track or "").lower()
    if use_gate and (
        track in ("gate", "jee_mains", "jee_advanced", "jee", "olympiad")
        or settings.ENABLE_GATE_REFERENCE_FOR_BOARD
    ):
        out = await enrich_context_with_gate_reference(
            out,
            query=query,
            locked_chapter=locked_chapter,
        )
    elif use_gate:
        from app.generation.gate_reference_ingest import load_gate_reference_manifest

        man = load_gate_reference_manifest()
        if (man.get("chapters") or {}).get(locked_chapter, 0) > 0:
            out = await enrich_context_with_gate_reference(
                out,
                query=query,
                locked_chapter=locked_chapter,
            )
    return out
