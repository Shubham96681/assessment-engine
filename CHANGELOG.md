# Changelog

All notable project changes should be recorded here by default.

## Unreleased

### Added

- **Jinja2 RAG JSON:** `rag_response_jinja.py` + `templates/rag/` canonicalize `rag_response.txt` (`ANSWER:` + JSON array + `SOURCES USED:`); `parse_rag_response_json()` / `format_rag_response_json()` on the file bridge.
- **LaTeX PDF export:** `PDF_BACKEND=latex` uses `templates/latex/preamble.tex.j2` (amsmath, fancyhdr, `\Real`/`\vect`), `enumerate` question layout, display `\[...\]` for recurrences, `s\,p_{n-1}` thin-space multiplication, `(i)(ii)` sub-parts; auto-falls back to ReportLab without TeX on PATH.

### Fixed

- **PDF fragmented stems:** each `p_n` / `α^n` token was a separate table row (one symbol per line). Stems now use one flowing ReportLab paragraph with `<sub>`/Unicode (`PDF_MATH_USE_IMAGES=false`). `s x p_{n-1}` typo fixed to `s·p_{n-1}`.
- **PDF subscript spacing:** tuned ReportLab `<sub>` baseline (`rise`) and forced `p<n>` adjacency in `p_n` notation to reduce the visual gap.
- **PDF subscript spacing (tighter):** reduced `<sub>` `size` and raised baseline further to bring `p` and `n` closer visually.
- **PDF subscript spacing (tightest):** reduced `<sub>` to `size=5` and `rise=-0.2` to eliminate remaining disjoint look in `p_{n}` / `p_{n-1}`.
- **Missing underscore indices:** normalize OCR-style `p0`, `p 1`, `pn-1` → `p_{0}`, `p_{1}`, `p_{n-1}` so subscripts always render in PDF/UI.
- **Subscript spacing (UI+PDF):** adjusted ReportLab `<sub>` (`size=4`, `rise=0`) and web UI `<sub>/<sup>` CSS to reduce visible separation in `p_{n}` / `p_{n-1}`.

### Changed

- **Quadratic M.Tech difficulty framework:** `quadratic_mtech_full_hard.py` and `quadratic_mtech_benchmark.py` now encode structural escalation (hidden D, parameter families, iff proofs, without-finding-roots, recurrence, construction, multi-condition k, reverse-engineer) and ban procedural/long-arithmetic difficulty.
- **Paper-style math display:** `x^2`/`x^4` → `x²`/`x⁴`; bare `p_n`/`p_n-1` → subscript rendering; recurrence `p_{n} = s·p_{n-1} − t·p_{n-2}` and fractions like `85/9` route to KaTeX in UI/PDF; middle-dot `·` preserved (not turned into `x`).
- **Assessment download UX:** Status poll now includes `pdf_url` / `answer_key_url`; detail page shows a prominent download card (not only header buttons); list page enables PDF when `pdf_url` exists.
- **M.Tech quadratic delivery (assessment `zstzjzj`):** Replaced board L5 pool apply with L8–L9 set (existence proofs, parameter family, Newton recurrence, transformed roots, domain optimization); 34 marks / 5 questions from 10-item oversample pool.

### Added

- **Quadratic M.Tech track (100% hard UI):** `quadratic_mtech_benchmark.py`, `quadratic_mtech_full_hard.py` prompt, `quadratic_mtech_stem_gate.py`; routed when `QUADRATIC_MTECH_AT_FULL_HARD=true` (default) — L8–L9 existence proofs, parameter families, construction, recursive roots, boundary optimization on Class 10 syllabus.
- **Quadratic duplicate registry** (`quadratic_duplicate_registry.py`): bans exact (a,b,c), area, and speed/time reuse in compact RAG prompts and drops registry duplicates in the pool pipeline.
- **PDF header fixes** (`paper_header.py`): 5-question / ≤35 mark papers show **1 Hour** (not 3 Hours); garbage UI titles replaced with `Subject — topic`.
- **Archetype coverage warnings** in quadratic pool pipeline (nature_of_roots, HOTS, etc.).

