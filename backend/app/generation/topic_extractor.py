"""

Extract primary topic, locked chapter, and subtopics from a document's indexed chunks.

All fields are driven by PDF text — not NCERT chapter-number hardcoding.

"""

from __future__ import annotations



import re

from collections import Counter

from typing import Any, Dict, List, Optional



from app.core.config import settings

from app.core.vector_store import qdrant_client, Filter, FieldCondition, MatchValue

from app.generation.chapter_concept_classifier import (

    refine_locked_chapter,

    _score_text_for_chapters,

)

from app.generation.pdf_content_analyzer import (

    extract_primary_topic_from_pdf,

    extract_subtopics_from_pdf,

    extract_theorems_from_pdf,

    infer_locked_chapter_from_pdf,

)

from app.generation.theorem_coverage import enrich_required_theorems, infer_required_theorems



_KEY_PHRASE_RE = re.compile(

    r"(?i)\b(?:prove|show\s+that|find|calculate|evaluate|solve|derive|"

    r"discriminant|tangent|parallelogram|rhombus|trapezium|"

    r"quadratic\s+equation|nature\s+of\s+roots|midpoint\s+theorem|"

    r"cyclic\s+quadrilateral|similar\s+triangles|arithmetic\s+progression|"

    r"\bsin\s|\bcos\s|\btan\s|\bradian\b)"

)





def _clean_label(text: str, max_len: int = 72) -> str:

    t = re.sub(r"\s+", " ", (text or "").strip())

    t = re.sub(r"[^\w\s\-–:().,²³√πθ]", "", t)

    return t[:max_len].strip(" .-")





async def scroll_document_text(

    document_id: str,

    *,

    limit: int = 120,

) -> List[Dict[str, Any]]:

    """Load chunk payloads for one document from Qdrant."""

    chunks: List[Dict[str, Any]] = []

    try:

        results, _ = await qdrant_client.scroll(

            collection_name=settings.QDRANT_COLLECTION_DOCUMENTS,

            scroll_filter=Filter(

                must=[

                    FieldCondition(

                        key="document_id", match=MatchValue(value=document_id)

                    )

                ]

            ),

            limit=limit,

            with_payload=True,

        )

        for point in results or []:

            payload = point.payload or {}

            text = (payload.get("text") or "").strip()

            if not text:

                continue

            chunks.append(

                {

                    "text": text,

                    "page_num": payload.get("page_num"),

                    "qdrant_id": str(point.id),

                }

            )

    except Exception:

        return []

    return chunks





def _extract_concept_phrases(blob: str, limit: int = 16) -> List[str]:

    counter: Counter[str] = Counter()

    for m in _KEY_PHRASE_RE.finditer(blob):

        counter[m.group(0).lower()] += 1

    return [p.title() for p, _ in counter.most_common(limit)]





def build_topic_profile(

    *,

    document_id: str,

    filename: str = "",

    topic_focus: str = "",

    subject: str = "",

    class_level: str = "",

    chunks: Optional[List[Dict[str, Any]]] = None,

) -> Dict[str, Any]:

    """Build topic profile from indexed PDF chunks."""

    blob = "\n".join((c.get("text") or "")[:800] for c in (chunks or [])[:80])

    subtopics = extract_subtopics_from_pdf(blob)
    seen = {s.lower() for s in subtopics}

    locked_chapter, source, confidence = infer_locked_chapter_from_pdf(
        blob=blob,
        filename=filename,
        topic_focus=topic_focus,
        subtopics=subtopics,
    )



    def _add(label: str) -> None:

        label = _clean_label(label)

        key = label.lower()

        if len(label) < 5 or key in seen:

            return

        seen.add(key)

        subtopics.append(label)



    if topic_focus:

        _add(topic_focus)

    for phrase in _extract_concept_phrases(blob):

        _add(phrase)



    locked_chapter, source, confidence = refine_locked_chapter(
        locked_chapter,
        source,
        confidence,
        filename=filename,
        context=blob,
        subtopics=subtopics,
    )

    # Re-lock after subtopics + filename (NCERT ch.3 mixes a few circle lines with trig)
    locked_chapter, source, confidence = infer_locked_chapter_from_pdf(
        blob=blob,
        filename=filename,
        topic_focus=topic_focus,
        subtopics=subtopics,
    )

    primary_topic = extract_primary_topic_from_pdf(

        blob=blob,

        filename=filename,

        topic_focus=topic_focus,

    )

    if not primary_topic:

        primary_topic = _clean_label(

            locked_chapter.replace("_", " ").title(), 80

        )



    pdf_theorems = extract_theorems_from_pdf(blob, subtopics)

    if pdf_theorems:

        required_theorems = enrich_required_theorems(pdf_theorems)

    else:

        required_theorems = infer_required_theorems(

            locked_chapter,

            blob,

            subtopics,

        )



    chapter_scores = _score_text_for_chapters(blob)

    secondary_chapters = [

        ch

        for ch, sc in sorted(chapter_scores.items(), key=lambda x: -x[1])

        if ch != locked_chapter and sc >= 1.0

    ][:4]



    return {

        "document_id": document_id,

        "filename": filename,

        "primary_topic": _clean_label(primary_topic, 80),

        "index_status": "indexed" if chunks else "no_chunks_in_vector_store",

        "locked_chapter": locked_chapter,

        "locked_chapter_source": source,

        "confidence": round(confidence, 3),

        "subject": subject or "Mathematics",

        "class_level": class_level or "",

        "subtopics": subtopics[:20],

        "secondary_chapters": secondary_chapters,

        "required_theorems": required_theorems,

        "chunk_count_used": len(chunks or []),

        "headings_found": len(

            [s for s in subtopics if re.search(r"exercise|theorem|chapter", s, re.I)]

        ),

    }





async def extract_document_topic_profile(

    document_id: str,

    *,

    filename: str = "",

    topic_focus: str = "",

    subject: str = "",

    class_level: str = "",

) -> Dict[str, Any]:

    chunks = await scroll_document_text(document_id)

    profile = build_topic_profile(

        document_id=document_id,

        filename=filename,

        topic_focus=topic_focus,

        subject=subject,

        class_level=class_level,

        chunks=chunks,

    )

    profile["sample_pages"] = sorted(

        {c["page_num"] for c in chunks if c.get("page_num") is not None}

    )[:12]

    return profile


