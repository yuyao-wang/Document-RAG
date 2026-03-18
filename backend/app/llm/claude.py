from __future__ import annotations

import os
from typing import List

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - optional dependency
    Anthropic = None

from app.retrieval.local_txt import RetrievedChunk


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
