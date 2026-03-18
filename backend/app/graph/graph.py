from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.nodes import answer_node, retrieve_node
from app.graph.state import RAGState


def build_graph():
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()
