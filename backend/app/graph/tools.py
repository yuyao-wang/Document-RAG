from __future__ import annotations

from pathlib import Path
from typing import List

from app.retrieval.chroma_retriever import RetrievedChunk, retrieve_docs

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
VECTOR_DIR = Path(__file__).resolve().parents[2] / "data" / "vectorstore" / "chroma"


def retrieve_docs_tool(query: str, top_k: int = 4) -> List[RetrievedChunk]:
    """Tool: retrieve_docs

    Args:
        query: user question

    Returns:
        Top-k retrieved chunks from local txt corpus.
    """
    return retrieve_docs(query, corpus_dir=CORPUS_DIR, vector_dir=VECTOR_DIR, top_k=top_k)


RETRIEVE_DOCS_TOOL = {
    "name": "retrieve_docs",
    "description": "Retrieve relevant chunks from the internal document store.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 4},
        },
        "required": ["query"],
    },
}
