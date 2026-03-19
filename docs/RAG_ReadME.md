# RAG Minimal (LangGraph) - Current Structure

This document describes the current LangGraph RAG implementation and the recent upgrades.

## 1. Current Workflow (Rewrite + Tool-Calling + Citations)

```
START
  ↓
rewrite_query
  ↓
agent (LLM with tools)
  ↓
    ├── tool call retrieve_docs → tools node → agent again
    └── direct answer → format_citations
  ↓
END
```

Why this structure:
- Query rewrite improves retrieval quality.
- The LLM decides when it needs more context.
- Citations are formatted as a stable output contract.

## 2. Folder Layout

```
backend/
├── app/
│   ├── graph/
│   │   ├── graph.py        # LangGraph wiring and routing
│   │   ├── nodes.py        # rewrite / agent / tools / format
│   │   ├── state.py        # RAGState
│   │   └── tools.py        # retrieve_docs tool spec
│   ├── llm/
│   │   └── claude.py       # Claude wrapper + tool calling
│   └── retrieval/
│       └── chroma_retriever.py  # Chroma vector retrieval
├── data/
│   ├── raw/                # txt corpus for internal DB (stub)
│   └── vectorstore/chroma/ # Chroma persistence
└── main.py                 # CLI runner
```

## 3. State Design

File: `backend/app/graph/state.py`

Fields:
- `question: str` (original)
- `query: str` (rewritten)
- `messages: List[dict]` (Anthropic message format)
- `docs: List[RetrievedChunk]`
- `answer: str`
- `citations: List[dict]`
- `tool_input: dict`
- `next_action: str` (`tool` or `final`)
- `attempt: int` (guards loop, max 2)

## 4. Node Responsibilities

File: `backend/app/graph/nodes.py`

- `rewrite_node`
  - Calls `rewrite_query()` to make a retrieval-friendly query.

- `agent_node`
  - Sends messages to Claude with tool definitions.
  - If Claude requests a tool, returns `next_action = tool`.
  - If Claude answers, returns `next_action = final` and `answer`.

- `tools_node`
  - Executes `retrieve_docs_tool` using Chroma retrieval.
  - Adds a `tool_result` message back into the conversation.
  - Increments `attempt`.

- `format_citations_node`
  - Converts retrieved chunks into a stable citation list.

## 5. Routing Logic

File: `backend/app/graph/graph.py`

Routing rule:
- `rewrite` → `agent`
- If `next_action == tool` and `attempt < 2` → `tools` → `agent`
- Otherwise → `format` → END

## 6. Tool Definition

File: `backend/app/graph/tools.py`

Tool: `retrieve_docs`
- Inputs: `query`, `top_k`
- Returns: top-k chunks from Chroma

The tool spec is passed to Claude via `tools=[...]` in `messages.create`.

## 7. LLM Wrapper

File: `backend/app/llm/claude.py`

- `call_llm_with_tools(messages, tools)`
- `rewrite_query(question)`
- `generate_answer(question, docs)` (stub mode)
- `has_llm_config()` to check key + client

Notes:
- Uses `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` if set.
- If not set, a stub flow is used for local testing.

## 8. Chroma Vector Retrieval (Real Embeddings)

File: `backend/app/retrieval/chroma_retriever.py`

Why not OpenAI embeddings:
- Cost and external dependency. This project uses a local embedding model.

Embedding model:
- `sentence-transformers/all-MiniLM-L6-v2`

Flow:
1. Chunk each txt file into fixed-size chunks.
2. Compute local embeddings with sentence-transformers.
3. Upsert chunks into Chroma.
4. Query Chroma for nearest vectors.
