from __future__ import annotations

import json
import sys

from app.graph import build_graph


def main() -> int:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "What is Project Orion?"

    graph = build_graph()
    result = graph.invoke({"question": question})

    output = {
        "answer": result.get("answer", ""),
        "citations": [
            {
                "source": d.source,
                "chunk_id": d.chunk_id,
                "score": d.score,
            }
            for d in result.get("docs", [])
        ],
    }

    print(json.dumps(output, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
