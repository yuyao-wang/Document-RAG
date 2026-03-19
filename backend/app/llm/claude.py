from __future__ import annotations

import os
import json
from typing import List

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - optional dependency
    Anthropic = None

from app.retrieval.chroma_retriever import RetrievedChunk


SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the provided context to answer. "
    "If the context is insufficient, say so plainly."
)
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _format_context(docs: List[RetrievedChunk]) -> str:
    if not docs:
        return ""
    blocks = []
    for d in docs:
        blocks.append(
            f"[source: {d.source} | chunk: {d.chunk_id}]\n{d.text}"
        )
    return "\n\n".join(blocks)


def has_llm_config() -> bool:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    return bool(api_key and Anthropic is not None)


def generate_answer(question: str, docs: List[RetrievedChunk]) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    context = _format_context(docs)

    if not api_key or Anthropic is None:
        if not context:
            return "I do not have enough context to answer that yet."
        return (
            "(stub) Based on the context, here is a grounded answer:\n"
            f"Question: {question}\n\nContext:\n{context}"
        )

    client = Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    user_prompt = (
        "Answer the question using only the context. Provide a concise answer.\n\n"
        f"Question: {question}\n\nContext:\n{context}"
    )

    message = client.messages.create(
        model=model,
        max_tokens=512,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text


def call_llm_with_tools(messages: List[dict], tools: List[dict]):
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or Anthropic is None:
        raise RuntimeError("Anthropic client not available or API key missing.")

    client = Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    return client.messages.create(
        model=model,
        max_tokens=512,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )


def rewrite_query(question: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or Anthropic is None:
        return question.strip()

    client = Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    user_prompt = (
        "Rewrite the user question into a clear, retrieval-friendly search query. "
        "Return only the rewritten query text.\n\n"
        f"Question: {question}"
    )

    message = client.messages.create(
        model=model,
        max_tokens=64,
        temperature=0.1,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text.strip() or question.strip()
