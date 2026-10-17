"""Create the local DuckDB database and the raw/staging/marts schemas."""
from pathlib import Path

import duckdb

from ingestion.config import DB_PATH

SCHEMAS = ["raw", "staging", "marts"]


def init_database(db_path: Path = DB_PATH) -> list[str]:
    """Create the database file and schemas if missing. Returns the schema names."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        for schema in SCHEMAS:
            con.execute(f"create schema if not exists {schema}")
        # Only this database's schemas, not the system/temp catalogs.
        return [r[0] for r in con.execute(
            "select schema_name from information_schema.schemata "
            "where catalog_name = current_database() order by 1"
        ).fetchall()]


def main():
    found = init_database()
    print(f"DuckDB ready at {DB_PATH}")
    print("Schemas:", ", ".join(found))


if __name__ == "__main__":
    main()
