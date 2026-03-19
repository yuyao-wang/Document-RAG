from __future__ import annotations

from typing import List, TypedDict

from app.retrieval.chroma_retriever import RetrievedChunk


class RAGState(TypedDict):
    question: str
    query: str
    docs: List[RetrievedChunk]
    answer: str
    citations: List[dict]
    messages: List[dict]
    tool_input: dict
    next_action: str
    attempt: int
