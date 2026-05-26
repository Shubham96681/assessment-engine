# RAG file agent (no API key)

> **Full setup on a new machine:** see [SETUP_GUIDE.md](./SETUP_GUIDE.md)  
> **Cursor AI quick instructions:** see [CURSOR_AI_README.md](./CURSOR_AI_README.md)

During quiz generation the backend writes **`rag_query.txt`** at the project root and waits for **`rag_response.txt`**.
## Files

| File | Written by | Content |
|------|------------|---------|
| `rag_query.txt` | Backend | `SELECTED DOCUMENT:` + `RETRIEVAL QUERY:` (dynamic: filename, chapter, class/JEE level) + `CONTEXT:` + `QUESTION:` |
| `rag_response.txt` | You / Cursor agent | `ANSWER:` + `SOURCES USED:` |

**Alignment:** CONTEXT chunks are retrieved only from the **document you pick** on the Generate page (`document_id`). The Cursor agent must write questions that match that CONTEXT (RD Sharma / RS Aggarwal depth), not another chapter.

**Stem style:** Compact RD Sharma voice — givens + Find/Prove; hidden theorem in stem; traps in numeric items. FigureBased stems stay 60+ words with sub-parts (i)(ii) on hard.

**Paper blueprint:** `rd_archetypes.py` emits **EXERCISE BLUEPRINT** in `rag_query.txt` (direct → hidden theorem → mixed → HOTS). Follow id order 1..N; do not copy exact textbook wording.

**Uniqueness:** `rag_query.txt` may include **PRIOR QUESTIONS — DO NOT REPEAT**. Each new generation must use **new stems** (different numbers, point labels, archetypes). Reusing the same `rag_response.txt` will cause dedup to drop repeats — update `rag_response.txt` with fresh JSON every round.

## Cursor agent (automatic)

Open the project in Cursor and keep an **Agent** chat open for this repo.

| Mechanism | Role |
|-----------|------|
| `.cursor/rules/rag-response-agent.mdc` | Defines how to read `rag_query.txt` and write `rag_response.txt` |
| `.cursor/hooks.json` (`stop`, `sessionStart`) | When `rag_query.txt` is newer than `rag_response.txt`, auto-continues the agent to process it |
| `.cursor/hooks/watch-rag-query.ps1` | Background watcher (run at dev time) logs changes under `.cursor/rag_watch.log` |

When the backend writes `rag_query.txt`, the agent should pick it up on the next turn (or immediately if a chat is already running and the `stop` hook fires). No manual prompt is required if hooks are enabled in **Cursor → Settings → Hooks**.

