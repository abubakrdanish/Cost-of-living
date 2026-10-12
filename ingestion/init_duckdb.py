"""Create the local DuckDB database and the raw/staging/marts schemas."""
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parent.parent / "warehouse" / "cost_of_living.duckdb"
SCHEMAS = ["raw", "staging", "marts"]


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    for schema in SCHEMAS:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    found = [r[0] for r in con.execute(
        "SELECT schema_name FROM information_schema.schemata ORDER BY 1"
    ).fetchall()]
    con.close()
    print(f"DuckDB ready at {DB_PATH}")
    print("Schemas:", ", ".join(found))


if __name__ == "__main__":
    main()
