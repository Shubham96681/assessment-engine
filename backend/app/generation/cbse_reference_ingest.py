"""
Ingest CBSE_QuestionPapers/**/*.pdf into the cbse_reference vector index.

Each question stem is embedded with metadata: locked_chapter, class_level, marks,
paper_type, source_file — so generation can retrieve board-level exemplars per topic.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.vector_store import PointStruct, qdrant_client
from app.generation.cbse_question_extract import (
    class_to_band,
    extract_stems_from_pdf_text,
    parse_class_from_path,
)
from app.generation.chapter_concept_classifier import classify_stem_chapter

logger = logging.getLogger(__name__)

_CHAPTER_HEAD = re.compile(
    r"(?im)(?:^|\n)\s*(?:chapter|unit)\s*(\d{1,2})[\s:\.\-]+([^\n]{4,90})",
)
_PAPER_TYPE = re.compile(
    r"(?i)(sqp|sample|marking\s*scheme|ms_|cbe|teacher|competency|basic|standard)",
)


def _resolve_cbse_root() -> Path:
    root = Path(settings.CBSE_BENCHMARK_ROOT)
    if not root.is_absolute():
        for base in (
            Path.cwd(),
            Path(__file__).resolve().parents[3],
            Path(__file__).resolve().parents[2],
        ):
            candidate = (base / root).resolve()
            if candidate.exists():
                return candidate
    return root.resolve()


def _manifest_path() -> Path:
    p = Path(settings.CBSE_REFERENCE_CACHE_PATH)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[2] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _paper_type_from_path(rel: str) -> str:
    low = rel.lower()
    if "marking" in low or "_ms" in low or "ms_" in low:
        return "marking_scheme"
    if "sqp" in low or "sample" in low:
        return "sample_paper"
    if "cbe" in low or "competency" in low:
        return "cbe"
    if "teacher" in low:
        return "teacher_resource"
    return "board"


def _chapter_from_heading(heading: str) -> Tuple[str, float]:
    from app.generation.chapter_concept_classifier import classify_stem_chapter

    return classify_stem_chapter(heading)


def _split_text_by_chapter_sections(text: str) -> List[Tuple[str, str]]:
    """Return (chapter_key, text_block) segments from CBE / teacher manuals."""
    matches = list(_CHAPTER_HEAD.finditer(text))
    if len(matches) < 2:
        return []
    segments: List[Tuple[str, str]] = []
    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        ch, conf, _ = _chapter_from_heading(heading)
        if ch == "generic" or conf < settings.CBSE_REFERENCE_MIN_CHAPTER_CONF:
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        if len(block) > 200:
            segments.append((ch, block))
    return segments


def _stems_from_pdf(
    pdf_path: Path,
    root: Path,
) -> List[Dict[str, Any]]:
    import fitz

    rel = str(pdf_path.relative_to(root)) if pdf_path.is_relative_to(root) else pdf_path.name
    class_level = parse_class_from_path(rel)
    band = class_to_band(class_level)
    paper_type = _paper_type_from_path(rel)

    doc = fitz.open(str(pdf_path))
    text = "\n".join(page.get_text("text") for page in doc)
    doc.close()

    rows: List[Dict[str, Any]] = []
    sections = _split_text_by_chapter_sections(text)
    if sections:
        for chapter_key, block in sections:
            for stem in extract_stems_from_pdf_text(block, source_file=rel):
                rows.append(
                    _enrich_stem(
                        stem,
                        rel=rel,
                        class_level=class_level,
                        band=band,
                        paper_type=paper_type,
                        forced_chapter=chapter_key,
                    )
                )
    else:
        for stem in extract_stems_from_pdf_text(text, source_file=rel):
            rows.append(
                _enrich_stem(
                    stem,
                    rel=rel,
                    class_level=class_level,
                    band=band,
                    paper_type=paper_type,
                )
            )
    return rows


def _enrich_stem(
    stem: Dict[str, Any],
    *,
    rel: str,
    class_level: str,
    band: str,
    paper_type: str,
    forced_chapter: str = "",
) -> Optional[Dict[str, Any]]:
    content = (stem.get("content") or "").strip()
    if len(content.split()) < 6:
        return None
    if forced_chapter:
        chapter = forced_chapter
        conf = 1.0
    else:
        chapter, conf, _ = classify_stem_chapter(content)
    if chapter == "generic" or conf < settings.CBSE_REFERENCE_MIN_CHAPTER_CONF:
        return None
    return {
        **stem,
        "content": content,
        "locked_chapter": chapter,
        "chapter_confidence": round(conf, 3),
        "class_level": class_level,
        "class_band": band,
        "paper_type": paper_type,
        "source_file": rel,
        "chunk_type": "cbse_question_stem",
    }


async def build_cbse_reference_index(*, force: bool = False) -> Dict[str, Any]:
    """Scan PDFs, embed stems, upsert into cbse_reference collection."""
    if not settings.ENABLE_CBSE_REFERENCE:
        return {"status": "disabled"}

    root = _resolve_cbse_root()
    pdfs = sorted(set(root.rglob("*.pdf")) | set(root.rglob("*.PDF")))
    if not pdfs:
        logger.warning("CBSE reference: no PDFs under %s", root)
        return {"status": "no_pdfs", "pdf_count": 0}

    manifest_path = _manifest_path()
    newest_pdf = max((p.stat().st_mtime for p in pdfs), default=0)
    old: Dict[str, Any] = {}
    stale = force or not manifest_path.exists()
    if manifest_path.exists() and not force:
        try:
            old = json.loads(manifest_path.read_text(encoding="utf-8"))
            cache_age_ok = (
                time.time() - old.get("built_at", 0)
                < settings.CBSE_BENCHMARK_MAX_AGE_HOURS * 3600
            )
            pdf_ok = not newest_pdf or manifest_path.stat().st_mtime >= newest_pdf
            if cache_age_ok and pdf_ok and old.get("stem_count", 0) > 0:
                return {**old, "status": "cached"}
            if newest_pdf > old.get("newest_pdf_mtime", 0):
                stale = True
        except Exception:
            stale = True

    from app.rag.embeddings import embed_texts

    all_rows: List[Dict[str, Any]] = []
    for pdf in pdfs:
        try:
            rows = _stems_from_pdf(pdf, root)
            all_rows.extend(r for r in rows if r)
        except Exception as exc:
            logger.warning("CBSE reference skip %s: %s", pdf.name, exc)

    if not all_rows:
        logger.warning("CBSE reference: no classified stems from %d PDFs", len(pdfs))
        return {"status": "no_stems", "pdf_count": len(pdfs)}

    collection = settings.QDRANT_COLLECTION_CBSE_REFERENCE
    # Full rebuild — drop stale FAISS collection so ids do not accumulate
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
            "class_level": row.get("class_level", ""),
            "class_band": row.get("class_band", ""),
            "marks": row.get("marks"),
            "paper_type": row.get("paper_type", ""),
            "source_file": row.get("source_file", ""),
            "slot_number": row.get("slot_number", 0),
            "chunk_type": row.get("chunk_type", "cbse_question_stem"),
            "document_id": "cbse_reference",
        }
        points.append(PointStruct(id=pid, vector=emb, payload=payload))

    # Replace collection: clear via re-upsert all (FAISS overwrites by id; new ids = full rebuild)
    # For incremental we'd need delete — full rebuild is simpler for local FAISS.
    await qdrant_client.upsert(collection_name=collection, points=points)

    manifest = {
        "status": "built",
        "built_at": time.time(),
        "pdf_count": len(pdfs),
        "stem_count": len(all_rows),
        "chapters": by_chapter,
        "source_root": str(root),
        "newest_pdf_mtime": newest_pdf,
        "collection": collection,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(
        "CBSE reference index: %d PDFs, %d stems, chapters=%s",
        len(pdfs),
        len(all_rows),
        list(by_chapter.keys())[:12],
    )
    return manifest


def load_cbse_reference_manifest() -> Dict[str, Any]:
    p = _manifest_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
