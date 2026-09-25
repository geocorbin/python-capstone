"""
FastAPI application exposing the Manager, Qualitative, and Quantitative
agents as HTTP endpoints, plus a /health check.

Run with:  uvicorn src.api.main:app --reload
Docs at:   http://127.0.0.1:8000/docs  (OpenAPI, auto-generated)
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from src.api.schemas import (
    HealthResponse,
    ManagerResponseSchema,
    QualitativeResponse,
    QuantitativeResponse,
    QueryRequest,
    SourceSchema,
)
from src.config import settings
from src.logging_config import get_logger
from src.manager.agent import handle_query
from src.qualitative import agent as qualitative_agent
from src.quantitative import agent as quantitative_agent

logger = get_logger(__name__)

app = FastAPI(
    title="Northwind Multi-Agent RAG API",
    description="Manager, Qualitative (RAG), and Quantitative (NL-to-SQL) agents over HTTP.",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    vector_store_ready = False
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))
        vector_store_ready = settings.docs_dir.exists() and any(
            c.name == qualitative_agent.COLLECTION_NAME for c in client.list_collections()
        )
    except Exception:
        vector_store_ready = False

    return HealthResponse(
        status="ok",
        gemini_configured=bool(settings.gemini_api_key),
        sqlite_db_exists=settings.sqlite_db_path.exists(),
        vector_store_ready=vector_store_ready,
    )


@app.post("/agents/qualitative", response_model=QualitativeResponse, tags=["agents"])
def query_qualitative(request: QueryRequest) -> QualitativeResponse:
    result = qualitative_agent.answer_question(request.question)
    return QualitativeResponse(
        question=result.question,
        answer=result.answer,
        sources=[
            SourceSchema(doc_id=s.doc_id, source_file=s.source_file, similarity=s.similarity)
            for s in result.sources
        ],
        below_threshold=result.below_threshold,
    )


@app.post("/agents/quantitative", response_model=QuantitativeResponse, tags=["agents"])
def query_quantitative(request: QueryRequest) -> QuantitativeResponse:
    result = quantitative_agent.answer_question(request.question)
    if result.error:
        raise HTTPException(status_code=422, detail=result.error)
    return QuantitativeResponse(
        question=result.question,
        sql=result.sql,
        columns=result.columns,
        rows=[list(row) for row in result.rows],
        row_count=result.row_count,
        error=result.error,
    )


@app.post("/agents/manager", response_model=ManagerResponseSchema, tags=["manager"])
def query_manager(request: QueryRequest) -> ManagerResponseSchema:
    response = handle_query(request.question)
    return ManagerResponseSchema(
        question=response.question,
        route=response.route.value,
        answer=response.answer,
        needs_clarification=response.needs_clarification,
    )