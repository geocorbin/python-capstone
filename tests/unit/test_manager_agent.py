from __future__ import annotations

import json

from src.manager import agent as manager_agent
from src.manager.agent import Route
from src.qualitative.agent import QualitativeResult
from src.quantitative.agent import QuantitativeResult


def _fake_classify_response(route: str, confidence: float = 0.9, clarification=None):
    return json.dumps(
        {
            "route": route,
            "confidence": confidence,
            "reasoning": "test",
            "clarification_question": clarification,
        }
    )


def test_classify_parses_valid_json(monkeypatch):
    monkeypatch.setattr(
        manager_agent, "generate_text", lambda prompt, temperature=0.0: _fake_classify_response("qualitative")
    )
    result = manager_agent.classify("What is our PTO policy?")
    assert result.route == Route.QUALITATIVE
    assert result.confidence == 0.9


def test_classify_handles_malformed_json_as_unclear(monkeypatch):
    monkeypatch.setattr(
        manager_agent, "generate_text", lambda prompt, temperature=0.0: "not json at all"
    )
    result = manager_agent.classify("asdkjhaskjdh")
    assert result.route == Route.UNCLEAR
    assert result.clarification_question is not None


def test_handle_query_routes_to_qualitative(monkeypatch):
    monkeypatch.setattr(
        manager_agent, "generate_text", lambda prompt, temperature=0.0: _fake_classify_response("qualitative")
    )
    fake_result = QualitativeResult(
        question="q", answer="the answer", sources=[], below_threshold=False
    )
    monkeypatch.setattr(
        manager_agent.qualitative_agent, "answer_question", lambda q: fake_result
    )

    response = manager_agent.handle_query("What is our PTO policy?")

    assert response.route == Route.QUALITATIVE
    assert "the answer" in response.answer
    assert not response.needs_clarification


def test_handle_query_routes_to_quantitative(monkeypatch):
    monkeypatch.setattr(
        manager_agent, "generate_text", lambda prompt, temperature=0.0: _fake_classify_response("quantitative")
    )
    fake_result = QuantitativeResult(
        question="q", sql="SELECT 1", columns=["x"], rows=[(1,)], row_count=1
    )
    monkeypatch.setattr(
        manager_agent.quantitative_agent, "answer_question", lambda q: fake_result
    )

    response = manager_agent.handle_query("What is our monthly revenue?")

    assert response.route == Route.QUANTITATIVE
    assert "SELECT 1" in response.answer


def test_handle_query_asks_for_clarification_on_low_confidence(monkeypatch):
    monkeypatch.setattr(
        manager_agent,
        "generate_text",
        lambda prompt, temperature=0.0: _fake_classify_response("qualitative", confidence=0.1),
    )

    response = manager_agent.handle_query("tell me stuff")

    assert response.needs_clarification is True
    assert response.route == Route.UNCLEAR


def test_handle_query_merges_both_agents(monkeypatch):
    monkeypatch.setattr(
        manager_agent, "generate_text", lambda prompt, temperature=0.0: _fake_classify_response("both")
    )
    qual_result = QualitativeResult(question="q", answer="policy says X", sources=[])
    quant_result = QuantitativeResult(
        question="q", sql="SELECT 2", columns=["y"], rows=[(2,)], row_count=1
    )
    monkeypatch.setattr(manager_agent.qualitative_agent, "answer_question", lambda q: qual_result)
    monkeypatch.setattr(manager_agent.quantitative_agent, "answer_question", lambda q: quant_result)
    monkeypatch.setattr(manager_agent, "_merge_answers", lambda q, a, b: "MERGED ANSWER")

    response = manager_agent.handle_query("compare policy and data")

    assert response.route == Route.BOTH
    assert response.answer == "MERGED ANSWER"
    assert "qualitative" in response.agent_outputs
    assert "quantitative" in response.agent_outputs


def test_handle_query_treats_low_route_specific_confidence_as_unclear(monkeypatch):
    # Even a "both" route with confidence below threshold should ask for clarification
    monkeypatch.setattr(
        manager_agent,
        "generate_text",
        lambda prompt, temperature=0.0: _fake_classify_response("both", confidence=0.05),
    )
    response = manager_agent.handle_query("ambiguous")
    assert response.needs_clarification