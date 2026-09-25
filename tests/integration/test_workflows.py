"""
Integration tests exercising the full Manager -> Agent(s) -> DB/VectorStore
pipeline with the LLM calls mocked (no real network access), but everything
else (SQLite execution, Chroma retrieval, chunking) running for real.
"""
from __future__ import annotations

import json

from src.manager import agent as manager_agent
from src.qualitative import agent as qualitative_agent
from src.quantitative import agent as quantitative_agent
from tests.conftest import fake_embed_text


def _classify_json(route: str, confidence: float = 0.9):
    return json.dumps(
        {"route": route, "confidence": confidence, "reasoning": "t", "clarification_question": None}
    )


def test_full_quantitative_workflow(temp_sqlite_db, monkeypatch):
    monkeypatch.setattr(
        manager_agent, "generate_text", lambda prompt, temperature=0.0: _classify_json("quantitative")
    )
    monkeypatch.setattr(
        quantitative_agent,
        "generate_sql",
        lambda question, schema: "SELECT COUNT(*) AS region_count FROM regions",
    )

    response = manager_agent.handle_query("How many regions do we operate in?")

    assert response.route.value == "quantitative"
    assert "region_count" in response.answer
    assert "4" in response.answer  # 4 seeded regions


def test_full_qualitative_workflow(temp_docs_dir, temp_chroma_dir, monkeypatch):
    monkeypatch.setattr("src.llm_client.embed_text", fake_embed_text)
    monkeypatch.setattr(qualitative_agent, "generate_text", lambda prompt, temperature=0.1: "PTO accrues at 1.5 days/month.")
    monkeypatch.setattr(qualitative_agent.settings, "rag_relevance_threshold", 0.05)
    qualitative_agent.ingest_documents(temp_docs_dir)

    monkeypatch.setattr(
        manager_agent, "generate_text", lambda prompt, temperature=0.0: _classify_json("qualitative")
    )

    response = manager_agent.handle_query("What is our PTO accrual policy?")

    assert response.route.value == "qualitative"
    assert "PTO accrues" in response.answer
    assert "Sources:" in response.answer


def test_full_complex_multiagent_workflow(temp_sqlite_db, temp_docs_dir, temp_chroma_dir, monkeypatch):
    monkeypatch.setattr("src.llm_client.embed_text", fake_embed_text)
    monkeypatch.setattr(qualitative_agent.settings, "rag_relevance_threshold", 0.05)
    qualitative_agent.ingest_documents(temp_docs_dir)

    monkeypatch.setattr(
        manager_agent, "generate_text", lambda prompt, temperature=0.0: _classify_json("both")
    )
    monkeypatch.setattr(
        qualitative_agent, "generate_text", lambda prompt, temperature=0.1: "Security requires MFA."
    )
    monkeypatch.setattr(
        quantitative_agent,
        "generate_sql",
        lambda question, schema: "SELECT COUNT(*) AS customer_count FROM customers",
    )
    monkeypatch.setattr(
        manager_agent, "_merge_answers", lambda q, a, b: f"From documentation: {a}\nFrom data: {b}"
    )

    response = manager_agent.handle_query(
        "What does our security policy require, and how many customers do we have?"
    )

    assert response.route.value == "both"
    assert "From documentation" in response.answer
    assert "From data" in response.answer
    assert "qualitative" in response.agent_outputs
    assert "quantitative" in response.agent_outputs


def test_unsupported_query_gets_clarification(monkeypatch):
    monkeypatch.setattr(
        manager_agent,
        "generate_text",
        lambda prompt, temperature=0.0: json.dumps(
            {
                "route": "unclear",
                "confidence": 0.2,
                "reasoning": "too vague",
                "clarification_question": "Can you be more specific?",
            }
        ),
    )

    response = manager_agent.handle_query("hi")

    assert response.needs_clarification
    assert "specific" in response.answer.lower()
