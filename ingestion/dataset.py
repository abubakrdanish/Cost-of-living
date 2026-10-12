"""A raw dataset definition and the shared download step used by every source module."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ingestion.abs_sdmx import SDMX_CSV_ACCEPT, validate_sdmx_csv
from ingestion.abs_timeseries_xlsx import looks_like_xlsx
from ingestion.config import RAW_DATA_DIR
from ingestion.http_client import PoliteClient
from ingestion.raw_files import SaveResult, save_raw

log = logging.getLogger(__name__)

Kind = Literal["sdmx_csv", "abs_xlsx"]


@dataclass(frozen=True)
class RawDataset:
    """One downloadable file and the DuckDB raw table it loads into.

    name:   file stem and raw table name, e.g. 'abs_cpi' -> raw.abs_cpi
    source: sub-folder of data/raw/
    """

    name: str
    source: str
    url: str
    kind: Kind
    description: str

    @property
    def ext(self) -> str:
        return "csv" if self.kind == "sdmx_csv" else "xlsx"

    @property
    def accept(self) -> str | None:
        return SDMX_CSV_ACCEPT if self.kind == "sdmx_csv" else None

    @property
    def table(self) -> str:
        return self.name

    def raw_dir(self, root: Path = RAW_DATA_DIR) -> Path:
        return root / self.source


def validate(dataset: RawDataset, content: bytes) -> dict:
    """Reject error pages before anything is saved. Returns extra metadata."""
    if dataset.kind == "sdmx_csv":
        return {"data_rows": validate_sdmx_csv(content)}
    if not looks_like_xlsx(content):
        raise ValueError(f"{dataset.name}: response is not an XLSX file")
    return {}


def fetch(dataset: RawDataset, client: PoliteClient, root: Path = RAW_DATA_DIR) -> SaveResult:
    """Download, validate and save one dataset unchanged."""
    log.info("Fetching %s: %s", dataset.name, dataset.description)
    response = client.get(dataset.url, accept=dataset.accept)
    extra = validate(dataset, response.content)
    if extra:
        log.info("  %s", ", ".join(f"{k}={v}" for k, v in extra.items()))
    return save_raw(
        content=response.content,
        directory=dataset.raw_dir(root),
        stem=dataset.name,
        ext=dataset.ext,
        source_url=dataset.url,
        extra_meta={"content_type": response.content_type,
                    "last_modified": response.last_modified, **extra},
    )
