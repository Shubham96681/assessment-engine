"""
Format CBSE reference exemplars for RAG context and compiler prompts.
"""
from __future__ import annotations

from typing import Any, Dict, List


def format_cbse_exemplar_block(
    exemplars: List[Dict[str, Any]],
    *,
    locked_chapter: str,
    class_level: str = "",
) -> str:
    if not exemplars:
        return ""
    lines = [
        "\nCBSE BOARD REFERENCE (match compression, marks, and reasoning depth — do NOT copy stems):",
        f"- Chapter: {locked_chapter} | Class: {class_level or 'any'}",
        "- Replicate SQP/CBE item style: direct givens, exam verbs, mark-appropriate steps.",
        "- Write NEW questions with different numbers, labels, and proof routes.",
        "",
    ]
    for i, ex in enumerate(exemplars[:8], 1):
        stem = (ex.get("content") or "")[:280]
        marks = ex.get("marks")
        src = ex.get("source_file") or ""
        mark_s = f" [{marks:g} marks]" if marks else ""
        lines.append(f"{i}. {stem}{mark_s}  (ref: {src})")
    lines.append("")
    return "\n".join(lines)


async def enrich_context_with_cbse_reference(
    context: str,
    *,
    query: str,
    locked_chapter: str,
    class_level: str = "",
) -> str:
    from app.core.config import settings
    from app.generation.cbse_reference_retriever import retrieve_cbse_exemplars

    if not settings.ENABLE_CBSE_REFERENCE or not locked_chapter or locked_chapter == "generic":
        return context

    exemplars = await retrieve_cbse_exemplars(
        query=query,
        locked_chapter=locked_chapter,
        class_level=class_level,
    )
    block = format_cbse_exemplar_block(
        exemplars,
        locked_chapter=locked_chapter,
        class_level=class_level,
    )
    if not block:
        return context
    return (context.strip() + "\n\n" + block.strip()).strip()


def cbse_reference_prompt_hints(
    exemplars: List[Dict[str, Any]],
    class_level: str = "",
) -> str:
    if not exemplars:
        return ""
    n = len(exemplars)
    avg_words = sum(len((e.get("content") or "").split()) for e in exemplars) / max(n, 1)
    return (
        f"CBSE reference pool: {n} board stems indexed; target stem length ~{avg_words:.0f} words; "
        f"class {class_level or 'mixed'}; match official SQP compression and mark weighting."
    )
