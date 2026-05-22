# CBSE Class 10 Mathematics (Standard) — PYQ Quality Reference

This document summarizes **2023 / 2024 / 2025** Previous Year Question (PYQ) papers in the repo root so generated questions match **board exam level** (English only).

Reference files (not auto-ingested — style guide only):

- `CBSE_Class10_Maths_Standard_2023_PYQ.pdf` (24 pages; may be scan-heavy)
- `CBSE_Class10_Maths_Standard_2024_PYQ.pdf` (marking scheme + structure)
- `CBSE_Class10_Maths_Standard_2025_PYQ.pdf` (full question paper text)

---

## Official paper structure (80 marks)

| Section | Q nos. | Type | Marks each | Count | Section total |
|---------|--------|------|------------|-------|----------------|
| **A** | 1–18 | MCQ | 1 | 18 | 18 |
| **A** | 19–20 | Assertion–Reason | 1 | 2 | 2 |
| **B** | 21–25 | Very Short Answer (VSA) | 2 | 5 | 10 |
| **C** | 26–31 | Short Answer (SA) | 3 | 6 | 18 |
| **D** | 32–35 | Long Answer (LA) | 5 | 4 | 20 |
| **E** | 36–38 | Case Study | 4 | 3 | 12 |
| | | | | **38 questions** | **80** |

**Internal choice:** 2 questions each in B, C, D; 3 in E (OR alternatives).

---

## Question quality patterns (what to copy)

### Section A — MCQ (1 mark)

- One clear stem; **exactly four options (A)–(D)**.
- Tests competency: polynomials, coordinate geometry, trig ratios, AP/GP, probability, mensuration, linear equations.
- Example style: *If α and β are zeroes of 3x² + 6x + k such that α + β + αβ = −2/3, then k is:*
- Distractors are numerical and plausible (common mistakes).

### Section A — Assertion–Reason (1 mark)

Fixed four options every time:

- (A) Both A and R true; R **correctly explains** A  
- (B) Both A and R true; R **not** correct explanation of A  
- (C) A true, R false  
- (D) A false, R true  

Stem format:

```text
Assertion (A): ...
Reason (R): ...
```

### Section B — VSA (2 marks)

- **Find / Evaluate / Show that** with 1–2 steps.
- Often includes **OR** alternative in same question number.
- Example: *If x cos 60° + y cos 0° + sin 30° cot 45° = 5, find x + 2y.*
- Example (geometry): *PA and PB are tangents from P; PA = 10 m, OP = 26 m; find radius.*

### Section C — SA (3 marks)

- Multi-step: prove identity, similarity, coordinate geometry, statistics, surface area.
- Example: *Prove that BAC + ACD = 90°* (tangent + circle).
- Example: *Find ratio in which y-axis divides segment joining (5, −6) and (−1, 4); find intersection point.*
- **OR** choice common.

### Section D — LA (5 marks)

- Longer proofs or applications: A.P., probability, coordinate geometry, trigonometry proofs.
- Sub-parts (i), (ii) with partial marking.
- Example: *Prove* trigonometric identity with full LHS/RHS working.

### Section E — Case Study (4 marks)

- Short **real-world / data context** (100–150 words).
- **2–3 sub-questions** with internal choice in one sub-part.
- Sub-questions mix **Find**, **Calculate**, **Prove** (1–2 marks each inside 4).

### Figure / diagram questions

- Wording: *In the given figure*, *O is centre of circle*, *adjoining figure*.
- Given lengths on diagram: cm, m; angles named with three letters (∠APO).
- Tasks: **Prove**, **Show that**, **Find** — always **show working**.

---

## Language rules (English only)

- Formal board English; no Hindi, no Hinglish.
- Use: *Prove that*, *Find*, *Show that*, *Hence*, *OR*, *Verification*.
- Units in questions: cm, m, m², m³, ° where needed.
- Take π = 22/7 if required (state in paper instructions).

---

## What NOT to do

- Do not copy exact PYQ numbers or names from these PDFs into new papers.
- Do not use NCERT activity text (*Activity 3: Draw a circle…*) as question stems.
- Do not use one-line questions for 3–5 mark items.
- Do not use non-standard point labels (symbols, subscripts).

---

## How the app uses this reference

1. **Prompts** (`backend/app/generation/prompts.py`) embed `CBSE_PYQ_STYLE` in every generation.
2. **Cursor rule** (`.cursor/rules/rag-response-agent.mdc`) enforces PYQ-level stems for `rag_response.txt`.
3. **Content** still comes from **your uploaded chapter PDF** (RAG) — PYQ PDFs are **style only**, unless you upload them as documents.

### Recommended generate settings (one chapter quiz)

| Setting | Value |
|---------|--------|
| Subject | Mathematics |
| Class | 10 |
| Language | English |
| Question types | MCQ, AssertionReason, ShortAnswer, FigureBased, LongAnswer, CaseStudy |
| Count | 5–10 for practice; 38 for full mock paper |
| Topic focus | e.g. *Circles tangents*, *Quadratic equations* |
| Difficulty mix | 30% easy, 50% medium, 20% hard (matches board spread) |

### Full mock paper preset (38 questions)

Use Generate with: **20 MCQ + 2 AR + 5 VSA + 6 SA + 4 LA + 3 Case Study** — configure types/counts in UI or via API to total 38.

---

## Upload workflow for best quality

1. Upload **NCERT chapter PDF** (with page range) — source facts.
2. Keep PYQ PDFs in repo as reference (optional).
3. Set **Topic focus** to chapter name.
4. Generate with **RAG file agent** or Gemini for PYQ-level wording.
5. Export PDF from assessment page when status is **Ready**.
