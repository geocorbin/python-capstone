"""
Quantitative Agent: translates a natural-language question into SQL, runs it
against the sample SQLite database, and returns a structured result.

Safety: only SELECT statements are ever executed. Any generated statement
containing a write/DDL keyword is rejected before it touches the database.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import settings
from src.llm_client import generate_text
from src.logging_config import Timer, get_logger, log_event

logger = get_logger(__name__)

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)

_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


class UnsafeSQLError(Exception):
    """Raised when the generated SQL is not a read-only SELECT statement."""


@dataclass
class QuantitativeResult:
    question: str
    sql: str
    columns: list[str]
    rows: list[tuple[Any, ...]]
    row_count: int
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None


def _get_schema_description(db_path: Path) -> str:
    """Introspect the SQLite DB and produce a compact schema description for the prompt."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        lines = []
        for name, create_sql in cur.fetchall():
            lines.append(f"-- {name}\n{create_sql};")
        return "\n\n".join(lines)
    finally:
        conn.close()


def _extract_sql(raw_text: str) -> str:
    match = _SQL_FENCE_RE.search(raw_text)
    sql = match.group(1) if match else raw_text
    sql = sql.strip().rstrip(";").strip()
    return sql


def _validate_readonly(sql: str) -> None:
    if not sql.lower().lstrip().startswith("select"):
        raise UnsafeSQLError("Generated statement is not a SELECT query.")
    if _FORBIDDEN_KEYWORDS.search(sql):
        raise UnsafeSQLError("Generated statement contains a disallowed keyword.")
    if ";" in sql:
        raise UnsafeSQLError("Multiple statements are not allowed.")


def generate_sql(question: str, schema_description: str) -> str:
    prompt = f"""You are a SQL expert for a SQLite database. Given the schema below and a
question, write ONE read-only SQLite SELECT query that answers it. Rules:
- Output ONLY the SQL query, no explanation, no markdown fences.
- Never use INSERT/UPDATE/DELETE/DROP/ALTER or any statement other than SELECT.
- Use only tables/columns that exist in the schema.
- Prefer explicit column lists over SELECT *.
- Add a LIMIT 100 unless the question implies aggregation to a single row.
- Be deterministic: given the same schema and question, always generate the same query.

Schema:
{schema_description}

Question: {question}

SQL query:"""
    raw = generate_text(prompt, temperature=0.0)
    return _extract_sql(raw)


def run_query(db_path: Path, sql: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        return columns, rows
    finally:
        conn.close()


def answer_question(question: str, *, db_path: Path | None = None) -> QuantitativeResult:
    """End-to-end: NL question -> SQL -> execution -> structured result."""
    db_path = db_path or settings.sqlite_db_path
    log_event(logger, "info", "quantitative_query_received", question=question)

    with Timer(logger, "quantitative_query_handled", question=question) as timer:
        try:
            schema = _get_schema_description(db_path)
            sql = generate_sql(question, schema)
            log_event(logger, "info", "sql_generated", question=question, sql=sql)
            _validate_readonly(sql)
            columns, rows = run_query(db_path, sql)
            result = QuantitativeResult(
                question=question,
                sql=sql,
                columns=columns,
                rows=rows,
                row_count=len(rows),
            )
        except UnsafeSQLError as exc:
            result = QuantitativeResult(
                question=question, sql="", columns=[], rows=[], row_count=0, error=str(exc)
            )
        except sqlite3.Error as exc:
            result = QuantitativeResult(
                question=question,
                sql=locals().get("sql", ""),
                columns=[],
                rows=[],
                row_count=0,
                error=f"SQL execution error: {exc}",
            )
    result.metadata["duration_ms"] = timer.duration_ms
    return result


def format_result(result: QuantitativeResult) -> str:
    """Render a QuantitativeResult as human-readable text for the CLI/manager."""
    if not result.ok:
        return f"I couldn't answer that with the data agent: {result.error}"
    if result.row_count == 0:
        return f"The query ran successfully but returned no rows.\n\nSQL used:\n{result.sql}"

    from tabulate import tabulate

    table = tabulate(result.rows, headers=result.columns, tablefmt="github")
    return f"{table}\n\n_SQL used:_ `{result.sql}`"