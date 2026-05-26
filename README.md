# Assessment Engine

AI-powered quiz generation from PDF textbooks using RAG (Retrieval-Augmented Generation).

## Quick start

1. Read **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** — complete install, run, and RAG file agent guide.
2. Windows: run **`START_ALL.bat`** from the repo root (Docker + backend + frontend).
3. Open http://localhost:3000

## RAG file agent (no API key)

| File | Role |
|------|------|
| `rag_query.txt` | Written by backend (CONTEXT + QUESTION) |
| `rag_response.txt` | Written by Cursor / you (JSON answers) |

Cursor rules: `.cursor/rules/rag-response-agent.mdc`  
Details: [RAG_FILE_AGENT.md](./RAG_FILE_AGENT.md)

## Stack

- **Frontend:** Next.js 16 → port 3000  
- **Backend:** FastAPI → port 8000  
- **Vectors:** FAISS (local, `backend/data/faiss` — no Docker)  
- **Postgres/SQLite:** metadata + assessments (SQLite default; optional Docker Postgres on **5433**)  

## Docs

| Document | Audience |
|----------|----------|
| [SETUP_GUIDE.md](./SETUP_GUIDE.md) | Humans — full setup on a new device |
| [CBSE_PYQ_REFERENCE.md](./CBSE_PYQ_REFERENCE.md) | CBSE Class 10 Maths Standard paper structure (2023–2025 PYQ) |
| [TEXTBOOK_EXERCISE_REFERENCE.md](./TEXTBOOK_EXERCISE_REFERENCE.md) | RD Sharma / RS Aggarwal exercise depth (multi-step HOTS) |
| [RD_SHARMA_CLASS10_REFERENCE.md](./RD_SHARMA_CLASS10_REFERENCE.md) | Compact exam-style calibration (`RD_Sharma_Class10_Maths.pdf`) |
| [CURSOR_AI_README.md](./CURSOR_AI_README.md) | Cursor Agent — what to do with RAG files |
| [RAG_FILE_AGENT.md](./RAG_FILE_AGENT.md) | Short RAG reference |
| [GATE_QuestionPapers/README.md](./GATE_QuestionPapers/README.md) | GATE MA PDF corpus for difficulty floors and RAG exemplars |
