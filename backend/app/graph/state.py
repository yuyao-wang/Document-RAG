from __future__ import annotations

from typing import List, TypedDict

from app.retrieval.local_txt import RetrievedChunk


class RAGState(TypedDict):
    question: str
    docs: List[RetrievedChunk]
    answer: str
