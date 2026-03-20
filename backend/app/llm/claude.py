from __future__ import annotations

import os
import json
from typing import List
import re

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - optional dependency
    Anthropic = None

from app.retrieval.chroma_retriever import RetrievedChunk


SYSTEM_PROMPT = (
    "You are a helpful assistant. Use only the provided context to answer. "
    "Do not use outside knowledge or assumptions. "
    "Do not copy raw context or metadata into the answer. "
    "If the context is insufficient, say so plainly."
)
DEFAULT_MODEL = "claude-sonnet-4-20250514"



def _tokenize(text: str) -> list[str]:
    cleaned = []
    for ch in text.lower():
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    return [t for t in "".join(cleaned).split() if t]


def _best_sentence(question: str, passage: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", passage) if s.strip()]
    if not sentences:
        return passage.strip()
    q_tokens = set(_tokenize(question))
    if not q_tokens:
        return sentences[0]
    best = (0, sentences[0])
    for s in sentences:
        score = len(q_tokens.intersection(_tokenize(s)))
        if score > best[0]:
            best = (score, s)
    return best[1]


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
        if not docs:
            return "I do not have enough context to answer that yet."
        bullets: List[str] = []
        seen = set()
        for doc in docs:
            passage = " ".join(doc.text.strip().split())
            if not passage:
                continue
            snippet = _best_sentence(question, passage)
            snippet = snippet.strip()
            if len(snippet) < 8:
                snippet = passage[:240].strip()
            key = snippet.lower()
            if key in seen:
                continue
            seen.add(key)
            bullets.append(snippet)
            if len(bullets) >= 3:
                break
        if not bullets:
            return "I found relevant sources, but couldn't extract a clean summary."
        return "Based on retrieved sources:\n- " + "\n- ".join(bullets)

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
        tool_choice={"type": "auto"},
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
