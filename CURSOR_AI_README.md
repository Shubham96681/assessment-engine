# Instructions for Cursor AI (new clone / new device)

**Read first:** [SETUP_GUIDE.md](./SETUP_GUIDE.md) (full install, run, troubleshoot).

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
