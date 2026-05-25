# Assessment Engine — Complete Setup & RAG File Agent Guide

Use this document when you **clone the repo on a new machine** or hand the project to **Cursor AI**. It explains how to install, run, and use the **RAG file agent** (`rag_query.txt` → `rag_response.txt`) so quiz generation works the same as on your current device.

---

## Table of contents

1. [What this project does](#1-what-this-project-does)
2. [Prerequisites](#2-prerequisites)
3. [Clone and folder layout](#3-clone-and-folder-layout)
4. [First-time setup (step by step)](#4-first-time-setup-step-by-step)
5. [Run everything (daily workflow)](#5-run-everything-daily-workflow)
6. [RAG file agent — how query/response works](#6-rag-file-agent--how-queryresponse-works)
7. [Cursor AI setup (automatic responses)](#7-cursor-ai-setup-automatic-responses)
8. [Generate a quiz end-to-end](#8-generate-a-quiz-end-to-end)
9. [Configuration reference](#9-configuration-reference)
10. [Troubleshooting](#10-troubleshooting)
11. [Prompt to paste into Cursor on a new machine](#11-prompt-to-paste-into-cursor-on-a-new-machine)

---

## 1. What this project does

| Layer | Technology | Role |
|-------|------------|------|
| Frontend | Next.js (`http://localhost:3000`) | Upload PDF, configure quiz, view questions, download PDF |
| Backend | FastAPI (`http://localhost:8000`) | RAG search, question generation, PDF export |
| PostgreSQL | Docker port **5433** | Assessments, documents, questions |
| FAISS | Local `backend/data/faiss` | Vector search over PDF chunks (default; no Docker) |
| Redis | Docker port **6379** | Optional (reserved for future workers) |
| Cursor agent | `rag_query.txt` / `rag_response.txt` | Acts as the “LLM” when no API key is set |

**Without OpenAI/Gemini keys**, the backend writes a prompt to `rag_query.txt` and waits for **you or Cursor** to fill `rag_response.txt` with a JSON array of questions.

---

## 2. Prerequisites

Install on the new machine:

| Tool | Version | Notes |
|------|---------|--------|
| **Git** | Any recent | To clone the repo |
| **Docker Desktop** | Latest | Must be **running** before `docker compose` |
| **Python** | 3.11 or 3.12 | Backend |
| **Node.js** | 18+ (20 recommended) | Frontend |
| **Cursor IDE** | Latest | For RAG file agent + rules |

Optional:

- **Ollama** — local LLM instead of file agent (`OLLAMA_ENABLED=true`)
- **Google Gemini / OpenAI API key** — skips file agent entirely

---

## 3. Clone and folder layout

```bash
git clone <your-repo-url> assessment
cd assessment
```

Important paths:

```
assessment/
├── backend/                 # FastAPI app
│   ├── .env                 # YOU CREATE from .env.example (not always in git)
│   ├── main.py
│   ├── requirements.txt
│   └── uploads/             # PDFs, figures, exported quiz PDFs
├── frontend/                # Next.js UI
├── docker/
│   └── docker-compose.yml   # Postgres, Redis, Qdrant
├── rag_query.txt            # Written by backend during generate
├── rag_response.txt         # Written by Cursor / you
├── .cursor/
│   ├── rules/rag-response-agent.mdc   # Agent instructions
│   └── hooks.json                     # Auto-trigger agent
├── SETUP_GUIDE.md           # This file
└── RAG_FILE_AGENT.md        # Short RAG reference
```

---

## 4. First-time setup (step by step)

### 4.1 Start infrastructure (Docker)

```powershell
cd assessment\docker
docker compose up -d
```

Wait until containers are healthy:

```powershell
docker ps
```

You should see: `assessment_postgres`, `assessment_redis`, `assessment_qdrant`.

**Postgres is on host port `5433`** (not 5432) to avoid conflicts with other Postgres installs.

### 4.2 Backend setup

```powershell
cd assessment\backend
copy .env.example .env
```

Edit `backend\.env` — minimum for **RAG file agent mode** (no cloud API):

```env
DEBUG=true
OPENAI_API_KEY=
GOOGLE_GEMINI_API_KEY=
OLLAMA_ENABLED=false

RAG_FILE_AGENT_ENABLED=true
RAG_FILE_TIMEOUT_SECONDS=180
RAG_FILE_POLL_INTERVAL_SECONDS=2.0

DATABASE_URL=postgresql+asyncpg://assessment_user:assessment_pass@localhost:5433/assessment_db
QDRANT_URL=http://localhost:6333
LOCAL_STORAGE_PATH=./uploads
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

**Windows note:** If `pymupdf` fails, try:

```powershell
python -m pip install pymupdf==1.24.5 PyMuPDFb
```

First backend start downloads **sentence-transformers** (~1–2 min once). The API should still respond; indexing runs in a background thread.

### 4.3 Frontend setup

```powershell
cd assessment\frontend
npm install
```

Optional `frontend\.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 5. Run everything (daily workflow)

### Option A — Windows batch (easiest)

From repo root:

```powershell
.\START_ALL.bat
```

This starts Docker, backend (`start.bat`), and frontend (`npm run dev`).

### Option B — Three terminals (recommended for debugging)

**Terminal 1 — Docker** (if not already up):

```powershell
cd assessment\docker
docker compose up -d
```

**Terminal 2 — Backend:**

```powershell
cd assessment\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for:

- `Application startup complete`
- `Local embedding model ready` (may appear a few seconds later)

**Terminal 3 — Frontend:**

```powershell
cd assessment\frontend
npm run dev
```

### Verify

| URL | Expected |
|-----|----------|
| http://localhost:8000/health | `{"status":"healthy",...}` |
| http://localhost:8000/api/docs | Swagger UI |
| http://localhost:3000 | Assessment Engine UI |
| http://localhost:6333/dashboard | Qdrant UI |

---

## 6. RAG file agent — how query/response works

```mermaid
sequenceDiagram
    participant UI as Frontend
    participant API as FastAPI
    participant RAG as Qdrant + Embeddings
    participant Files as rag_query.txt / rag_response.txt
    participant Cursor as Cursor Agent

    UI->>API: POST /assessments/generate
    API->>RAG: Retrieve top 6 PDF chunks
    API->>Files: Write rag_query.txt (CONTEXT + QUESTION)
    Note over API,Files: Deletes nothing; waits up to 180s
    Cursor->>Files: Read rag_query.txt
    Cursor->>Files: Write rag_response.txt (ANSWER JSON)
    API->>Files: Read rag_response.txt
    API->>API: Parse JSON, draw figures, build PDF
    API->>UI: Assessment status = ready
```

### 6.1 `rag_query.txt` (written by backend)

Format:

```text
CONTEXT:
<retrieved PDF text chunks joined with --->

QUESTION:
<instructions: how many questions, types, difficulty, full prompt>
```

Created at **repository root**: `assessment/rag_query.txt`.

### 6.2 `rag_response.txt` (written by Cursor or you)

Format (**strict** — parser breaks otherwise):

```text
ANSWER:
[
  {
    "id": "1",
    "type": "FigureBased",
    "question": "...",
    "marks": 4,
    "figure_type": "labeled_diagram",
    "figure_spec": { ... },
    "correct_answer": "...",
    "explanation": "..."
  }
]

SOURCES USED:
Brief note on which CONTEXT parts you used.
```

Rules:

- Start JSON with `[` immediately after `ANSWER:` (no markdown fences).
- Match **exact question count and types** from `QUESTION`.
- Follow `.cursor/rules/rag-response-agent.mdc` for board-style stems and figure labels.

### 6.3 Timing

- Backend waits **`RAG_FILE_TIMEOUT_SECONDS`** (default 180s in config, may be 90 in your `.env`).
- Save `rag_response.txt **after** `rag_query.txt` updates for that run.
- If timeout: backend falls back to a **local** question builder (lower quality).

### 6.4 Manual finish (if UI stuck on “Generating”)

On the assessment page, click:

**“I filled rag_response.txt — finish now”**

Or call API:

```http
POST http://localhost:8000/api/v1/assessments/{assessment_id}/apply-rag-response
```

---

## 7. Cursor AI setup (automatic responses)

These files **must exist in the repo** after clone (commit them to git):

| File | Purpose |
|------|---------|
| `.cursor/rules/rag-response-agent.mdc` | Tells the agent how to write `rag_response.txt` |
| `.cursor/hooks.json` | Runs hooks on session start / agent stop |
| `.cursor/hooks/rag-common.ps1` | Detects pending query |
| `.cursor/hooks/rag-stop.ps1` | Injects follow-up message when query pending |
| `.cursor/hooks/rag-session-start.ps1` | Same on new chat |

### 7.1 Enable Cursor hooks

1. Open the project folder in **Cursor** (root = `assessment/`, not only `backend/`).
2. **Cursor → Settings → Hooks** — ensure hooks are **enabled**.
3. Keep an **Agent** chat open for this workspace.

When `rag_query.txt` is newer than `rag_response.txt`, the **stop** hook sends:

```text
RAG_FILE_AGENT: rag_query.txt is pending. Read the entire file at the project root,
follow .cursor/rules/rag-response-agent.mdc exactly, and write rag_response.txt...
```

### 7.2 Optional file watcher (Windows)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .cursor/hooks/watch-rag-query.ps1
```

Logs to `.cursor/rag_watch.log`.

### 7.3 Manual trigger (if hooks do not run)

Paste into Cursor Agent chat:

```text
RAG_FILE_AGENT: rag_query.txt is pending. Read the entire file at the project root,
follow .cursor/rules/rag-response-agent.mdc exactly, and write rag_response.txt
in the same directory. Do not ask for confirmation. Do not explain; only write the file.
```

---

## 8. Generate a quiz end-to-end

1. **Start** Docker + backend + frontend (Section 5).
2. Open http://localhost:3000 → **Upload Content**.
3. Upload a **PDF** (use **page range** e.g. 1–15 for speed).
4. Wait until document status is **Ready** (not “Processing…”).
5. Open **Generate Assessment** → select document, set title, question count (start with **5**), types, optional **Topic focus** (e.g. `Circles tangents`).
6. Click **Generate** → you are redirected to the assessment page (may show “Generating…”).
7. Watch repo root: **`rag_query.txt`** appears/updates.
8. Cursor should write **`rag_response.txt`** within the timeout.
9. Status becomes **Ready** → view questions, **Download PDF** / Answer Key.

**Speed tips**

- Upload one chapter, not a full book.
- Use page range on upload.
- Set topic focus on generate.
- Keep only **one** Agent chat processing RAG files.

---

## 9. Configuration reference

### `backend/.env` (main knobs)

| Variable | Typical value | Meaning |
|----------|---------------|---------|
| `RAG_FILE_AGENT_ENABLED` | `true` | Use file bridge instead of cloud LLM |
| `RAG_FILE_TIMEOUT_SECONDS` | `180` | Seconds to wait for `rag_response.txt` |
| `OLLAMA_ENABLED` | `false` | Use Ollama if `true` and running |
| `GOOGLE_GEMINI_API_KEY` | empty or key | If set, skips file agent |
| `DATABASE_URL` | `...@localhost:5433/...` | Must match Docker Postgres port |
| `QDRANT_URL` | `http://localhost:6333` | Vector DB |
| `ENABLE_INGEST_OCR` | `false` | OCR is slow; leave off |
| `MAX_INGEST_PAGES` | `0` | `0` = all pages; set `25` to cap upload time |

### Frontend

| Variable | Default |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` |

### API timeouts (frontend)

All requests use **120s** default (`frontend/src/lib/api.ts`) except upload (300s) and apply-rag-response (180s).

---

## 10. Troubleshooting

| Problem | Cause | Fix |
|---------|--------|-----|
| `timeout of 15000ms` / API timeout | Old frontend build or backend blocked | Restart backend + frontend; hard refresh `Ctrl+Shift+R` |
| “Loading documents…” forever | Backend not responding during indexing | Restart backend; use page range on upload |
| Document stuck **Processing** >12 min | Indexing failed/hung | Re-upload with page range; check Docker + Qdrant |
| **Generating** forever | No `rag_response.txt` or server reload mid-job | Fill response; click “finish now”; or regenerate |
| `rag_response` ignored | Saved **before** `rag_query.txt` updated | Save response **after** query file changes |
| Network Error on upload | Backend not on 8000 | Start uvicorn; check firewall |
| Postgres connection refused | Docker not running / wrong port | `docker compose up -d`; port **5433** in `.env` |
| PyMuPDF DLL error (Windows) | Binary mismatch | `pip install pymupdf==1.24.5 PyMuPDFb` |
| Empty quiz / 0 questions | Invalid JSON in `rag_response.txt` | Valid `[...]` array; see rule file |
| PDF has no figures | Bad `figure_spec` or path | Use `elements` in `figure_spec`; check `uploads/figures/` |

**Health check:**

```powershell
Invoke-WebRequest http://localhost:8000/health -TimeoutSec 5
Invoke-WebRequest http://localhost:8000/api/v1/documents -TimeoutSec 30
```

Both should return quickly (< 5s when idle).

---

## 11. Prompt to paste into Cursor on a new machine

Copy this into the **first Agent message** after opening the cloned repo:

```text
You are helping run the Assessment Engine at this repo root.

1. Read SETUP_GUIDE.md and follow it if I need setup.
2. RAG file agent mode is ON: when rag_query.txt appears or changes at the project root,
   read it fully, follow .cursor/rules/rag-response-agent.mdc exactly, and write
   rag_response.txt with ANSWER: (raw JSON array) and SOURCES USED:.
   Do not use markdown fences. Do not ask confirmation.
3. Backend: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
4. Frontend: cd frontend && npm run dev
5. Docker: cd docker && docker compose up -d
6. Postgres port is 5433, not 5432.

When I say "process RAG", check rag_query.txt vs rag_response.txt and write the response file.
```

---

## Quick reference card

```
┌─────────────────────────────────────────────────────────────┐
│  START:  docker compose up -d  (in docker/)                 │
│          uvicorn in backend/   → :8000                       │
│          npm run dev in frontend/ → :3000                    │
│  UPLOAD: PDF + optional page range → wait Ready              │
│  GENERATE: UI → rag_query.txt written                     │
│  CURSOR:  writes rag_response.txt (rules + hooks)          │
│  RESULT:  Assessment Ready + PDF download                    │
└─────────────────────────────────────────────────────────────┘
```

---

*Last updated for Assessment Engine — RAG file agent, async ingestion, port 5433 Postgres.*
