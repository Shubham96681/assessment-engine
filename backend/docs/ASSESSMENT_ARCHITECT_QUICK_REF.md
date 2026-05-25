# Assessment Architect — Quick Reference

Full spec: `app/generation/assessment_architect_rules.py` | Cursor: `.cursor/rules/assessment-architect.mdc`

## Instant rejection

| Check | Fail | Fix |
|-------|------|-----|
| Blank / partial | Missing (ii)(iii) | One question at a time |
| Header | yjd, dfyil, test 11 | `Subject: Mathematics \| Class: 11/12 \| Date: DD MMM YYYY` |
| LaTeX | `\mathfrak`, `\begin{` | Unicode only: π √ θ ≤ ∈ |
| Difficulty | Hard label, score ≤3 | Step-count algorithm |
| Marks | 6 marks, 3 steps | Cognitive step formula |
| Duplicate | Same equation stem | Skill registry |
| Hence | sin 2x → Hence sin 75° | Use sin(A+B) base |
| Verify | sin²θ+cos²θ=1 | Remove |
| Angles | 7.5°, 17.5°, 162°30′ | Approved list |
| Paper | &lt;80 marks / 3h | 10×6 + capstone 8 |

## Difficulty score → label

| Score | Label |
|-------|-------|
| 1–3 | Easy |
| 4–6 | Moderate |
| 7–10 | Hard |
| 11–14 | Very Hard |
| 15+ | Extreme |

## Marks (round 0.5 up)

Min **2** | Max **6** | Extended **8** (4+ parts)

Key steps: formula_proof(3), general_solution(2), optimization(3), compound_angle(2), factorization(1.5)

## Trigonometry codes (max/paper)

| Code | Max | Example |
|------|-----|---------|
| P-D | 1 | 330° → radian, quadrant |
| P-R | 1 | −19π/4 reduction |
| C-P | 1 | Prove tan(A+B) |
| M-A | 1 | cos 3θ identity |
| P-S | 1 | sec φ, QIV ratios |
| I-P | 2 | cot² identity |
| T-E | 2 | Solve in [0,2π) + count |
| I-T | 1 | tan⁻¹ sums |
| O-E | 1 | R sin(x+α) max |
| C-I | 1 | A+B+C=π |

**10Q mandatory:** T-E, O-E, I-T, one of C-P/M-A/I-P with 3-part Hence.

## Hence 3-gate

1. Requires previous result  
2. Sufficient with previous only  
3. Foundation → Application → Extension  

## Approved angles (°)

15, 18, 22.5, 30, 36, 45, 60, 75, 105, 120, 135, 150, 165, 195, 255, 330

## rag_response.txt

```
ANSWER:
[{...}]
SOURCES USED:
...
```
