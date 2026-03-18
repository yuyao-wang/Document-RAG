from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


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


def _tokenize(text: str) -> List[str]:
    cleaned = []
    for ch in text.lower():
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    return [t for t in "".join(cleaned).split() if t]


def _score_chunk(query: str, chunk: str) -> float:
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return 0.0
    c_tokens = set(_tokenize(chunk))
    overlap = q_tokens.intersection(c_tokens)
    return float(len(overlap))


def retrieve_docs(
    query: str,
    corpus_dir: str | Path,
    top_k: int = 4,
) -> List[RetrievedChunk]:
    corpus_path = Path(corpus_dir)
    results: List[RetrievedChunk] = []

    for file_path in _iter_txt_files(corpus_path):
        text = file_path.read_text(encoding="utf-8")
        chunks = _chunk_text(text)
        for idx, chunk in enumerate(chunks):
            score = _score_chunk(query, chunk)
            if score <= 0:
                continue
            results.append(
                RetrievedChunk(
                    text=chunk,
                    source=file_path.name,
                    chunk_id=f"{file_path.stem}_chunk_{idx:02d}",
                    score=score,
                )
            )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]
