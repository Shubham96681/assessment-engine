import asyncio
from app.generation.rag_file_bridge import read_rag_response, parse_rag_response
from app.generation.generator import QuestionGenerator
from app.schemas import GenerationConfig
from app.generation.generation_oversample import pool_question_count, score_and_select_best
from app.generation.structural_dedup import filter_structural_duplicates
from app.generation.theorem_variety_engine import filter_theorem_equivalence_duplicates
from app.generation.chapter_paper_quality import validate_all_slots_present

async def main():
    raw = read_rag_response()
    answer, _ = parse_rag_response(raw)
    cfg = GenerationConfig(
        document_id="b0000000-0000-4000-8000-00000000cbse01",
        total_questions=5,
        subject="Mathematics",
        class_level="10",
        topic_focus="Trigonometry",
        question_types=["LongAnswer"],
        difficulty_distribution={"easy": 0, "medium": 25, "hard": 75},
    )
    gen = QuestionGenerator()
    delivery_n = 5
    pool_n = pool_question_count(delivery_n)
    difficulty, bloom = gen._resolve_generation_profile(cfg)
    task = {
        "type": "LongAnswer",
        "difficulty": difficulty,
        "bloom_level": bloom,
        "count": pool_n,
        "delivery_count": delivery_n,
    }
    parsed = gen._parse_llm_output(answer, task, cfg, [])
    parsed = filter_theorem_equivalence_duplicates(
        filter_structural_duplicates(parsed, min_keep=pool_n)
    )
    from app.generation.rd_archetypes import get_slot_bands, get_slot_metadata
    from app.generation.author_styles import resolve_author_style

    slot_bands = get_slot_bands(len(parsed), ui_difficulty=difficulty, difficulty_distribution=cfg.difficulty_distribution)
    slot_meta = get_slot_metadata(
        len(parsed),
        resolve_author_style(instructions=""),
        ui_difficulty=difficulty,
        locked_chapter="trigonometry",
        difficulty_distribution=cfg.difficulty_distribution,
    )
    from app.generation.generation_oversample import select_best_questions

    selected, meta = select_best_questions(
        parsed, delivery_n, quality_gate=None, ui_difficulty=difficulty, chapter="trigonometry"
    )
    ok, issues = validate_all_slots_present(selected, delivery_n)
    lines = [f"parsed={len(parsed)} selected={len(selected)} ok={ok}"]
    for q in selected:
        lines.append(f"slot={q.get('slot_number')} content_len={len(q.get('content') or '')}")
    open("../_test_apply_out.txt", "w", encoding="utf-8").write("\n".join(lines) + "\nissues: " + str(issues))

asyncio.run(main())
