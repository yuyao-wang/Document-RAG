from __future__ import annotations

import json

from app.graph.state import RAGState
from app.graph.tools import RETRIEVE_DOCS_TOOL, retrieve_docs_tool
from app.llm.claude import (
    call_llm_with_tools,
    generate_answer,
    has_llm_config,
    rewrite_query,
)


def _format_context_for_llm(docs) -> str:
    blocks = []
    for d in docs:
        blocks.append(f"[source: {d.source} | chunk: {d.chunk_id}]\n{d.text}")
    return "\n\n".join(blocks)


def rewrite_node(state: RAGState) -> RAGState:
    question = state["question"]
    rewritten = rewrite_query(question)
    return {**state, "query": rewritten}


def agent_node(state: RAGState) -> RAGState:
    question = state["question"]
    query = state.get("query", question)
    docs = state.get("docs", [])
    messages = state.get("messages", [])

    if not messages:
        messages = [{"role": "user", "content": query}]

    if not docs and state.get("attempt", 0) == 0:
        return {
            **state,
            "messages": messages,
            "next_action": "tool",
            "tool_input": {"query": query, "top_k": 4},
        }

    if not has_llm_config():
        if not docs:
            return {
                **state,
                "messages": messages,
                "next_action": "tool",
                "tool_input": {"query": query, "top_k": 4, "tool_use_id": "stub"},
            }
        answer = generate_answer(question, docs)
        return {**state, "messages": messages, "next_action": "final", "answer": answer}

    # If we already retrieved docs (prefetch), inject context for the LLM.
    if docs:
        has_tool_result = False
        for m in messages:
            content = m.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        has_tool_result = True
                        break
            if has_tool_result:
                break
        has_context_msg = any(
            isinstance(m.get("content"), str) and m["content"].startswith("Context:\n")
            for m in messages
        )
        if not has_tool_result and not has_context_msg:
            context_msg = (
                "Use only the following context to answer. If there are multiple meanings, "
                "answer only the meaning supported by the context and do not mention other meanings. "
                "If the context is insufficient, say so plainly.\n\n"
                "Context:\n" + _format_context_for_llm(docs)
            )
            messages = messages + [{"role": "user", "content": context_msg}]

    response = call_llm_with_tools(messages=messages, tools=[RETRIEVE_DOCS_TOOL])
    content = response.content
    messages = messages + [{"role": "assistant", "content": content}]

    tool_use = None
    for block in content:
        block_type = getattr(block, "type", None) or block.get("type")
        if block_type == "tool_use":
            tool_use = block
            break

    if tool_use is not None:
        tool_input = getattr(tool_use, "input", None) or tool_use.get("input", {})
        tool_use_id = getattr(tool_use, "id", None) or tool_use.get("id")
        return {
            **state,
            "messages": messages,
            "next_action": "tool",
            "tool_input": {
                "query": tool_input.get("query", query),
                "top_k": tool_input.get("top_k", 4),
                "tool_use_id": tool_use_id,
            },
        }

    answer_text = ""
    for block in content:
        block_type = getattr(block, "type", None) or block.get("type")
        if block_type == "text":
            answer_text += getattr(block, "text", None) or block.get("text", "")

    answer_text = answer_text.strip()
    if not answer_text:
        if docs:
            answer_text = generate_answer(question, docs)
        else:
            answer_text = "I do not have enough context to answer that yet."

    return {
        **state,
        "messages": messages,
        "next_action": "final",
        "answer": answer_text,
    }


def tools_node(state: RAGState) -> RAGState:
    tool_input = state.get("tool_input", {})
    query = tool_input.get("query", state.get("query", state["question"]))
    top_k = int(tool_input.get("top_k", 4))
    docs = retrieve_docs_tool(query, top_k=top_k)
    attempt = state.get("attempt", 0) + 1

    messages = state.get("messages", [])
    tool_use_id = tool_input.get("tool_use_id")
    if tool_use_id and tool_use_id != "prefetch":
        tool_payload = [
            {
                "source": d.source,
                "chunk_id": d.chunk_id,
                "text": d.text,
                "score": d.score,
            }
            for d in docs
        ]
        tool_result = json.dumps(tool_payload, ensure_ascii=True)
        messages = messages + [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": tool_result,
                    }
                ],
            }
        ]

    return {**state, "docs": docs, "attempt": attempt, "messages": messages}


def format_citations_node(state: RAGState) -> RAGState:
    docs = state.get("docs", [])
    citations = [
        {
            "source": d.source,
            "chunk_id": d.chunk_id,
            "score": d.score,
        }
        for d in docs
    ]
    return {**state, "citations": citations}
