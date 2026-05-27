# 20 Hardest Trigonometry Questions — full-hard calibration

**When UI = 100% hard and chapter = trigonometry**, generation targets this reference paper (invent new numbers — do not copy stems verbatim).

| Section | Qs | Marks | Focus |
|---------|-----|-------|--------|
| A | 1–4 | 24 | Compound & multiple angles |
| B | 5–8 | 24 | Equations & general solutions |
| C | 9–12 | 24 | Identities & algebraic manipulation |
| D | 13–15 | 18 | Inverse trigonometry |
| E | 16–18 | 18 | Triangle properties |
| F | 19–20 | 14 | Advanced reduction & optimization |
| **Total** | **20** | **122** | ~3 hours |

**Passing:** ~45 marks | **Distinction:** ~85+ marks

## Difficulty mix

| Level | Share | Example slots |
|-------|-------|----------------|
| Hard (JEE Main) | ~60% | Q1–4, Q9–12, Q16–18 |
| Very Hard (JEE Advanced) | ~40% | Q5–8, Q13–15, Q19–20 |

## Sample slot roles (reference)

| Slot | Marks | Role |
|------|-------|------|
| Q1 | 6 | Prove sin(A+B); Hence tan 3θ; numeric application |
| Q2 | 6 | sin α+sin β=a, cos α+cos β=b → prove identities |
| Q3 | 6 | sin θ/sin 7θ polynomial; Hence roots of cubic |
| Q4 | 6 | A+B+C=π → tan sum, sin 2 sum; Hence evaluate tan sum |
| Q5 | 6 | General solution: cubed sine identity; count in [0,2π] |
| Q6–8 | 6 | Tan product equations; sin⁴+cos⁴; grouped ratio = tan 4x |
| Q9–12 | 6 | Fraction identity; complex roots; cos product; inverse sum |
| Q13–15 | 6 | tan⁻¹ telescoping; sin⁻¹ equation; inverse prove |
| Q16–18 | 6 | Triangle sine rule; equilateral condition; R, r relation |
| Q19 | 6 | **Gold:** evaluate sin²(π/8)+…+sin²(7π/8); Hence Σ sin²(kπ/(2n+1)) |
| Q20 | 8 | sin⁶x+cos⁶x: prove, extrema, period, solve |

## Scaled papers

| Questions | Mapping | Typical marks |
|-----------|---------|---------------|
| 20 | Full reference Q1–Q20 | 122 |
| 10 | Ref slots 1,3,5,7,9,12,14,17,19,20 | ~62 |
| 5 | Ref slots 1,5,9,13,20 | ~32 |

## Depth rules

- Multi-step proof (4+ steps) on most slots; **Hence** chains on ≥40% of paper.
- General-solution + interval counting required when n ≥ 8.
- Inverse-trigonometry slot when n ≥ 5.
- Capstone (Q20 style) on last slot when n ≥ 5.

## Bans

- Bare Find cos 30° / one-line standard angle only.
- Identical (i)(ii)(iii) on every question.
- Copying π/7, π/11, 20°+40°+60°+80° with same labels every paper.
- Circle / secant / concentric vocabulary in trigonometry stems.

## Q19 gold stem (copy structure, not numbers)

```
Evaluate exactly:
sin²(π/8) + sin²(3π/8) + sin²(5π/8) + sin²(7π/8)

Hence find the exact value of:
Σ_{k=1}^{n} sin²(kπ/(2n+1))
```

Requires: complementary-angle reduction, sin²→(1−cos 2θ)/2, numeric sum, then generalization.

## Code

- `backend/app/generation/trigonometry_hard_benchmark.py` — slot maps, marks, prompt block
- `backend/app/generation/trigonometry_hard_stem_gate.py` — rejects stems below Q19 quality on full-hard papers
