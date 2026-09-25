from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The natural-language question to answer.")


class SourceSchema(BaseModel):
    doc_id: str
    source_file: str
    similarity: float


class QualitativeResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceSchema]
    below_threshold: bool


class QuantitativeResponse(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    error: str | None = None


class ManagerResponseSchema(BaseModel):
    question: str
    route: str
    answer: str
    needs_clarification: bool


class HealthResponse(BaseModel):
    status: str
    gemini_configured: bool
    sqlite_db_exists: bool
    vector_store_ready: bool