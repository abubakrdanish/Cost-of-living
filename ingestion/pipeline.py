"""Shared runner: download each dataset, then load all raw files into DuckDB."""
from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

import duckdb

from ingestion.config import DB_PATH, setup_logging
from ingestion.dataset import RawDataset, fetch
from ingestion.http_client import PoliteClient
from ingestion.init_duckdb import init_database
from ingestion.load_raw import load_dataset

log = logging.getLogger(__name__)


def download_all(datasets: Sequence[RawDataset]) -> list[str]:
    """Fetch each dataset; keep going if one fails. Returns names that failed."""
    client = PoliteClient()
    failed = []
    for dataset in datasets:
        try:
            result = fetch(dataset, client)
            log.info("%s: %s %s", dataset.name,
                     "new file" if result.written else "no change", result.path.name)
        except Exception:
            log.exception("Download failed for %s", dataset.name)
            failed.append(dataset.name)
    return failed


def load_all(datasets: Sequence[RawDataset]) -> list[str]:
    """Load raw files into DuckDB. Returns names that failed."""
    init_database(DB_PATH)
    failed = []
    with duckdb.connect(str(DB_PATH)) as con:
        for dataset in datasets:
            try:
                summary = load_dataset(con, dataset)
                log.info("raw.%s: %d new file(s), %d rows in table",
                         summary.table, len(summary.files_loaded), summary.total_rows)
            except Exception:
                log.exception("Load failed for %s", dataset.name)
                failed.append(dataset.name)
    return failed


def run(datasets: Sequence[RawDataset], download: bool = True, load: bool = True) -> None:
    """Entry point used by each source module and by run_all. Exits 1 on any failure."""
    setup_logging()
    failed = []
    if download:
        failed += download_all(datasets)
    if load:
        failed += load_all(datasets)
    if failed:
        log.error("Finished with failures: %s", ", ".join(sorted(set(failed))))
        sys.exit(1)
    log.info("Done.")
