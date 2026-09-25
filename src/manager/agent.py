"""
Manager Agent: classifies incoming queries, routes them to the Qualitative
and/or Quantitative agents, merges multi-agent responses, and asks a
clarifying question when a query is too ambiguous to route confidently.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.llm_client import generate_text
from src.logging_config import Timer, get_logger, log_event
from src.qualitative import agent as qualitative_agent
from src.quantitative import agent as quantitative_agent

logger = get_logger(__name__)

_CONFIDENCE_THRESHOLD = 0.45

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


class Route(str, Enum):
    QUALITATIVE = "qualitative"
    QUANTITATIVE = "quantitative"
    BOTH = "both"
    UNCLEAR = "unclear"


@dataclass
class Classification:
    route: Route
    confidence: float
    reasoning: str
    clarification_question: str | None = None


@dataclass
class ManagerResponse:
    question: str
    route: Route
    answer: str
    needs_clarification: bool = False
    agent_outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


_CLASSIFY_PROMPT = """You are the routing component of a multi-agent enterprise assistant. You
must classify the user's question into exactly one route:

- "qualitative": the question is about policies, processes, documentation, or other text-based
  knowledge (e.g., "what is our PTO policy", "how do we handle a security incident").
- "quantitative": the question is about numeric/tabular business data (e.g., "revenue by region",
  "how many customers signed up in 2024", "average satisfaction score").
- "both": the question genuinely needs information from both documentation AND data to answer
  (e.g., "how does our sales performance compare to what our customer success policy promises").
- "unclear": the question is too vague, off-topic, or ambiguous to route confidently (e.g., "tell
  me about the company", a one-word query, or something with no clear informational need).

Be deterministic: given the same question, always return the same classification.

Respond with ONLY a JSON object, no markdown fences, no explanation outside the JSON, in this
exact shape:
{{
  "route": "qualitative" | "quantitative" | "both" | "unclear",
  "confidence": <float between 0 and 1>,
  "reasoning": "<one short sentence>",
  "clarification_question": "<a question to ask the user, or null if route is not unclear>"
}}

User question: {question}
"""


def _extract_json(raw_text: str) -> dict[str, Any]:
    match = _JSON_FENCE_RE.search(raw_text)
    payload = match.group(1) if match else raw_text
    return json.loads(payload.strip())


def classify(question: str) -> Classification:
    prompt = _CLASSIFY_PROMPT.format(question=question)
    raw = generate_text(prompt, temperature=0.0)
    try:
        data = _extract_json(raw)
        route = Route(data.get("route", "unclear"))
        confidence = float(data.get("confidence", 0.0))
        reasoning = str(data.get("reasoning", ""))
        clarification = data.get("clarification_question")
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        log_event(logger, "warning", "classification_parse_failed", raw=raw, error=str(exc))
        route = Route.UNCLEAR
        confidence = 0.0
        reasoning = "Could not parse classifier output."
        clarification = (
            "I had trouble understanding that question — could you rephrase it or be more "
            "specific about whether you're asking about a policy/process or about data/numbers?"
        )

    if route == Route.UNCLEAR and not clarification:
        clarification = (
            "Could you clarify your question? For example, are you asking about a company "
            "policy or process, or about specific data/numbers?"
        )

    return Classification(
        route=route,
        confidence=confidence,
        reasoning=reasoning,
        clarification_question=clarification,
    )


def _merge_answers(question: str, qual_text: str, quant_text: str) -> str:
    prompt = f"""Combine the two agent answers below into a single, clearly labeled response to
the user's original question. Use headers "From documentation:" and "From data:" so it's clear
which agent contributed which part. Keep it concise; do not repeat information unnecessarily.

Original question: {question}

Documentation agent answer:
{qual_text}

Data agent answer:
{quant_text}

Combined answer:"""
    return generate_text(prompt, temperature=0.2)


def handle_query(question: str) -> ManagerResponse:
    log_event(logger, "info", "manager_query_received", question=question)

    with Timer(logger, "manager_query_handled", question=question) as timer:
        classification = classify(question)
        log_event(
            logger,
            "info",
            "manager_classified",
            question=question,
            route=classification.route.value,
            confidence=classification.confidence,
        )

        if classification.route == Route.UNCLEAR or classification.confidence < _CONFIDENCE_THRESHOLD:
            response = ManagerResponse(
                question=question,
                route=Route.UNCLEAR,
                answer=classification.clarification_question or "Could you clarify your question?",
                needs_clarification=True,
                metadata={"classification": classification.__dict__},
            )

        elif classification.route == Route.QUALITATIVE:
            result = qualitative_agent.answer_question(question)
            response = ManagerResponse(
                question=question,
                route=Route.QUALITATIVE,
                answer=qualitative_agent.format_result(result),
                agent_outputs={"qualitative": result},
                metadata={"classification": classification.__dict__},
            )

        elif classification.route == Route.QUANTITATIVE:
            result = quantitative_agent.answer_question(question)
            response = ManagerResponse(
                question=question,
                route=Route.QUANTITATIVE,
                answer=quantitative_agent.format_result(result),
                agent_outputs={"quantitative": result},
                metadata={"classification": classification.__dict__},
            )

        else:  # BOTH
            qual_result = qualitative_agent.answer_question(question)
            quant_result = quantitative_agent.answer_question(question)
            merged = _merge_answers(
                question,
                qualitative_agent.format_result(qual_result),
                quantitative_agent.format_result(quant_result),
            )
            response = ManagerResponse(
                question=question,
                route=Route.BOTH,
                answer=merged,
                agent_outputs={"qualitative": qual_result, "quantitative": quant_result},
                metadata={"classification": classification.__dict__},
            )

    response.metadata["duration_ms"] = timer.duration_ms
    return response