"""Load saved raw files into DuckDB `raw.<dataset>` tables.

Each raw table keeps every downloaded snapshot, tagged with `_source_file`
and `_loaded_at`. A file that is already in the table is skipped, so
re-running never duplicates rows. Staging models (dbt, week 2) pick the
latest snapshot; older snapshots let us see ABS revisions.

SDMX-CSV columns are loaded as VARCHAR with names normalised
('TIME_PERIOD: Time Period' -> time_period); values are untouched.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from ingestion.abs_sdmx import normalise_column_name
from ingestion.abs_timeseries_xlsx import parse_workbook
from ingestion.config import RAW_DATA_DIR
from ingestion.dataset import RawDataset
from ingestion.raw_files import list_data_files

log = logging.getLogger(__name__)

RAW_SCHEMA = "raw"


@dataclass(frozen=True)
class LoadSummary:
    table: str
    files_loaded: list[str]
    files_skipped: list[str]
    total_rows: int


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
        [RAW_SCHEMA, table],
    ).fetchone()[0] > 0


def loaded_files(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    if not table_exists(con, table):
        return set()
    rows = con.execute(f"SELECT DISTINCT _source_file FROM {RAW_SCHEMA}.{table}").fetchall()
    return {r[0] for r in rows}


def _sdmx_select(con: duckdb.DuckDBPyConnection, path: Path) -> str:
    """SELECT list + FROM clause reading a CSV as text with normalised column names."""
    source = f"read_csv({_sql_string(str(path))}, header = true, all_varchar = true)"
    headers = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()]
    columns = ", ".join(f"{_quote_ident(h)} AS {normalise_column_name(h)}" for h in headers)
    return f"SELECT {columns} FROM {source}"


def _insert(con: duckdb.DuckDBPyConnection, table: str, select_sql: str,
            source_file: str, loaded_at: datetime) -> int:
    """Create the table on first use, then append rows by column name."""
    lineage = f"{_sql_string(source_file)} AS _source_file, " \
              f"CAST({_sql_string(loaded_at.isoformat())} AS TIMESTAMPTZ) AS _loaded_at"
    wrapped = f"SELECT src.*, {lineage} FROM ({select_sql}) AS src"
    con.execute(f"CREATE TABLE IF NOT EXISTS {RAW_SCHEMA}.{table} AS {wrapped} LIMIT 0")
    before = con.execute(f"SELECT count(*) FROM {RAW_SCHEMA}.{table}").fetchone()[0]
    con.execute(f"INSERT INTO {RAW_SCHEMA}.{table} BY NAME {wrapped}")
    after = con.execute(f"SELECT count(*) FROM {RAW_SCHEMA}.{table}").fetchone()[0]
    return after - before


def load_file(con: duckdb.DuckDBPyConnection, dataset: RawDataset, path: Path,
              loaded_at: datetime) -> int:
    """Load one file inside a transaction. Returns rows inserted."""
    con.begin()
    try:
        if dataset.kind == "sdmx_csv":
            inserted = _insert(con, dataset.table, _sdmx_select(con, path), path.name, loaded_at)
        else:
            frame = parse_workbook(path)
            con.register("xlsx_frame", frame)
            try:
                inserted = _insert(con, dataset.table, "SELECT * FROM xlsx_frame",
                                   path.name, loaded_at)
            finally:
                con.unregister("xlsx_frame")
        con.commit()
    except Exception:
        con.rollback()
        raise
    return inserted


def load_dataset(con: duckdb.DuckDBPyConnection, dataset: RawDataset,
                 root: Path = RAW_DATA_DIR, loaded_at: datetime | None = None) -> LoadSummary:
    """Load every raw file for a dataset that is not already in its table."""
    loaded_at = loaded_at or datetime.now(timezone.utc)
    already = loaded_files(con, dataset.table)
    loaded, skipped = [], []
    for path in list_data_files(dataset.raw_dir(root), dataset.name, dataset.ext):
        if path.name in already:
            skipped.append(path.name)
            continue
        rows = load_file(con, dataset, path, loaded_at)
        log.info("Loaded %s -> %s.%s (%d rows)", path.name, RAW_SCHEMA, dataset.table, rows)
        loaded.append(path.name)
    if skipped:
        log.info("Already loaded, skipped: %s", ", ".join(skipped))
    total = (con.execute(f"SELECT count(*) FROM {RAW_SCHEMA}.{dataset.table}").fetchone()[0]
             if table_exists(con, dataset.table) else 0)
    return LoadSummary(dataset.table, loaded, skipped, total)
