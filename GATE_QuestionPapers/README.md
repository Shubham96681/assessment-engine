# GATE Question Papers (reference corpus)

Place official GATE PDFs here (e.g. `GATE_2024_MA_Question_Paper.pdf`, solutions, answer keys).

The assessment engine indexes **question papers and solutions** to:

1. **Quality floors** — `backend/scripts/build_gate_benchmark.py` → `backend/data/gate_benchmark/benchmark.json`
2. **RAG exemplars** — `backend/scripts/build_gate_reference_index.py` → FAISS collection `gate_reference`

## Supported layout

```
GATE_QuestionPapers/
  GATE_2021_MA_Question_Paper.pdf
  GATE_2021_MA_Answer_Key.pdf      (skipped for stem index — keys only)
  GATE_2023_MA_Solutions.pdf
  GATE_2024_MA_Question_Paper.pdf
  ...
```

Subject codes in filenames: `MA` (Maths), `CS`, `PH`, etc.

## Build (from `backend/`)

```bash
python scripts/build_gate_benchmark.py
python scripts/build_gate_reference_index.py
```

Restart the API after adding or replacing PDFs. Generation uses GATE stems when the locked chapter matches (e.g. trigonometry) and raises difficulty floors toward GATE compression.
