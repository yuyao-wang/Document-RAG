from __future__ import annotations

from pathlib import Path
from typing import List

from app.retrieval.local_txt import RetrievedChunk, retrieve_docs

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def retrieve_docs_tool(query: str) -> List[RetrievedChunk]:
    """Tool: retrieve_docs

    Args:
        query: user question

    Returns:
        Top-k retrieved chunks from local txt corpus.
    """
    return retrieve_docs(query, corpus_dir=CORPUS_DIR)
