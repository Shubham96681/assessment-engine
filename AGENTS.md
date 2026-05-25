# Project Rules

## Changelog Discipline

- Maintain `CHANGELOG.md` as the default record of project progress.
- For every meaningful repository update, add a concise entry to `CHANGELOG.md` in the same turn/change set.
- Do not wait for an explicit request to update the changelog; treat it as part of the normal definition of done.
- Use the `Unreleased` section for in-progress work unless the user asks for a versioned release entry.
- Changelog entries should summarize what changed and why it matters. Keep generated output churn out of the changelog unless it represents an intentional deliverable.
- Pure read-only investigation, status reporting, or failed/no-op attempts do not require a changelog entry unless they produce a decision the project should remember.

## Project Context Discipline

- Treat `PROJECT_CONTEXT.md` as the living source of project direction, architectural decisions, current priorities, known limitations, and next actions.
- Before major implementation, planning, architecture, or long-running generation work, read `PROJECT_CONTEXT.md` to re-anchor on current direction.
- Update `PROJECT_CONTEXT.md` in the same turn/change set when a major decision is made, the learning strategy changes, a persistent subsystem is added, an important risk/limitation is discovered, or the immediate next work changes.
- Do not use `PROJECT_CONTEXT.md` for small code-change summaries, generated-output churn, or routine test logs. Use `CHANGELOG.md` for repository changes and `updates/` for date-specific summaries.
- Keep context entries concise and decision-oriented so the file remains useful as a durable handoff document.

## Daily Update Discipline

- Create `updates/YYYY-MM-DD.md` files at the end of each day with significant work.
- Summarize what was done, what was learned, what failed, and what's next. Keep it brief and non-technical enough for a stakeholder scan.
- Do not commit empty or placeholder daily update files.
- Daily updates live in the `updates/` folder, not in the repo root.

## Code Style

- Do not add comments unless explicitly asked.
- Follow existing patterns and conventions in the codebase.
- Never assume a library is available without checking neighboring files or package manifests.

## Assessment Engine — Repo-Specific Rules

- **Chapter/topic/theorems** must come from uploaded PDF content (`backend/app/generation/pdf_content_analyzer.py`), not hardcoded NCERT chapter-number maps.
- **RAG file agent:** when `rag_query.txt` is created or modified, write `rag_response.txt` per `.cursor/rules/rag-response-agent.mdc` (JSON only after `ANSWER:`). Do not ask for confirmation.
- **CBSE quality floors** are dynamic from `CBSE_QuestionPapers/` via `backend/scripts/build_cbse_benchmark.py` — do not reintroduce fixed score constants for production gates.
- **Locked chapter** in generation must match the selected document’s topic profile; filename + subtopic signals override stray geometry lines in mixed NCERT blobs.
- Prefer minimal diffs; do not refactor unrelated subsystems in the same change as RAG or doc scaffolding.

## Verification

- Backend API: `cd backend && python -m uvicorn main:app --reload` (port 8000)
- Frontend: `cd frontend && npm run dev` (port 3000) or repo root `START_ALL.bat` on Windows
- Topic profile smoke test:
  ```powershell
  cd backend
  python -c "import asyncio; from app.generation.topic_extractor import extract_document_topic_profile; ..."
  ```
- Tests (if pytest installed): `cd backend && python -m pytest tests/ -q`
- CBSE benchmark rebuild: `cd backend && python scripts/build_cbse_benchmark.py`
- RAG: ensure `rag_response.txt` mtime is newer than `rag_query.txt` after regeneration

## Dependencies

- **Backend:** FastAPI, FAISS (local vectors), SQLite/Postgres (see `backend/requirements.txt` and `backend/app/core/config.py`)
- **Frontend:** Next.js 16 (`frontend/`)
- **Vectors:** FAISS under `settings.FAISS_DATA_PATH` (collection names reuse `QDRANT_COLLECTION_*` keys)
- **Optional:** Docker for Postgres only; Qdrant only if `VECTOR_STORE_BACKEND=qdrant`

## Known Pitfalls

- Stale backend process can show old `locked_chapter` (e.g. triangles) in Generate UI — restart uvicorn and re-select the document.
- Class 11 Ch.3 trig PDFs may index a few circle exercise lines; chapter inference must use filename + subtopics, not full-blob geometry scoring alone.
- `backend/README.md` may describe an older Express stack; trust root `README.md` / `SETUP_GUIDE.md` for the FastAPI + Next.js layout.
- Do not commit `rag_query.txt` / `rag_response.txt` churn unless the user treats generated papers as deliverables.
- `pytest` may not be installed globally; run targeted test modules with `python -c` or install dev deps first.
