# RD Sharma Class 10 — Authentic Question Style (calibration)

Use this when tuning prompts and reviewing generated papers. Source: `RD_Sharma_Class10_Maths.pdf` (mostly scanned; sample text from Ch. 1 divisibility) + standard RD Sharma / RS Aggarwal exercise patterns.

## What RD Sharma / RS Aggarwal sounds like

**Good (book-quality):**
- PQ is a tangent at P to a circle with centre O. OP = 5 cm, OQ = 12 cm. Find PQ.
- Tangents TA, TB from T. If ∠ATB = 60°, find ∠AOB.
- Concentric circles, radii 7 cm and 4 cm. Find chord of larger touching smaller.
- PA, PB tangents from P. OA = 5 cm, OP = 13 cm. Find AP.
- Can a tangent be drawn through a point inside the circle?

**Bad (AI worksheet — reject):**
- Show your working / Use the diagram / Students often subtract…
- Examine, Analyze, configuration, mechanical-geometric
- Using the tangent theorem, calculate AP when OA = 5 cm and OP = 13 cm.
- The segment PQ lies along the tangent from P to Q.

## Core principle

> **Difficulty comes from thinking, not word count.**

Stems stay compact; multi-step reasoning lives in the model answer.

## Human textbook behavior (final layer)

| Rule | Detail |
|------|--------|
| Meta language | Banned globally — see `textbook_constants.BANNED_META_PHRASES` |
| Stem length | L1: 12–25 words; L3: 20–40; HOTS: 35–60; occasional one-liner |
| Traps | Invisible — never explain in stem |
| Rhythm | Uneven: easy → medium → **spike** → conceptual → HOTS |
| Author modes | RD Sharma (`author_styles.py`) vs RS Aggarwal |
| Real difficulty | `solution_difficulty.py` scores answer theorem chain |
| Pipeline | generate → score → `curation.compress_stem` → authenticity filter |

**RS mode:** Put `RS Aggarwal` in Generate instructions field.

## Exercise archetypes (sample across each paper)

| Archetype | Example pattern |
|-----------|-----------------|
| Direct theorem | Radius ⟂ tangent — Prove / Show that |
| Length finding | Givens + Find PQ (theorem hidden) |
| Angle theorem | ∠ATB → ∠AOB |
| Converse / identify | Tangent through interior point? |
| Chord–tangent combo | Chord + tangent in one solve |
| Concentric circles | Chord of larger touching smaller |
| Common tangents | Two circles, external tangent length |
| Secant + tangent | Contrast secant vs tangent |
| Hidden theorem | Find AP with OA, OP only — no theorem name in stem |
| HOTS mixed | Prove → Hence find; OR; (i)(ii) |

Engine: `backend/app/generation/rd_archetypes.py` rotates archetypes and emits an **EXERCISE BLUEPRINT** for ids 1..N.

## Difficulty bands (L1–L5)

| Band | UI mapping | Characteristics |
|------|------------|-----------------|
| L1 | easy | Single theorem, direct |
| L2 | easy | Slight variation, 2-step |
| L3 | medium | Hidden theorem in stem |
| L4 | medium | Mixed geometry (two ideas) |
| L5 | hard | Trap, OR, Olympiad-lite |

## Exercise sequencing (within one paper)

1. Direct (L1)  
2. Variation (L2)  
3. Hidden theorem (L3)  
4. Mixed (L4)  
5. HOTS / trap (L5)  

Questions are kept in **id order 1 → N**, not re-sorted by quality score.

## Human imperfection / hidden theorem

| AI-style (reject) | Book-style (use) |
|-------------------|------------------|
| Using the tangent theorem, calculate AP | PA, PB tangents from P. OA = 5 cm, OP = 13 cm. Find AP. |
| By Pythagoras theorem, find… | Find the length of PQ. (theorem in answer only) |

## Trap construction

Natural traps (distractors = wrong intermediate):

- OP − OA instead of √(OP² − OA²) when finding tangent length  
- Confusing secant with tangent  
- Assuming tangent exists through interior point  

## Question compression

If removing ~30% of words does not change the mathematics, shorten the stem.

| Verbose | Compressed |
|---------|------------|
| A tangent is drawn from an external point to a circle… | From P, tangents PA and PB. OA = 5 cm, OP = 13 cm. Find AP. |

## Figure diversity (when FigureBased)

Mix diagrams across a set — not five identical “external point + two tangents”:

- Concentric circles + chord  
- Angle ATB / AOB  
- Secant vs tangent  
- Interior point (no tangent)  
- Common external tangents (if CONTEXT supports)

## RAG workflow (structure, not copying)

Use chapter PDFs to extract:

- Theorem patterns and archetypes  
- Difficulty progression  
- Phrasing style  

Do **not** semantically copy exact RD Sharma / NCERT question wording.

