"""
Builds the sample SQLite database used by the Quantitative NL-to-SQL agent.

Run with:  python -m scripts.init_db
Produces a small but realistic "enterprise" dataset: regions, customers,
products, and monthly sales, plus an employee satisfaction survey table
(used by the cross-agent "complex query" demo).
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date
from pathlib import Path

from src.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS regions (
    region_id   INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    region_id     INTEGER NOT NULL REFERENCES regions(region_id),
    signup_date   TEXT NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    unit_price   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id      INTEGER PRIMARY KEY,
    sale_date    TEXT NOT NULL,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    product_id   INTEGER NOT NULL REFERENCES products(product_id),
    quantity     INTEGER NOT NULL,
    revenue      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_satisfaction (
    survey_id     INTEGER PRIMARY KEY,
    survey_period TEXT NOT NULL,
    department    TEXT NOT NULL,
    avg_score     REAL NOT NULL,
    response_rate REAL NOT NULL
);
"""

REGIONS = ["North America", "EMEA", "APAC", "LATAM"]

PRODUCTS = [
    ("Northwind Analytics Core", "Platform", 499.00),
    ("Northwind Insights Add-on", "Platform", 149.00),
    ("Northwind API Access", "Platform", 99.00),
    ("Onboarding Package", "Services", 1200.00),
    ("Premium Support Plan", "Services", 300.00),
]

DEPARTMENTS = ["Engineering", "Sales", "Customer Success", "Marketing", "HR"]


def _random_date(year: int, month: int) -> str:
    day = random.randint(1, 28)
    return date(year, month, day).isoformat()


def build_database(db_path: Path) -> None:
    random.seed(42)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)

        # Regions
        conn.executemany(
            "INSERT INTO regions (region_id, region_name) VALUES (?, ?)",
            list(enumerate(REGIONS, start=1)),
        )

        # Products
        conn.executemany(
            "INSERT INTO products (product_id, product_name, category, unit_price) "
            "VALUES (?, ?, ?, ?)",
            [(i, name, cat, price) for i, (name, cat, price) in enumerate(PRODUCTS, start=1)],
        )

        # Customers
        customers = []
        for cid in range(1, 41):
            region_id = random.randint(1, len(REGIONS))
            signup = _random_date(2024, random.randint(1, 12))
            is_active = 0 if random.random() < 0.15 else 1
            customers.append((cid, f"Customer {cid:03d}", region_id, signup, is_active))
        conn.executemany(
            "INSERT INTO customers (customer_id, customer_name, region_id, signup_date, is_active) "
            "VALUES (?, ?, ?, ?, ?)",
            customers,
        )

        # Sales across 2024 and 2025 (through September), with a Q4 seasonal bump
        sales = []
        sale_id = 1
        for year in (2024, 2025):
            last_month = 12 if year == 2024 else 9
            for month in range(1, last_month + 1):
                seasonal_boost = 1.4 if month in (11, 12) else 1.0
                num_sales = int(random.randint(15, 25) * seasonal_boost)
                for _ in range(num_sales):
                    customer_id = random.randint(1, 40)
                    product_id = random.randint(1, len(PRODUCTS))
                    quantity = random.randint(1, 5)
                    unit_price = PRODUCTS[product_id - 1][2]
                    revenue = round(unit_price * quantity * random.uniform(0.9, 1.1), 2)
                    sales.append(
                        (sale_id, _random_date(year, month), customer_id, product_id, quantity, revenue)
                    )
                    sale_id += 1
        conn.executemany(
            "INSERT INTO sales (sale_id, sale_date, customer_id, product_id, quantity, revenue) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            sales,
        )

        # Employee satisfaction survey (used for cross-agent "complex query" demo)
        survey_rows = []
        survey_id = 1
        for period in ("2024-H1", "2024-H2", "2025-H1"):
            for dept in DEPARTMENTS:
                avg_score = round(random.uniform(3.2, 4.6), 2)
                response_rate = round(random.uniform(0.55, 0.95), 2)
                survey_rows.append((survey_id, period, dept, avg_score, response_rate))
                survey_id += 1
        conn.executemany(
            "INSERT INTO employee_satisfaction "
            "(survey_id, survey_period, department, avg_score, response_rate) "
            "VALUES (?, ?, ?, ?, ?)",
            survey_rows,
        )

        conn.commit()
    finally:
        conn.close()


def main() -> None:
    build_database(settings.sqlite_db_path)
    print(f"Database created at {settings.sqlite_db_path}")


if __name__ == "__main__":
    main()