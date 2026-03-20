from __future__ import annotations

import time
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.graph import build_graph
from app.llm.claude import has_llm_config
from app.retrieval.chroma_retriever import reset_index

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"
METADATA_PATH = Path(__file__).resolve().parent / "data" / "metadata.json"

app = FastAPI(title="Document RAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_GRAPH = build_graph()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[dict]
    llm_mode: str


class IngestTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: Optional[str] = Field(
        default=None, description="Optional filename (without path)."
    )


class IngestTextResponse(BaseModel):
    source: str
    chunks: int
    status: str


class DocumentItem(BaseModel):
    source: str
    size_bytes: int
    modified_at: str
    chunk_count: int
    content_hash: str
    ingested_at: str


class DocumentsResponse(BaseModel):
    documents: list[DocumentItem]



def _load_metadata() -> dict:
    if not METADATA_PATH.exists():
        return {}
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_metadata(data: dict) -> None:
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")



def _to_iso(ts: float) -> str:
    if not ts:
        return ""
    return datetime.utcfromtimestamp(float(ts)).isoformat() + "Z"




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

    llm_mode = "claude" if has_llm_config() else "stub"
    return AskResponse(
        query=result.get("query", question),
        answer=result.get("answer", ""),
        citations=result.get("citations", []),
        llm_mode=llm_mode,
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

    chunks = max(1, (len(text) + 499) // 500)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    ingested_at = time.time()

    metadata = _load_metadata()
    metadata[filename] = {
        "source": filename,
        "size_bytes": file_path.stat().st_size,
        "modified_at": _to_iso(file_path.stat().st_mtime),
        "chunk_count": chunks,
        "content_hash": content_hash,
        "ingested_at": _to_iso(ingested_at),
    }
    _save_metadata(metadata)

    reset_index()

    return IngestTextResponse(source=filename, chunks=chunks, status="ok")


@app.get("/api/documents", response_model=DocumentsResponse)
def list_documents() -> DocumentsResponse:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    metadata = _load_metadata()
    documents: list[DocumentItem] = []
    for path in sorted(RAW_DIR.glob("*.txt")):
        if not path.is_file():
            continue
        stat = path.stat()
        meta = metadata.get(path.name, {})
        documents.append(
            DocumentItem(
                source=path.name,
                size_bytes=stat.st_size,
                modified_at=_to_iso(stat.st_mtime),
                chunk_count=int(meta.get("chunk_count", 0)),
                content_hash=str(meta.get("content_hash", "")),
                ingested_at=str(meta.get("ingested_at", "")),
            )
        )
    return DocumentsResponse(documents=documents)
