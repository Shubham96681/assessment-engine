# Instructions for Cursor AI (new clone / new device)

**Read first:** [SETUP_GUIDE.md](./SETUP_GUIDE.md) (full install, run, troubleshoot).

## Daily workflow (automated)

1. User clicks **Generate** in the UI (http://localhost:3000).
2. User says **go capture** in this Agent chat (or Hooks auto-prompt on `stop` when pending).
3. You read `rag_query.txt`, write verified `rag_response.txt`, run `cd backend && python scripts/rag_capture_finish.py`.
4. Backend auto-applies when the file validates — user does **not** click "Apply rag_response.txt".

Enable **Cursor → Settings → Hooks** for `.cursor/hooks.json`.

## Your job when `rag_query.txt` changes

1. Read `rag_query.txt` at the **repository root** (not `backend/`).
2. Follow `.cursor/rules/rag-response-agent.mdc` **exactly**.
3. Write `rag_response.txt` in the same folder:

```text
ANSWER:
[ ... valid JSON array only ... ]

SOURCES USED:
...
```

4. Do **not** ask the user to confirm. Do **not** explain in chat — only write the file (unless the user asks otherwise).

## Pending check

`rag_query.txt` is pending when:

- `rag_response.txt` does not exist, OR
- `rag_response.txt` is older than `rag_query.txt`, OR
- response is empty / invalid JSON

PowerShell logic: `.cursor/hooks/rag-common.ps1` → `Test-RagQueryPending`.

## Services to run (if user asks to start the app)

```powershell
cd docker; docker compose up -d
cd ..\backend; python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
cd ..\frontend; npm run dev
```

## Critical config

- Postgres: **localhost:5433**
- API: **http://localhost:8000/api/v1**
- UI: **http://localhost:3000**
- `backend/.env`: `RAG_FILE_AGENT_ENABLED=true`

## If generation is stuck on "Generating"

User can click **"I filled rag_response.txt — finish now"** or you can ensure `rag_response.txt` is valid, then they call:

`POST /api/v1/assessments/{id}/apply-rag-response`
