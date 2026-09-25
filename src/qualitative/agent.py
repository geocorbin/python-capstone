"""
Qualitative Agent: semantic search over enterprise documents using Chroma +
Gemini embeddings, with an LLM generating a cited answer from retrieved
chunks.

Retrieval-quality features (Gold tier):
- Every answer carries source citations with document IDs and similarity scores.
- A minimum relevance threshold filters out weak matches.
- Questions with no relevant chunks return an explicit "not found" response
  instead of a hallucinated answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from src.config import settings
from src.llm_client import generate_text
from src.logging_config import Timer, get_logger, log_event

logger = get_logger(__name__)

COLLECTION_NAME = "enterprise_docs"
_CHUNK_SIZE = 900
_CHUNK_OVERLAP = 150


@dataclass
class Source:
    doc_id: str
    source_file: str
    similarity: float
    text: str


@dataclass
class QualitativeResult:
    question: str
    answer: str
    sources: list[Source]
    below_threshold: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return True  # a "not found" answer is still a valid, non-error result


class GeminiEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Adapts our llm_client embedding call to Chroma's EmbeddingFunction interface."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002 (Chroma's API)
        from src.llm_client import embed_text

        return embed_text(input)

    @staticmethod
    def name() -> str:
        return "gemini_embedding_function"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "GeminiEmbeddingFunction":
        return GeminiEmbeddingFunction()


def _get_client() -> chromadb.ClientAPI:
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_persist_dir))


def _get_collection(client: chromadb.ClientAPI):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=GeminiEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Simple sliding-window chunking on whitespace-normalized text."""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]


def ingest_documents(docs_dir: Path | None = None) -> int:
    """Chunk and embed every .md/.txt file in docs_dir into the Chroma collection.

    Returns the number of chunks ingested. Safe to re-run (clears and rebuilds
    the collection each time so re-ingestion doesn't duplicate chunks).
    """
    docs_dir = docs_dir or settings.docs_dir
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = _get_collection(client)

    ids, texts, metadatas = [], [], []
    for path in sorted(docs_dir.glob("*.md")) + sorted(docs_dir.glob("*.txt")):
        raw = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(_chunk_text(raw)):
            chunk_id = f"{path.stem}::chunk-{i}"
            ids.append(chunk_id)
            texts.append(chunk)
            metadatas.append({"source_file": path.name, "chunk_index": i})

    if not ids:
        log_event(logger, "warning", "no_documents_found", docs_dir=str(docs_dir))
        return 0

    # Chroma/embedding APIs are happier with modest batch sizes.
    batch_size = 16
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i : i + batch_size],
            documents=texts[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    log_event(logger, "info", "documents_ingested", chunk_count=len(ids), docs_dir=str(docs_dir))
    return len(ids)


def retrieve(question: str, top_k: int | None = None) -> list[Source]:
    top_k = top_k or settings.rag_top_k
    client = _get_client()
    collection = _get_collection(client)
    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[question], n_results=top_k)
    sources: list[Source] = []
    ids = results["ids"][0]
    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    for doc_id, doc_text, meta, distance in zip(ids, docs, metadatas, distances):
        # Chroma cosine "distance" -> similarity in [0, 1] (approx; clipped for safety).
        similarity = max(0.0, min(1.0, 1.0 - distance))
        sources.append(
            Source(
                doc_id=doc_id,
                source_file=meta.get("source_file", "unknown"),
                similarity=round(similarity, 4),
                text=doc_text,
            )
        )
    return sources


def _build_prompt(question: str, sources: list[Source]) -> str:
    context_blocks = "\n\n".join(
        f"[Source: {s.doc_id} | similarity={s.similarity}]\n{s.text}" for s in sources
    )
    return f"""You are answering questions about internal enterprise documentation using ONLY
the context provided below. Follow these rules:
- Base your answer strictly on the provided context. Do not use outside knowledge.
- If the context does not contain enough information to answer, say so explicitly rather than
  guessing.
- When you state a fact, mention which source it came from (e.g., "per hr_policy::chunk-1").
- Be concise and directly answer the question.

Context:
{context_blocks}

Question: {question}

Answer:"""


def answer_question(question: str, *, top_k: int | None = None) -> QualitativeResult:
    log_event(logger, "info", "qualitative_query_received", question=question)

    with Timer(logger, "qualitative_query_handled", question=question) as timer:
        sources = retrieve(question, top_k=top_k)
        relevant = [s for s in sources if s.similarity >= settings.rag_relevance_threshold]

        if not relevant:
            answer = (
                "I couldn't find anything in the enterprise documentation that answers this "
                "question with confidence. It may not be covered in the indexed documents, or "
                "it may need to be rephrased."
            )
            result = QualitativeResult(
                question=question, answer=answer, sources=sources, below_threshold=True
            )
        else:
            prompt = _build_prompt(question, relevant)
            answer = generate_text(prompt, temperature=0.1)
            result = QualitativeResult(question=question, answer=answer, sources=relevant)

    result.metadata["duration_ms"] = timer.duration_ms
    log_event(
        logger,
        "info",
        "qualitative_sources_retrieved",
        question=question,
        source_count=len(result.sources),
        below_threshold=result.below_threshold,
    )
    return result


def format_result(result: QualitativeResult) -> str:
    if result.below_threshold or not result.sources:
        return result.answer

    citations = "\n".join(
        f"  - {s.doc_id} (file: {s.source_file}, similarity: {s.similarity})" for s in result.sources
    )
    return f"{result.answer}\n\n_Sources:_\n{citations}"