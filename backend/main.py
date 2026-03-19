from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.graph import build_graph
from app.retrieval.chroma_retriever import reset_index

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"

app = FastAPI(title="Document RAG API", version="0.1.0")
_GRAPH = build_graph()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[dict]


class IngestTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: Optional[str] = Field(
        default=None, description="Optional filename (without path)."
    )


class IngestTextResponse(BaseModel):
    source: str
    chunks: int
    status: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    result = _GRAPH.invoke(
        {"question": question, "attempt": 0, "messages": [], "query": question}
    )

    return AskResponse(
        query=result.get("query", question),
        answer=result.get("answer", ""),
        citations=result.get("citations", []),
    )


@app.post("/api/ingest/text", response_model=IngestTextResponse)
def ingest_text(request: IngestTextRequest) -> IngestTextResponse:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if request.source:
        filename = Path(request.source).name
        if not filename.endswith(".txt"):
            filename = f"{filename}.txt"
    else:
        filename = f"ingest_{int(time.time())}.txt"

    file_path = RAW_DIR / filename
    file_path.write_text(text, encoding="utf-8")

    reset_index()

    chunks = max(1, (len(text) + 499) // 500)
    return IngestTextResponse(source=filename, chunks=chunks, status="ok")
