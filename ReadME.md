# Document RAG / Agent Architecture

## 1. Project goal

Build a small but extensible enterprise-style document assistant for messy internal knowledge.

The first version prioritizes:

* a clean backend architecture
* a working RAG / agent pipeline
* clear service boundaries
* an easy path to later add parsing, OCR, vector DB, and cloud deployment

The initial version does **not** prioritize:

* production-grade auth
* full database modeling
* full OCR pipeline
* polished frontend
* AWS deployment in v1

---

## 2. Final target architecture

```text
[Frontend: Next.js / React]
        |
        | HTTP/JSON
        v
[Backend API: FastAPI]
        |
        | calls
        +----------------------+
        |                      |
        v                      v
[RAG / Agent Service]     [Document Service]
 (LangGraph)              (parse / OCR / ingest)
        |                      |
        | reads/writes         | reads/writes
        v                      v
[Metadata DB: Postgres]   [Raw File Storage]
        |
        | doc/chunk metadata
        v
[Vector Store]
        |
        | retrieval results
        v
[LLM Provider / SDK]
(OpenAI / Anthropic / etc.)
```

---

## 3. v1 implementation scope

### v1 should include

* Next.js / React frontend
* FastAPI backend
* LangGraph-based RAG / agent workflow
* simple file placeholder input (txt first)
* embedding + vector retrieval
* answer with citations
* optional simple metadata persistence

### v1 should NOT include yet

* PDF/PPTX/DOCX parsing
* OCR pipeline
* AWS-specific deployment
* full Postgres schema design
* advanced multi-agent collaboration

---

## 4. Why this order

The core value of the system is not file parsing itself. The core value is:

1. retrieving the right knowledge
2. orchestrating agent / RAG logic cleanly
3. exposing it through a usable API and UI

So the recommended build order is:

1. define architecture
2. build backend skeleton
3. build RAG / agent core with txt placeholder documents
4. expose API
5. build minimal frontend
6. later add document parsing and OCR as a pluggable ingestion layer

This keeps the system modular and avoids getting blocked by messy document handling too early.

---

## 5. Main components

## 5.1 Frontend

Recommended: Next.js

Responsibilities:

* provide chat UI
* optionally upload files later
* show retrieved sources / citations
* show ingestion status later

Core pages:

* `/` chat page
* `/documents` document list page (later)
* `/upload` upload page (later)

Frontend communicates with backend via HTTP/JSON.

---

## 5.2 Backend API

Recommended: FastAPI

Responsibilities:

* expose chat / ask endpoint
* expose ingest endpoint
* expose health/config endpoints
* later expose document management endpoints

Example endpoints:

* `POST /api/ask`
* `POST /api/ingest/text`
* `GET /api/documents`
* `GET /api/health`

FastAPI is still a very reasonable choice here because the core backend need is stable API orchestration, not chasing the newest LLM trend.

---

## 5.3 RAG / Agent Service

Recommended: LangGraph

Responsibilities:

* receive user query
* optionally rewrite / classify query
* retrieve relevant chunks
* assemble context
* call LLM
* return grounded answer with citations

Initial graph can be simple:

```text
User Query
   |
   v
Query Router / Normalizer
   |
   v
Retriever
   |
   v
Answer Generator
   |
   v
Response Formatter
```

Later extensions:

* fallback retrieval
* summary mode vs factual mode
* document search mode
* follow-up question handling

---

## 5.4 Document Service

In v1, this is a placeholder ingestion layer.

Responsibilities in v1:

* accept txt documents
* chunk them
* attach metadata
* send embeddings to vector store

Responsibilities in v2:

* parse PDF/PPTX/DOCX
* OCR on images/scanned PDFs
* standardize extracted text
* incremental indexing

Important design rule:
The RAG / Agent layer should **not** depend on document format specifics.
All documents should be normalized into a unified chunk format before retrieval.

---

## 5.5 Vector Store

Options:

* FAISS (best for local prototype)
* Chroma
* pgvector later if Postgres is used heavily

Responsibilities:

* store embeddings
* retrieve top-k chunks

For v1, FAISS is enough.

---

## 5.6 Metadata DB

Recommended later: Postgres

But for v1, can be postponed.

Temporary v1 options:

* JSON / JSONL metadata files
* SQLite

Why postpone Postgres:

* metadata schema depends on ingestion behavior
* retrieval core can be built first without full relational modeling
* avoids unnecessary complexity early

---

## 5.7 LLM layer

Use provider SDK directly or through a thin wrapper.

Suggested abstraction:

* `llm_client.py`
* backend does not directly depend on a single provider everywhere

Responsibilities:

* generate answer
* later possibly support summarization or structured output

Important note:
This is the part most likely to change fast.
So isolate SDK/provider logic behind a small adapter interface.

---

## 6. Communication flow

## 6.1 Ask flow

```text
User types question in Next.js UI
    -> POST /api/ask
    -> FastAPI receives query
    -> FastAPI calls LangGraph workflow
    -> LangGraph retrieves chunks from vector store
    -> LangGraph calls LLM provider
    -> LangGraph returns answer + citations
    -> FastAPI returns JSON
    -> Frontend renders answer + sources
```

### Example response JSON

```json
{
  "answer": "Project Orion focused on internal knowledge retrieval and source-grounded QA.",
  "citations": [
    {
      "doc_id": "orion_proposal",
      "source": "orion_proposal.txt",
      "chunk_id": "chunk_03"
    }
  ]
}
```

---

## 6.2 Ingest flow (v1 txt)

```text
Developer places txt file / uploads txt file
    -> POST /api/ingest/text
    -> Backend normalizes document
    -> chunking
    -> embedding
    -> write to vector store
    -> save metadata
```

---

## 6.3 Future ingest flow (v2 docs + OCR)

```text
User uploads PDF/PPTX/DOCX/image
    -> FastAPI upload endpoint
    -> Document Service detects file type
    -> parse text or call OCR
    -> normalize pages/sections into chunks
    -> embedding
    -> write vector store
    -> save metadata to Postgres
```

---

## 7. Recommended development order

## Phase 0: architecture and README

* define system boundaries
* define APIs
* define data contracts
* define folder structure

## Phase 1: backend skeleton

* FastAPI app
* config handling
* health endpoint
* ask endpoint placeholder
* ingest txt endpoint placeholder

## Phase 2: RAG / agent core

* build LangGraph flow
* add retriever
* add LLM call
* return answer + citations
* use txt files only

## Phase 3: local vector store and metadata

* use FAISS or Chroma
* use JSON/SQLite for metadata temporarily

## Phase 4: minimal frontend

* Next.js chat page
* call `/api/ask`
* show response and citations

## Phase 5: ingestion upgrade

* add PDF parser
* add DOCX parser
* add PPTX parser
* add OCR module

## Phase 6: persistence upgrade

* migrate metadata to Postgres
* optionally move vector storage to pgvector or managed vector DB

## Phase 7: cloud / AWS alignment

* S3 for files
* RDS Postgres
* managed vector solution or pgvector
* ECS/Lambda deployment depending on architecture

---

## 8. Folder structure

```text
enterprise-doc-rag/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── graph/
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── services/
│   │   ├── models/
│   │   └── utils/
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   └── vectorstore/
│   ├── tests/
│   └── main.py
├── frontend/
│   ├── app/
│   ├── components/
│   └── lib/
├── docs/
│   └── architecture.md
└── README.md
```

---

## 9. Core design decisions

### Decision 1

Use stable web stack for frontend/backend:

* Next.js / React
* FastAPI

### Decision 2

Treat LangGraph as the evolving orchestration layer.
Do not tightly couple the whole system to one provider SDK.

### Decision 3

Build RAG with txt placeholders first.
Do not let OCR/parsing complexity block core retrieval design.

### Decision 4

Postpone Postgres until the ingestion and metadata shape become clearer.

### Decision 5

Keep communication contracts simple and explicit through JSON APIs.

---

## 10. Immediate next step

The immediate next build step should be:

### Step 1

Create backend skeleton and define these endpoints:

* `GET /api/health`
* `POST /api/ingest/text`
* `POST /api/ask`

### Step 2

Create a simple LangGraph-based RAG flow using txt documents only.

### Step 3

Confirm the response contract between frontend and backend.

Only after that should document parsing / OCR be added.

---

## 11. One-sentence summary

Build a stable web architecture first, put LangGraph-based RAG at the center, use txt documents as placeholders, and treat parsing/OCR/database as modular upgrades rather than blockers.