Optional: start the watcher in a terminal:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .cursor/hooks/watch-rag-query.ps1
```

## Generate a quiz

1. Restart backend: `python -m uvicorn main:app --reload` from `backend/`
2. Upload PDF → wait until **Ready**
3. Click **Generate** — backend writes `rag_query.txt` and waits up to 180s
4. With an Agent chat open, the hooks should process `rag_query.txt` automatically (within ~180s timeout)
5. Backend picks up `rag_response.txt` and builds the quiz

## Rejection corpus (negative training memory)

When quality gates **reject** a question, the backend stores it in:

| File | Purpose |
|------|---------|
| `rejection_corpus.jsonl` | Raw rejected stems + flags (audit) |
| `training_rejection_corpus.jsonl` | Instruction-style rows for future fine-tuning |
| Qdrant `generation_history` (`record_type=rejected`) | Semantic memory scoped by user/document/chapter |

On the next generation, the prompt includes a **REJECTION CORPUS** block listing banned patterns (`stem_too_long`, `symmetric_subparts`, etc.) so the file agent / LLM avoids repeating them.

```env
ENABLE_REJECTION_CORPUS=true
REJECTION_CORPUS_LIMIT=40
REJECTION_CORPUS_PROMPT_MAX_EXAMPLES=8
```

Restart the backend after changing these flags.

## Production prompt (quadratic full-hard)

When **Quadratic Equations** is locked and difficulty is **full hard** (≥90% hard), the backend writes a **compact** `QUESTION` block (~6 KB) instead of the legacy ~15–30 KB compiler stack.

| Setting | Default | Effect |
|---------|---------|--------|
| `QUADRATIC_PRODUCTION_PROMPT_ENABLED` | `true` | Use `backend/app/generation/production_prompts/quadratic_full_hard.py` |

Compact mode also omits `PRIOR QUESTIONS`, rejection corpus, and uniqueness blocks from `rag_query.txt` (dedup still runs after JSON parse). Set `QUADRATIC_PRODUCTION_PROMPT_ENABLED=false` to restore the verbose prompt.

## Quadratic L5 quality monitor (post-parse)

`ENABLE_QUADRATIC_QUALITY_MONITOR=true` runs stem + paper audits after every parse:

| Check | Blocks |
|-------|--------|
| Fusion score & word count | Thin L5 drills |
| Dead sub-part (i) | Equation-only (i), "(i) Answer ONE" |
| OR format | Must use (a)/(b); branches balanced; no trivial reciprocal branch |
| Hence chain | Factorisation cannot ignore discriminant from prior part |
| Verification | No circular "verify reciprocal product" |
| Paper | At most one "without quadratic formula" phrase per paper |
| Paper | At most three stems containing "verify" (`verification_fatigue`) |
| Sub-parts | No reference to (iii)/(iv) unless that part exists |
| Nature Q2 | Integrated only — no dead (i) + Hence factorise using D |

All paths use `quadratic_generation_pipeline.py` (generator, apply-rag, scripts) so **structural dedup keeps pool size** (10 for deliver-5) and bad stems are dropped before delivery.

### Computational math verification (mandatory)

`ENABLE_QUADRATIC_MATH_VERIFY=true` and `QUADRATIC_MATH_VERIFY_BLOCK_DELIVERY=true` (defaults) run `quadratic_math_verify.py` on **stem + correct_answer** for every quadratic item:

| Check | Catches |
|-------|---------|
| Factor pairs of ac | Impossible factorisation, wrong middle term from claimed factors |
| D = 0 parameters | Wrong k/p, internal contradictions (e.g. p = 68 vs p + 51 = 68) |
| Speed/time | Stem time difference ≠ back-substitution into distance/speed equation |
| α² + β² | Wrong final fraction vs (b/a)² − 2c/a |

**Cannot be bypassed** by `force=true` on apply-rag-response. Bad `rag_response.txt` returns **400** with `Quadratic math verification failed: …`. Regenerate until all pool items pass.

Failures appear in `generation_log` as `quadratic_quality_*` / `quadratic_paper_quality` and reject stems during `should_reject` / apply-rag-response.
Slot regen uses the **production prompt** (not the verbose compiler) to avoid `PromptContaminationError`.

## Config (`backend/.env`)

```env
RAG_FILE_AGENT_ENABLED=true
RAG_FILE_TIMEOUT_SECONDS=180
QUADRATIC_PRODUCTION_PROMPT_ENABLED=true
OLLAMA_ENABLED=false
```

If timeout, the backend falls back to the structured local question builder.

## Topic isolation (chapter drift fix)

When you switch PDFs (e.g. Circles → Quadrilaterals):

1. `clear_topic_cache()` deletes stale `rag_response.txt` and writes `rag_topic_state.json`
2. `rag_query.txt` includes `LOCKED CHAPTER: quadrilaterals` (from filename / topic focus)
3. Stale circle answers are **not** reused (`response_matches_current_topic`)
4. Questions with `tangent`, `radius`, etc. are **rejected** when chapter is Quadrilaterals

Set **Topic focus** on Generate to `Quadrilaterals` if the filename is ambiguous.

## Quality reject → slot regeneration

When a question fails quality checks (`QUALITY_REGEN_ENABLED=true`), the backend rewrites **`rag_query.txt`** with a **QUALITY REGENERATION** prompt for that single slot and waits for a **new** `rag_response.txt` (mtime after the query).

| File | Role |
|------|------|
| `rag_regen_pending.json` | Written while waiting; shows slot number and rejection reason |
| `rag_query.txt` | `QUESTION:` block starts with `QUALITY REGENERATION — Cursor agent` |
| `rag_response.txt` | `ANSWER:` must be a JSON array with **one** object and matching `"id"` |

Config:

```env
QUALITY_REGEN_ENABLED=true
QUALITY_REGEN_USE_CURSOR=true
RAG_FILE_SLOT_REGEN_TIMEOUT_SECONDS=180
```

If Cursor does not respond in time, the backend falls back to Gemini/OpenAI/Ollama for that attempt.
