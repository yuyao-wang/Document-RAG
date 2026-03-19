from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import chromadb
from sentence_transformers import SentenceTransformer


@dataclass
class RetrievedChunk:
    text: str
    source: str
    chunk_id: str
    score: float


def _iter_txt_files(corpus_dir: Path) -> Iterable[Path]:
    if not corpus_dir.exists():
        return []
    return sorted(p for p in corpus_dir.glob("*.txt") if p.is_file())


def _chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    text = text.strip()
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_EMBEDDER = None


_COLLECTION = None
_INDEXED = False


def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = SentenceTransformer(MODEL_NAME)
    return _EMBEDDER


def _embed_texts(texts: List[str]) -> List[List[float]]:
    model = _get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def _get_collection(vector_dir: Path):
    global _COLLECTION
    if _COLLECTION is None:
        vector_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(vector_dir))
        _COLLECTION = client.get_or_create_collection("rag_docs")
    return _COLLECTION


def _index_corpus(corpus_dir: Path, collection) -> None:
    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for file_path in _iter_txt_files(corpus_dir):
        text = file_path.read_text(encoding="utf-8")
        chunks = _chunk_text(text)
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{file_path.stem}_chunk_{idx:02d}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({"source": file_path.name, "chunk_id": chunk_id})
            embeddings.append(_embed_texts([chunk])[0])

    if ids:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )


def retrieve_docs(
    query: str,
    corpus_dir: str | Path,
    vector_dir: str | Path,
    top_k: int = 4,
) -> List[RetrievedChunk]:
    global _INDEXED
    corpus_path = Path(corpus_dir)
    vector_path = Path(vector_dir)

    collection = _get_collection(vector_path)
    if not _INDEXED:
        _index_corpus(corpus_path, collection)
        _INDEXED = True

    query_emb = _embed_texts([query])[0]
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs: List[RetrievedChunk] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        score = 1.0 / (1.0 + float(dist)) if dist is not None else 0.0
        docs.append(
            RetrievedChunk(
                text=doc,
                source=meta.get("source", ""),
                chunk_id=meta.get("chunk_id", ""),
                score=score,
            )
        )

    return docs
