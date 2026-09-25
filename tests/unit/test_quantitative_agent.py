from __future__ import annotations

import pytest

from src.quantitative import agent as quantitative_agent
from src.quantitative.agent import UnsafeSQLError, _extract_sql, _validate_readonly


def test_extract_sql_strips_markdown_fence():
    raw = "```sql\nSELECT * FROM sales;\n```"
    assert _extract_sql(raw) == "SELECT * FROM sales"


def test_extract_sql_handles_plain_text():
    raw = "SELECT customer_id FROM customers;"
    assert _extract_sql(raw) == "SELECT customer_id FROM customers"


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE sales",
        "DELETE FROM customers",
        "UPDATE sales SET revenue = 0",
        "SELECT * FROM sales; DROP TABLE sales",
        "INSERT INTO sales VALUES (1,2,3)",
    ],
)
def test_validate_readonly_rejects_unsafe_sql(sql):
    with pytest.raises(UnsafeSQLError):
        _validate_readonly(sql)


def test_validate_readonly_accepts_select():
    _validate_readonly("SELECT region_name FROM regions")  # should not raise


def test_answer_question_end_to_end(temp_sqlite_db, monkeypatch):
    monkeypatch.setattr(
        quantitative_agent,
        "generate_sql",
        lambda question, schema: "SELECT region_name FROM regions ORDER BY region_id",
    )

    result = quantitative_agent.answer_question("List all regions", db_path=temp_sqlite_db)

    assert result.ok
    assert result.columns == ["region_name"]
    assert result.row_count == 4
    assert ("North America",) in result.rows


def test_answer_question_rejects_unsafe_generated_sql(temp_sqlite_db, monkeypatch):
    monkeypatch.setattr(
        quantitative_agent, "generate_sql", lambda question, schema: "DROP TABLE sales"
    )

    result = quantitative_agent.answer_question("delete everything", db_path=temp_sqlite_db)

    assert not result.ok
    assert "disallowed" in result.error.lower() or "not a select" in result.error.lower()


def test_answer_question_surfaces_sql_errors(temp_sqlite_db, monkeypatch):
    monkeypatch.setattr(
        quantitative_agent, "generate_sql", lambda question, schema: "SELECT * FROM not_a_table"
    )

    result = quantitative_agent.answer_question("nonsense query", db_path=temp_sqlite_db)

    assert not result.ok
    assert "sql execution error" in result.error.lower()


def test_format_result_renders_table(temp_sqlite_db, monkeypatch):
    monkeypatch.setattr(
        quantitative_agent,
        "generate_sql",
        lambda question, schema: "SELECT region_name FROM regions ORDER BY region_id LIMIT 1",
    )
    result = quantitative_agent.answer_question("first region", db_path=temp_sqlite_db)
    text = quantitative_agent.format_result(result)
    assert "North America" in text
    assert "SQL used" in text