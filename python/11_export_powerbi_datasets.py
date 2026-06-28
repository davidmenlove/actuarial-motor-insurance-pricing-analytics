"""
11_export_powerbi_datasets.py
Project: Actuarial Motor Insurance Risk Analysis

Purpose:
    Export every table in the DuckDB mart schema to CSV files for Power BI.

Why this exists:
    Power BI can have file-locking issues when connecting directly to a local
    DuckDB database through ODBC. Exporting the mart layer to CSV keeps the
    analytical architecture intact while giving Power BI stable import files.

Inputs:
    database/actuarial_risk.duckdb
    mart schema tables inside DuckDB

Outputs:
    powerbi/datasets/*.csv

Run from the project root:
    python python/11_export_powerbi_datasets.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "database" / "actuarial_risk.duckdb"
EXPORT_DIR = PROJECT_ROOT / "powerbi" / "datasets"


def safe_csv_name(table_name: str) -> str:
    """Convert a DuckDB table name into a CSV filename."""
    return f"{table_name}.csv"


def main() -> None:
    """Export all mart schema tables to Power BI dataset CSVs."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB database not found: {DB_PATH}\n"
            "Run build_project.py or build the warehouse first."
        )

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    mart_tables = con.sql(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'mart'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
    ).df()["table_name"].tolist()

    if not mart_tables:
        raise ValueError(
            "No mart tables found. Run sql/07_create_powerbi_mart.sql first."
        )

    print()
    print("Exporting Power BI datasets")
    print("-" * 72)
    print(f"Source database: {DB_PATH}")
    print(f"Export folder:   {EXPORT_DIR}")
    print()

    for table_name in mart_tables:
        output_path = EXPORT_DIR / safe_csv_name(table_name)
        output_path_sql = str(output_path).replace("'", "''")

        con.sql(
            f"""
            COPY mart.{table_name}
            TO '{output_path_sql}'
            (HEADER, DELIMITER ',');
            """
        )

        row_count = con.sql(
            f"SELECT COUNT(*) AS row_count FROM mart.{table_name};"
        ).fetchone()[0]

        print(f"✓ {table_name} -> {output_path.name} ({row_count:,} rows)")

    con.close()

    print()
    print(f"Exported {len(mart_tables)} mart tables to powerbi/datasets/")


if __name__ == "__main__":
    main()
