from __future__ import annotations

from src.qualitative import agent as qualitative_agent
from tests.conftest import fake_embed_text


def test_chunk_text_respects_overlap():
    text = "word " * 500
    chunks = qualitative_agent._chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


def test_ingest_and_retrieve(temp_docs_dir, temp_chroma_dir, monkeypatch):
    monkeypatch.setattr("src.llm_client.embed_text", fake_embed_text)

    count = qualitative_agent.ingest_documents(temp_docs_dir)
    assert count >= 2

    sources = qualitative_agent.retrieve("What is the PTO accrual rate?", top_k=2)
    assert len(sources) > 0
    assert any("hr_policy" in s.doc_id for s in sources)
    assert all(0.0 <= s.similarity <= 1.0 for s in sources)


def test_answer_question_returns_not_found_below_threshold(
    temp_docs_dir, temp_chroma_dir, monkeypatch
):
    monkeypatch.setattr("src.llm_client.embed_text", fake_embed_text)
    monkeypatch.setattr(qualitative_agent.settings, "rag_relevance_threshold", 1.1)  # impossible
    qualitative_agent.ingest_documents(temp_docs_dir)

    result = qualitative_agent.answer_question("What is our PTO policy?")

    assert result.below_threshold is True
    assert "couldn't find" in result.answer.lower()


def test_answer_question_generates_cited_answer(temp_docs_dir, temp_chroma_dir, monkeypatch):
    monkeypatch.setattr("src.llm_client.embed_text", fake_embed_text)
    monkeypatch.setattr(qualitative_agent.settings, "rag_relevance_threshold", 0.05)
    monkeypatch.setattr(
        qualitative_agent, "generate_text", lambda prompt, temperature=0.1: "Employees accrue 1.5 PTO days/month (per hr_policy::chunk-0)."
    )
    qualitative_agent.ingest_documents(temp_docs_dir)

    result = qualitative_agent.answer_question("What is our PTO accrual rate?")

    assert result.below_threshold is False
    assert len(result.sources) > 0
    formatted = qualitative_agent.format_result(result)
    assert "Sources:" in formatted
    assert "similarity" in formatted


def test_retrieve_with_empty_collection_returns_empty(temp_docs_dir, temp_chroma_dir):
    # No ingestion has happened yet against this fresh chroma dir.
    sources = qualitative_agent.retrieve("anything")
    assert sources == []