"""Run the queries behind the written findings (docs/findings_queries.sql).

Opens the warehouse read-only and prints each named query's result, so every
figure in the README and dashboard can be checked against the data.

    python -m orchestration.findings            # all queries
    python -m orchestration.findings F1 F6      # selected queries
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb

from ingestion.config import DB_PATH, PROJECT_ROOT

QUERIES_FILE = PROJECT_ROOT / "docs" / "findings_queries.sql"
NAME_LINE = re.compile(r"^-- name:\s*(\S+)\s*$", re.MULTILINE)


def parse_queries(text: str) -> dict[str, str]:
    """Split the file into {name: sql} on '-- name: <id>' lines."""
    parts = NAME_LINE.split(text)
    # parts = [preamble, name1, body1, name2, body2, ...]
    return {name: body.strip().rstrip(";") for name, body in zip(parts[1::2], parts[2::2])}


def run(names: list[str] | None = None, db_path: Path = DB_PATH,
        queries_file: Path = QUERIES_FILE) -> dict[str, duckdb.DuckDBPyRelation]:
    queries = parse_queries(queries_file.read_text(encoding="utf-8"))
    selected = {k: v for k, v in queries.items()
                if not names or any(k == n or k.startswith(n + "_") for n in names)}
    con = duckdb.connect(str(db_path), read_only=True)
    return {name: con.sql(sql) for name, sql in selected.items()}


def main(argv: list[str] | None = None) -> int:
    results = run(argv if argv is not None else sys.argv[1:])
    for name, relation in results.items():
        print(f"\n## {name}")
        relation.show(max_width=200, max_rows=40)
    return 0


if __name__ == "__main__":
    sys.exit(main())
