from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8000"


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _load_questions(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help="API base URL, default http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--questions",
        default=str(Path(__file__).with_name("regression_questions.json")),
        help="Path to regression_questions.json",
    )
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between calls")
    args = parser.parse_args()

    questions = _load_questions(Path(args.questions))
    if not questions:
        print("No questions found.")
        return 1

    for item in questions:
        qid = item.get("id", "unknown")
        question = item.get("question", "").strip()
        if not question:
            print(f"[{qid}] skipped (empty question)")
            continue

        try:
            result = _post_json(f"{args.base}/api/ask", {"question": question})
        except Exception as exc:
            print(f"[{qid}] ERROR: {exc}")
            continue

        answer = result.get("answer", "")
        citations = result.get("citations", [])
        llm_mode = result.get("llm_mode", "unknown")
        print(f"\n=== {qid} ===")
        print(f"Q: {question}")
        print(f"LLM: {llm_mode}")
        print("A:")
        print(answer)
        print("Citations:")
        for c in citations:
            source = c.get("source", "")
            chunk = c.get("chunk_id", "")
            print(f"- {source} :: {chunk}")

        time.sleep(args.sleep)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