## Difficulty ladder (UI tiers)

| Tier | RD / RS level | Stem style | Steps in answer |
|------|---------------|------------|-----------------|
| easy | Level-I | One precise sentence; direct theorem or substitution | 2–3 |
| medium | Level-II | 1–2 sentences; two linked ideas (theorem → find) | 4–5 |
| hard | Level-III / HOTS | Compact stem + (i)(ii) or OR; hidden theorem | 5–7 |

## Language rules

| Use | Avoid |
|-----|--------|
| Find, Prove, Show that, Calculate, If … then find, Hence | Examine, Analyze, Explore, Discuss, Describe the configuration |
| Short givens then command | “With reference to”, “mechanical-geometric”, “several lines are drawn” |
| One figure cue max: “In the figure,” or givens only | “In the adjoining figure,” on every item |
| Hidden theorem (student must recall) | Spelling out every step in the question stem |

## Stem length (aggressive compression)

| Band | Words |
| L1 direct | 12–25 |
| L2–L3 | 20–40 |
| L5 HOTS | 35–60 |
| One-line conceptual | 8–18 (occasional) |
| FigureBased | 20–55 typical |

- **Never:** 150+ word essay stems; meta phrases (Show your working, Use the diagram)

## Model answers

- Numbered: Given → Step 1 → … → Hence
- Name theorem when used (e.g. tangent ⟂ radius)
- Value points for marking scheme in `explanation`

## Micro-quality layer (stability)

| Module | Role |
|--------|------|
| `idiomatic_geometry_patterns.py` | Standard theorem phrasing; fix awkward idiom |
| `question_completeness.py` | Self-contained stems; angle-find givens; text–figure independence |
| `quality.should_reject()` | Drops incomplete / awkward / low combined score |

**Reject examples:** "find angle PTQ" without POQ; "passes through the perpendicular".

## Elite layer (92% → 98%)

| Feature | Module |
|---------|--------|
| Author imperfection profiles | `author_imperfections.py` — proof habits, theorem repeat bias |
| Exercise memory | Blueprint: Q2 teaches → Q5 disguised reuse |
| Sparse hard | Q3 minimal stem (`Prove that PA = PB.`) — deep answer only |
| Visual style memory | Dashed radii, tangent placement, chord naming per author |
| Imperfect compression | `curation.py` — ~1 in 4 slots keep light redundancy |
| Solution-graph difficulty | `solution_difficulty.py` — not word-count difficulty |

## Engine wiring

| File | Role |
|------|------|
| `backend/app/generation/textbook_constants.py` | Global bans, stem targets, difficulty mix |
| `backend/app/generation/author_styles.py` | RD vs RS author DNA |
| `backend/app/generation/author_imperfections.py` | Controlled human habits + visual memory |
| `backend/app/generation/authenticity.py` | Textbook detector |
| `backend/app/generation/solution_difficulty.py` | Solution-graph difficulty |
| `backend/app/generation/numeric_constraint_validator.py` | TA²=TC·TD, OT²−r², angle sums — reject bad givens |
| `backend/app/generation/hard_mode_calibration.py` | Hard UI: theorem depth, banned L1 stems |
| `backend/app/generation/reasoning_signature.py` | Reasoning-graph dedup (max 1 tangent-pair central-angle per paper) |
| `backend/app/generation/angle_target_validator.py` | Reject TOW-style targets; require TOU for tangent-pair items |
| `backend/app/generation/proof_elegance.py` | Flag non-textbook chord ⟂ proofs (ON > OM chains) |
| `backend/app/generation/curation.py` | Meta-language strip + compression |
| `backend/app/generation/rd_archetypes.py` | Chapter fingerprints, human blueprint |
| `backend/app/generation/quality.py` | Combined score + curation |
| `backend/app/generation/content_profile.py` | Dynamic RAG query + chapter/exam detection from PDF + context |
| `backend/app/generation/chapter_concept_classifier.py` | Lock chapter from filename/topic/CONTEXT; classify stems |
| `backend/app/generation/strict_topic_gate.py` | Reject circle/tangent stems when chapter is Quadrilaterals, etc. |
| `backend/app/generation/topic_isolation.py` | Clear stale `rag_response.txt` on document/chapter change |
| `backend/app/generation/structural_dedup.py` | Block Q2=Q3=Q4 duplicate theorem graphs |
| `backend/app/rag/chapter_chunk_filter.py` | Drop contaminated RAG chunks before generation |
| `backend/app/generation/generator.py` | Full pipeline wiring |
| `.cursor/rules/rag-response-agent.mdc` | Same rules for `rag_response.txt` |
| `TEXTBOOK_EXERCISE_REFERENCE.md` | Short pointer to this file |

After prompt changes, **regenerate** assessments; upload chapter PDFs (not only NCERT) for RAG context.
