# RD Sharma / RS Aggarwal — Question Quality Reference

> **Full calibration guide:** [RD_SHARMA_CLASS10_REFERENCE.md](./RD_SHARMA_CLASS10_REFERENCE.md)  
> Reference PDF at repo root: `RD_Sharma_Class10_Maths.pdf` (upload chapters for RAG, not the whole 90MB file at once).

## Target voice

**Good:** PQ is a tangent at P to a circle with centre O. OP = 5 cm, OQ = 12 cm. Find PQ.

**Bad:** Show your working; Students often subtract…; Examine/Analyze/configuration.

## Difficulty tiers

| UI tier | Textbook level | Stem | Answer steps |
|---------|----------------|------|--------------|
| easy | Level-I | 1 sentence, direct | 2–3 |
| medium | Level-II | 1–2 sentences | 4–5 |
| hard | Level-III / HOTS | compact + (i)(ii) or OR | 6+ |

## Variety per paper

Mix: direct find | prove | angle/chord | justify | concentric or mixed theorem — not five copies of the same tangent problem.

## Archetypes, bands, sequencing

- **Archetypes:** direct theorem, length find, angle, converse, chord–tangent, concentric, traps, HOTS — see full table in [RD_SHARMA_CLASS10_REFERENCE.md](./RD_SHARMA_CLASS10_REFERENCE.md)
- **Bands L1–L5** map to easy/medium/hard answer depth (not stem length)
- **Paper order:** ids 1→N follow blueprint: direct → hidden theorem → mixed → HOTS

## Engine configuration

| File | Role |
|------|------|
| `textbook_constants.py` | Global meta-language bans |
| `author_styles.py` | RD Sharma vs RS Aggarwal profiles |
| `authenticity.py` + `solution_difficulty.py` | Textbook detector + answer-graph difficulty |
| `curation.py` | Strip meta language, compress stems |
| `rd_archetypes.py` | Chapter fingerprints, uneven blueprint |
| `quality.py` + `generator.py` | Score → curate → filter pipeline |
| `.cursor/rules/rag-response-agent.mdc` | `rag_response.txt` rules |

**RS mode:** type `RS Aggarwal` in Generate instructions.

Default UI: **10% easy / 30% medium / 60% hard** on Generate page.

Regenerate assessments after prompt updates; old PDFs keep old wording.
