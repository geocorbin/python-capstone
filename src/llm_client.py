"""
Thin wrapper around Google's current `google-genai` SDK.

Keeping all direct SDK calls in one place makes it easy to (a) mock in unit
tests, and (b) swap providers later without touching agent logic.
"""
from __future__ import annotations

from typing import Sequence

from google import genai
from google.genai import types

from src.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.require_api_key())
    return _client


def generate_text(prompt: str, *, system_instruction: str | None = None,
                   temperature: float = 0.2) -> str:
    """Send a single-turn prompt to the configured Gemini LLM and return text.

    NOTE on `temperature`: as of the Gemini 3.6/3.8 Flash generation, Google
    deprecated the temperature/top_p/top_k sampling parameters, and its own
    migration guidance for gemini-3.8-flash says to omit them entirely rather
    than pass them (see https://ai.google.dev/gemini-api/docs/latest-model).
    The parameter is kept here for interface stability -- callers still state
    their intent (e.g. temperature=0.0 for the classifier/SQL prompts) -- but
    it is intentionally NOT forwarded to the API. Determinism for those
    prompts instead comes from explicit wording in the prompt text itself,
    which is Google's recommended replacement approach.
    """
    client = _get_client()
    config = types.GenerateContentConfig(system_instruction=system_instruction)
    response = client.models.generate_content(
        model=settings.gemini_llm_model,
        contents=prompt,
        config=config,
    )
    return (response.text or "").strip()


def embed_text(texts: Sequence[str], *, task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed one or more texts using the configured Gemini embedding model.

    Sent one text per request rather than batched: gemini-embedding-001 (the
    current recommended embedding model, replacing the retired
    text-embedding-004) only supports a single input text per request on some
    API surfaces, so per-text calls are the safe default regardless of which
    embedding model is configured.
    """
    client = _get_client()
    config = types.EmbedContentConfig(task_type=task_type)
    embeddings: list[list[float]] = []
    for text in texts:
        result = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text,
            config=config,
        )
        embeddings.append(result.embeddings[0].values)
    return embeddings