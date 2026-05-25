# Project Context

Last updated: 2026-05-25

## Purpose Of This File

This is the living context ledger for the **Assessment Engine**.

Use it to preserve the reasoning behind major decisions, current priorities, implementation direction, known constraints, and next actions. This file is not a changelog and not a daily status report.

Related files:

- `CHANGELOG.md`: what changed in the repository.
- `updates/`: date-specific progress summaries.
- `SETUP_GUIDE.md` / `README.md`: human runbooks.

## Product Direction

Build CBSE-aligned mathematics assessments from uploaded textbook PDFs using RAG, with quality at or above reference CBSE question papers. Teachers select a source document; the system extracts topics, plans theorem coverage from PDF text, generates questions via a file-based RAG agent (Cursor), validates quality, and exports PDFs. No hardcoded chapter tables for production topic lock — content comes from the indexed PDF.

## Current Architectural State

| Area | Role |
|------|------|
| `frontend/` | Next.js UI — document upload, Generate page, topic profile display |
| `backend/app/api/` | FastAPI routes — documents, generation, feedback |
| `backend/app/generation/` | Topic extraction, PDF analyzer, prompt compiler, quality scoring, PDF export |
| `backend/app/rag/` | Hybrid retrieval, structured chunking, rerank |
| `rag_query.txt` / `rag_response.txt` | File-based RAG loop (backend writes query; agent writes JSON response) |
| `CBSE_QuestionPapers/` | Reference corpus for dynamic quality floors |
| `.cursor/rules/rag-response-agent.mdc` | Stem/answer discipline for geometry papers |

Data: Qdrant for chunk vectors; SQLite/Postgres for document metadata.

## Decisions Made

### 1. PDF-first topic and theorem lock

Decision: Primary topic, `locked_chapter`, subtopics, and required theorems are inferred from indexed PDF text and filename signals, with catalog fallbacks only when PDF evidence is thin.

Reasoning: Hardcoded NCERT chapter-number maps mislabeled trigonometry PDFs as triangles when blobs contained mixed exercises. Filename weight and subtopic-first inference fix dominant-domain errors without maintaining per-book tables.

### 2. CBSE benchmark as dynamic quality floor

Decision: Quality gates use statistics built from `CBSE_QuestionPapers/` (`benchmark.json`), not a fixed constant like `0.38`.

Reasoning: Lets the bar rise with the local reference corpus and avoids one-size-fits-all thresholds across classes and chapters.

### 3. RAG file agent for generation

Decision: Production generation can use `rag_query.txt` → `rag_response.txt` with strict JSON and geometry stem rules, rather than only inline LLM calls.

Reasoning: Gives reproducible, reviewable question batches and allows Cursor-side authoring with blueprint and PRIOR QUESTIONS enforcement.

### 4. phyEngine ideas, not replacement pipeline

Decision: Adopt structured chunking, metadata, rerank, and RL-style reward scoring into the existing CBSE geometry generation path; do not replace the chapter-specific prompt/quality stack wholesale.

Reasoning: Preserves investment in circles/trig templates, theorem graphs, and PDF export while improving retrieval and feedback loops.

## Current Limitations

### Mixed content in single NCERT chapters

Some PDFs index both trigonometry and a few circle exercises in one chapter blob. Full-text scoring can favor the wrong domain without filename + subtopic overrides.

Risk: Wrong theorem plan (Pythagoras vs trig identities) and off-chapter generation.

Mitigation: `pdf_trig_density` override, subtopics passed into `infer_locked_chapter_from_pdf`, topic-profile refresh on document select.

### RAG agent dependency

Quality regeneration and full papers depend on a timely `rag_response.txt` with valid JSON and blueprint compliance.

Risk: Backend blocks on slot retry if stems are empty or duplicate prior questions.

Mitigation: `QUALITY REGENERATION` prompts in `rag_query.txt`; workspace rule `rag-response-agent.mdc`.

### CBSE folder optional in git

Benchmark script expects PDFs under `CBSE_QuestionPapers/`; repo may ship README only until the user adds papers locally.

Risk: Fallback quality floors if benchmark not built.

Mitigation: Run `python scripts/build_cbse_benchmark.py` after adding PDFs.

## Immediate Next Work

1. Verify Generate UI shows `trigonometry` for Class 11 Ch.3 PDF after backend restart and document re-select.
2. Keep RAG regeneration responses timely when `rag_query.txt` requests slot fixes (e.g. empty_stem on slot 5).
3. Optionally re-index or backfill chunk `locked_chapter` metadata if retrieval still pulls wrong-domain chunks.

## Context Update Protocol

Update this file when:

- A major architectural decision is made.
- We change direction or strategy.
- A new persistent subsystem is added.
- A major limitation or risk is discovered.
- The immediate next work changes.

Do not use this file for:

- Every small code change.
- Generated output churn.
- Test run logs.
- Daily summaries.

Use `CHANGELOG.md` for repository changes and `updates/` for daily summaries.

## Current One-Line Summary

Assessment Engine generates board-style maths papers from uploaded PDFs via RAG, with PDF-driven chapter lock and CBSE-calibrated quality gates.