- **RAG capture automation**: `rag_capture.py`, background auto-apply loop, `POST /api/v1/rag/finish-capture`, `backend/scripts/rag_capture_finish.py`, `.cursor/hooks.json` (stop + afterFileEdit), frontend auto-apply when `rag_response.txt` validates — workflow is Generate → say **go capture** → done (no Apply button).
- GATE exam corpus ingestion: `GATE_QuestionPapers/`, benchmark floors, and `gate_reference` vector index (mirrors CBSE pipeline).
- Repo documentation scaffold: `AGENTS.md`, `CHANGELOG.md`, `PROJECT_CONTEXT.md`, and `updates/` per `setup.md`.
- PDF-driven chapter/topic inference with trig density override for misclassified NCERT chapter blobs (`pdf_content_analyzer.py`, `topic_extractor.py`).
- CBSE corpus dynamic quality floors (`cbse_benchmark.py`, `build_cbse_benchmark.py`).
- Structured chunking, retrieval rerank, and RL reward hooks (phyEngine-inspired, wired into generation quality).

### Changed

- Raised default difficulty mix (L4/L5 bands, elevated-hard at 55%+ slider) and stem-rephrase rules for harder Circles items.
- Circles papers now assign FigureBased to all 5 slots by default; geometry chapters enforce a diagram floor in `question_type_planner.py`.
- Generate UI defaults: 75% hard, FigureBased + ShortAnswer + LongAnswer pre-selected.
- `GET /documents/{id}/topic-profile` persists reconciled chapter via `save_topic_map()` after extraction.
- Topic profile build order: subtopics before `infer_locked_chapter_from_pdf`, with post-refine re-inference.

### Fixed

- Quadratic equal-roots + linear constraint: `verify_equal_roots_linear_constraint` rejects when `ax + b = c` disagrees with `r = −b/(2a)` (caught Iteration 6 Q5 contradiction); prompt numeric rule updated.
- Wrong `locked_chapter` (triangles/circles) for `Class_11_Maths_Chapter_3_Trigonometric_Functions.pdf` when indexed content mixed geometry exercises with trigonometry.

---

## [2026-05-26]

Shipped in commit `148ef59` on `main`.

### Added

- **Quadratic Equations — computational math verification** (`quadratic_math_verify.py`, `quadratic_math_gate.py`): automatic checks on every generation and `apply-rag-response` path for wrong factorisations, equal-root parameter contradictions, speed/time back-substitution, α²+β² arithmetic, rectangle area vs stated dimensions, and OR-branch root-difference parameters (Vieta + |α − β|).
- **Quadratic L5 production prompt** (`production_prompts/quadratic_full_hard.py`) with mandatory verification steps; wired via `QUADRATIC_PRODUCTION_PROMPT_ENABLED`.
- Quadratic full-hard pipeline: `quadratic_generation_pipeline.py`, `quadratic_paper_quality.py`, `quadratic_hard_stem_gate.py`, `quadratic_hard_benchmark.py`.
- GATE reference modules: `gate_benchmark.py`, `gate_reference_*`, `build_gate_benchmark.py`, `build_gate_reference_index.py`.
- `validate_rag_answer_json()` — rejects invalid `rag_response.txt` pools at read time when math verification is enabled.
- Config flags (`.env.example`): `ENABLE_QUADRATIC_MATH_VERIFY`, `QUADRATIC_MATH_VERIFY_BLOCK_DELIVERY`, `ENABLE_QUADRATIC_QUALITY_MONITOR`, `QUADRATIC_QUALITY_BLOCK_DELIVERY`.
- Regression tests: `test_quadratic_math_verify.py`, `test_quadratic_math_gate.py` (covers iteration 3–5 audit failures and OR root-difference cases).
- `GET /api/v1/llm/health` endpoint (`llm_health.py`).

### Changed

- Quadratic math gate runs for **all** quadratic papers (not only full-hard L5); stem-quality audits remain full-hard only.
- `apply-rag-response?force=true` bypasses chapter/quality warnings but **not** quadratic math verification when blocking is enabled.
- `math_stem_validator.py`: `quadratic_math_verification_failed` is a critical flag (same tier as trig SymPy failures).
- `QualityScorer.should_reject` and `rag_file_bridge` call quadratic math checks before delivery.
- `RAG_FILE_AGENT.md` documents math verification blocking on apply-rag and file-agent read paths.

### Fixed

- Recurring quadratic paper math errors from manual audits: wrong ac factor pairs, invented factorisations, speed/time stem–equation mismatch, wrong post-solve dimensions, α²+β² fraction slips, internal parameter contradictions (e.g. p = 68 vs p + 51 = 68).
- Area verifier parsing when stems/answers had spaces stripped (`area143m²`, compact dimension lines).
