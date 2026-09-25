"""
Embeds every document in data/docs/ into the Chroma vector store.

Run with:  python -m scripts.ingest_docs
"""
from __future__ import annotations

from src.qualitative.agent import ingest_documents


def main() -> None:
    count = ingest_documents()
    print(f"Ingested {count} chunks into the vector store.")


if __name__ == "__main__":
    main()