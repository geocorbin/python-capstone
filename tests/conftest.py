from __future__ import annotations

from pathlib import Path

import pytest

from scripts.init_db import build_database
from src.config import settings


@pytest.fixture()
def temp_sqlite_db(tmp_path: Path, monkeypatch) -> Path:
    """Build a fresh sample SQLite DB in a temp dir and point settings at it."""
    db_path = tmp_path / "enterprise.db"
    build_database(db_path)
    monkeypatch.setattr(settings, "sqlite_db_path", db_path)
    return db_path


@pytest.fixture()
def temp_docs_dir(tmp_path: Path, monkeypatch) -> Path:
    """A tiny, fast-to-embed set of docs for RAG tests."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "hr_policy.md").write_text(
        "# HR Policy\n\nFull-time employees accrue 1.5 PTO days per month, "
        "capped at 30 banked days. New hires cannot use PTO in their first 60 days.",
        encoding="utf-8",
    )
    (docs_dir / "security_policy.md").write_text(
        "# Security Policy\n\nMulti-factor authentication is mandatory for all systems "
        "containing customer data or source code. Passwords must be 14+ characters.",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "docs_dir", docs_dir)
    return docs_dir


@pytest.fixture()
def temp_chroma_dir(tmp_path: Path, monkeypatch) -> Path:
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(settings, "chroma_persist_dir", chroma_dir)
    return chroma_dir


def fake_embed_text(texts, task_type="retrieval_document"):
    """Deterministic pseudo-embeddings so cosine similarity is meaningful in tests,
    without calling any real embedding API. Buckets text by keyword overlap.
    """
    import hashlib

    vectors = []
    keywords = ["pto", "hire", "security", "password", "authentication", "policy", "employee"]
    for text in texts:
        lowered = text.lower()
        vec = [1.0 if kw in lowered else 0.0 for kw in keywords]
        digest = hashlib.sha256(text.encode()).digest()
        vec += [b / 255.0 for b in digest[:8]]
        vectors.append(vec)
    return vectors