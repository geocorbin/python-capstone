"""
Connection-level integration tests: confirm the SQLite DB build produces a
usable, queryable database, and that the LLM client wraps the SDK the way
the rest of the app expects (mocking the actual network call).
"""
from __future__ import annotations

import sqlite3

import pytest

from scripts.init_db import build_database
from src import llm_client


def test_sqlite_db_builds_and_is_queryable(tmp_path):
    db_path = tmp_path / "test.db"
    build_database(db_path)

    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"regions", "customers", "products", "sales", "employee_satisfaction"} <= tables

        (count,) = conn.execute("SELECT COUNT(*) FROM sales").fetchone()
        assert count > 0

        (region_count,) = conn.execute("SELECT COUNT(*) FROM regions").fetchone()
        assert region_count == 4
    finally:
        conn.close()


def test_generate_text_calls_sdk_and_returns_text(monkeypatch):
    class FakeResponse:
        text = "  hello from gemini  "

    class FakeModels:
        def generate_content(self, model, contents, config):
            assert model  # a model name was passed
            assert contents == "hi"
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(llm_client, "_client", FakeClient())

    result = llm_client.generate_text("hi")
    assert result == "hello from gemini"


def test_embed_text_calls_sdk_once_per_text_and_returns_vectors(monkeypatch):
    # gemini-embedding-001 only supports one input per request on some API
    # surfaces, so embed_text() calls the SDK once per text rather than
    # batching -- this test locks in that behavior.
    class FakeEmbedding:
        def __init__(self, values):
            self.values = values

    calls = []

    class FakeModels:
        def embed_content(self, model, contents, config):
            calls.append(contents)
            vector = [0.1, 0.2] if contents == "a" else [0.3, 0.4]

            class FakeEmbedResult:
                embeddings = [FakeEmbedding(vector)]

            return FakeEmbedResult()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(llm_client, "_client", FakeClient())

    vectors = llm_client.embed_text(["a", "b"])
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert calls == ["a", "b"]  # one call per text, not one batched call


def test_generate_text_raises_clear_error_without_api_key(monkeypatch):
    from src.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(llm_client, "_client", None)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        llm_client.generate_text("hi")