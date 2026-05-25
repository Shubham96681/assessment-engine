"""Trigger 5-question Groq generation and poll until ready."""
import json
import sys
import time
import urllib.request

API = "http://localhost:8000/api/v1"
config = {
    "locked_chapter": "trigonometry",
    "title": "Groq Demo - 5 Trigonometry Questions",
    "total_questions": 5,
    "question_types": ["MCQ", "ShortAnswer", "LongAnswer"],
    "difficulty_distribution": {"easy": 1, "medium": 2, "hard": 2},
    "bloom_levels": ["Remember", "Understand", "Apply"],
    "topic_focus": "Trigonometry",
    "subject": "Mathematics",
    "class_level": "10",
    "instructions": "Exam level: board_medium",
    "use_chapter_pdf": False,
}


def post_json(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get_json(path: str) -> dict:
    with urllib.request.urlopen(API + path, timeout=90) as r:
        return json.loads(r.read().decode())


def main() -> int:
    out = post_json("/assessments/generate", config)
    aid = out["id"]
    print("created", aid, "status", out.get("status"))
    for i in range(120):
        time.sleep(3)
        a = get_json(f"/assessments/{aid}")
        st = a.get("status")
        nq = len(a.get("questions") or [])
        print(f"poll {i + 1}: status={st} questions={nq}")
        if st in ("ready", "failed"):
            print("DASHBOARD_URL=http://localhost:3000/assessments/" + aid)
            if st == "ready":
                for j, q in enumerate(a.get("questions") or [], 1):
                    stem = (q.get("content") or "")[:90].replace("\n", " ")
                    qtype = q.get("question_type", "")
                    print(f"  Q{j}: [{qtype}] {stem}")
            else:
                print("failed", json.dumps(a.get("generation_log", []))[-800:])
            return 0 if st == "ready" else 1
    print("timeout still generating", aid)
    return 2


if __name__ == "__main__":
    sys.exit(main())
