from __future__ import annotations

from pathlib import Path

from app.graph.state import RAGState
from app.llm.claude import generate_answer
from app.retrieval.local_txt import retrieve_docs

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def retrieve_node(state: RAGState) -> RAGState:
    question = state["question"]
    docs = retrieve_docs(question, corpus_dir=CORPUS_DIR)
    return {**state, "docs": docs}


def answer_node(state: RAGState) -> RAGState:
    question = state["question"]
    docs = state.get("docs", [])
    answer = generate_answer(question, docs)
    return {**state, "answer": answer}
