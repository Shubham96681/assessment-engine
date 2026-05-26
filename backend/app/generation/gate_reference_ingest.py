"""
Ingest GATE_QuestionPapers/**/*.pdf into gate_reference vector index.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.vector_store import PointStruct, qdrant_client
from app.generation.chapter_concept_classifier import classify_stem_chapter
from app.generation.gate_question_extract import (
    extract_stems_from_gate_pdf_text,
    paper_role_from_path,
    parse_gate_subject,
    parse_gate_year,
    should_index_pdf,
)

logger = logging.getLogger(__name__)


def _resolve_gate_root() -> Path:
    root = Path(settings.GATE_REFERENCE_ROOT or settings.GATE_BENCHMARK_ROOT)
    if not root.is_absolute():
        backend = Path(__file__).resolve().parents[2]
        root = (backend.parent / root).resolve()
    return root


def _manifest_path() -> Path:
    p = Path(settings.GATE_REFERENCE_CACHE_PATH)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[2] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _stems_from_pdf(pdf_path: Path, root: Path) -> List[Dict[str, Any]]:
    import fitz

    rel = (
        str(pdf_path.relative_to(root))
        if pdf_path.is_relative_to(root)
        else pdf_path.name
    )
    if not should_index_pdf(rel):
        return []
    doc = fitz.open(str(pdf_path))
    text = "\n".join(page.get_text("text") for page in doc)
    doc.close()
    rows: List[Dict[str, Any]] = []
    for stem in extract_stems_from_gate_pdf_text(text, source_file=rel):
        content = (stem.get("content") or "").strip()
        if len(content.split()) < 8:
            continue
        chapter, conf, _ = classify_stem_chapter(content)
        if chapter == "generic" or conf < settings.GATE_REFERENCE_MIN_CHAPTER_CONF:
            continue
        rows.append(
            {
                **stem,
                "content": content,
                "locked_chapter": chapter,
                "chapter_confidence": round(conf, 3),
                "gate_year": parse_gate_year(rel),
                "gate_subject": parse_gate_subject(rel),
                "paper_role": paper_role_from_path(rel),
                "chunk_type": "gate_question_stem",
            }
        )
    return rows


async def build_gate_reference_index(*, force: bool = False) -> Dict[str, Any]:
    if not settings.ENABLE_GATE_REFERENCE:
        return {"status": "disabled"}

    root = _resolve_gate_root()
    pdfs = sorted(set(root.rglob("*.pdf")) | set(root.rglob("*.PDF")))
    index_pdfs = [p for p in pdfs if should_index_pdf(str(p))]
    if not index_pdfs:
        logger.warning("GATE reference: no question/solution PDFs under %s", root)
        return {"status": "no_pdfs", "pdf_count": 0}

    manifest_path = _manifest_path()
    newest_pdf = max((p.stat().st_mtime for p in index_pdfs), default=0)
    if manifest_path.exists() and not force:
        try:
            old = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                old.get("stem_count", 0) > 0
                and manifest_path.stat().st_mtime >= newest_pdf
                and time.time() - old.get("built_at", 0)
                < settings.GATE_BENCHMARK_MAX_AGE_HOURS * 3600
            ):
                return {**old, "status": "cached"}
        except Exception:
            pass

    from app.rag.embeddings import embed_texts

    all_rows: List[Dict[str, Any]] = []
    for pdf in index_pdfs:
        try:
            all_rows.extend(_stems_from_pdf(pdf, root))
        except Exception as exc:
            logger.warning("GATE reference skip %s: %s", pdf.name, exc)

    if not all_rows:
        return {"status": "no_stems", "pdf_count": len(index_pdfs)}

    collection = settings.QDRANT_COLLECTION_GATE_REFERENCE
    if settings.VECTOR_STORE_BACKEND.lower() != "qdrant":
        import shutil
        from app.core.faiss_store import faiss_client

        col_dir = Path(settings.FAISS_DATA_PATH) / collection
        if col_dir.exists():
            shutil.rmtree(col_dir)
        faiss_client._collections.pop(collection, None)

    texts = [r["content"] for r in all_rows]
    embeddings: List[List[float]] = []
    batch = settings.INGEST_EMBED_BATCH_SIZE
    for i in range(0, len(texts), batch):
        embeddings.extend(await embed_texts(texts[i : i + batch]))

    points: List[PointStruct] = []
    by_chapter: Dict[str, int] = {}
    for row, emb in zip(all_rows, embeddings):
        key = f"{row['source_file']}|{row.get('slot_number', 0)}|{row['content'][:160]}"
        pid = str(uuid.uuid5(uuid.NAMESPACE_URL, key))
        ch = row["locked_chapter"]
        by_chapter[ch] = by_chapter.get(ch, 0) + 1
        payload = {
            "text": row["content"],
            "content": row["content"],
            "locked_chapter": ch,
            "marks": row.get("marks"),
            "gate_year": row.get("gate_year", ""),
            "gate_subject": row.get("gate_subject", ""),
            "paper_role": row.get("paper_role", ""),
            "source_file": row.get("source_file", ""),
            "slot_number": row.get("slot_number", 0),
            "chunk_type": "gate_question_stem",
            "document_id": "gate_reference",
            "exam_tier": "gate",
        }
        points.append(PointStruct(id=pid, vector=emb, payload=payload))

    await qdrant_client.upsert(collection_name=collection, points=points)
    manifest = {
        "status": "built",
        "built_at": time.time(),
        "pdf_count": len(index_pdfs),
        "stem_count": len(all_rows),
        "chapters": by_chapter,
        "source_root": str(root),
        "newest_pdf_mtime": newest_pdf,
        "collection": collection,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(
        "GATE reference index: %d PDFs, %d stems, chapters=%s",
        len(index_pdfs),
        len(all_rows),
        list(by_chapter.keys())[:12],
    )
    return manifest


def load_gate_reference_manifest() -> Dict[str, Any]:
    p = _manifest_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
