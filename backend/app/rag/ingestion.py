"""
PDF Ingestion Pipeline — RAG Document Processing
Handles: PDF parsing, chunking, embedding, vector store upsert
"""
import asyncio
import os
import uuid
import hashlib
import logging
from typing import List, Dict, Any, Tuple

import fitz  # PyMuPDF

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.core.vector_store import qdrant_client, PointStruct
from app.rag.embeddings import embed_texts
from app.rag.chunk_metadata import label_chunk_payload
from app.rag.structured_chunker import chunk_document_pages

logger = logging.getLogger(__name__)


def _extract_text_sync(
    file_path: str,
    page_start: int | None,
    page_end: int | None,
) -> Tuple[List[Dict], int]:
    """CPU-bound PDF parse — must run in a thread pool, not on the asyncio loop."""
    pages_text = []
    doc = fitz.open(file_path)
    total_pages = len(doc)

    start = max(0, (page_start or 1) - 1)
    end = total_pages
    if page_end is not None:
        end = min(total_pages, page_end)
    if settings.MAX_INGEST_PAGES > 0:
        end = min(end, start + settings.MAX_INGEST_PAGES)

    for page_num in range(start, end):
        page = doc[page_num]
        text = page.get_text("text").strip()

        # OCR is very slow — off by default
        if settings.ENABLE_INGEST_OCR and len(text) < 50:
            try:
                import pytesseract
                from PIL import Image
                import io

                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                logger.warning(f"OCR skipped page {page_num + 1}: {e}")

        if text:
            pages_text.append({"page_num": page_num + 1, "text": text})

    doc.close()
    return pages_text, total_pages


class PDFIngestionPipeline:
    """Full pipeline: PDF → Text → Chunks → Embeddings → Qdrant"""

    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.MAX_CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    async def process(
        self,
        file_path: str,
        document_id: str,
        user_id: str,
        metadata: Dict[str, Any] = None,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        logger.info(f"📄 Starting ingestion for document {document_id}")

        pages_text, total_pages = await asyncio.to_thread(
            _extract_text_sync, file_path, page_start, page_end
        )
        logger.info(f"   Extracted {len(pages_text)} pages (file has {total_pages} pages)")

        chunks = await asyncio.to_thread(
            self._create_chunks, pages_text, document_id, user_id, metadata
        )
        logger.info(f"   Created {len(chunks)} chunks")

        if not chunks:
            return {"total_pages": total_pages, "total_chunks": 0, "status": "ready"}

        embeddings: List[List[float]] = []
        texts = [c["text"] for c in chunks]
        batch = settings.INGEST_EMBED_BATCH_SIZE
        for i in range(0, len(texts), batch):
            batch_emb = await embed_texts(texts[i : i + batch])
            embeddings.extend(batch_emb)
            await asyncio.sleep(0)  # yield so /documents API can respond

        logger.info(f"   Generated {len(embeddings)} embeddings")

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point_id = str(uuid.uuid4())
            chunk["qdrant_id"] = point_id
            points.append(
                PointStruct(id=point_id, vector=embedding, payload=chunk)
            )

        batch_size = 100
        for i in range(0, len(points), batch_size):
            await qdrant_client.upsert(
                collection_name=settings.QDRANT_COLLECTION_DOCUMENTS,
                points=points[i : i + batch_size],
            )
            await asyncio.sleep(0)

        logger.info(f"Ingestion complete: {len(chunks)} chunks")
        return {
            "total_pages": total_pages,
            "total_chunks": len(chunks),
            "status": "ready",
        }

    def _create_chunks(
        self,
        pages_text: List[Dict],
        document_id: str,
        user_id: str,
        metadata: Dict,
    ) -> List[Dict]:
        filename = metadata.get("filename", "") or metadata.get("original_filename", "")
        subject = metadata.get("subject", "")

        if settings.ENABLE_STRUCTURED_CHUNKING:
            structured = chunk_document_pages(
                pages_text,
                document_id=document_id,
                filename=filename,
            )
            if structured:
                all_chunks = []
                for sc in structured:
                    row = {
                        "text": sc.text,
                        "document_id": document_id,
                        "user_id": user_id,
                        "page_num": sc.page_num,
                        "chunk_index": sc.chunk_index,
                        "chunk_hash": hashlib.sha256(sc.text.encode()).hexdigest(),
                        "chunk_id": sc.chunk_id,
                        "section_type": sc.section_type,
                        "section_label": sc.section_label,
                        "exercise_id": sc.exercise_id,
                        "subject": subject,
                        "class_level": metadata.get("class_level", ""),
                        "char_count": len(sc.text),
                    }
                    all_chunks.append(
                        label_chunk_payload(row, filename=filename, subject=subject)
                    )
                return all_chunks

        all_chunks = []
        for page_info in pages_text:
            if not page_info["text"]:
                continue
            for idx, chunk_text in enumerate(
                self.splitter.split_text(page_info["text"])
            ):
                row = {
                    "text": chunk_text,
                    "document_id": document_id,
                    "user_id": user_id,
                    "page_num": page_info["page_num"],
                    "chunk_index": idx,
                    "chunk_hash": hashlib.sha256(chunk_text.encode()).hexdigest(),
                    "subject": subject,
                    "class_level": metadata.get("class_level", ""),
                    "char_count": len(chunk_text),
                    "section_type": "paragraph",
                }
                all_chunks.append(
                    label_chunk_payload(row, filename=filename, subject=subject)
                )
        return all_chunks
