from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.nodes import agent_node, format_citations_node, rewrite_node, tools_node
from app.graph.state import RAGState

MAX_RETRIEVALS = 2


def build_graph():
    graph = StateGraph(RAGState)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("format", format_citations_node)

    graph.set_entry_point("rewrite")
    graph.add_edge("rewrite", "agent")

    def route_after_agent(state: RAGState) -> str:
        if state.get("next_action") == "tool" and state.get("attempt", 0) < MAX_RETRIEVALS:
            return "tools"
        return "format"

    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "format": "format"},
    )

    graph.add_edge("tools", "agent")
    graph.add_edge("format", END)

    return graph.compile()
