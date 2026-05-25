# Changelog

All notable project changes should be recorded here by default.

## Unreleased

### Added

- Repo documentation scaffold: `AGENTS.md`, `CHANGELOG.md`, `PROJECT_CONTEXT.md`, and `updates/` per `setup.md`.
- PDF-driven chapter/topic inference with trig density override for misclassified NCERT chapter blobs (`pdf_content_analyzer.py`, `topic_extractor.py`).
- CBSE corpus dynamic quality floors (`cbse_benchmark.py`, `build_cbse_benchmark.py`).
- Structured chunking, retrieval rerank, and RL reward hooks (phyEngine-inspired, wired into generation quality).

### Changed

- `GET /documents/{id}/topic-profile` persists reconciled chapter via `save_topic_map()` after extraction.
- Topic profile build order: subtopics before `infer_locked_chapter_from_pdf`, with post-refine re-inference.

### Fixed

- Wrong `locked_chapter` (triangles/circles) for `Class_11_Maths_Chapter_3_Trigonometric_Functions.pdf` when indexed content mixed geometry exercises with trigonometry.
