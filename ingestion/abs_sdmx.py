"""Helpers for the ABS Data API (SDMX REST, beta, no key required).

Docs: https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis/data-api-user-guide
Data query pattern: {base}/data/{agency},{dataflow},{version}/{key}?startPeriod=&endPeriod=
"""
from __future__ import annotations

import csv
import io
from urllib.parse import urlencode

from ingestion.config import ABS_DATA_API_BASE

# CSV with both codes and labels, e.g. "2: Melbourne", so raw files are self-describing.
SDMX_CSV_ACCEPT = "application/vnd.sdmx.data+csv;labels=both"
REQUIRED_COLUMNS = ("DATAFLOW", "TIME_PERIOD", "OBS_VALUE")


def data_url(
    dataflow: str,
    key: str,
    start_period: str | None = None,
    end_period: str | None = None,
    base: str = ABS_DATA_API_BASE,
) -> str:
    """Build a data query URL. `dataflow` is e.g. 'ABS,CPI,2.0.0'."""
    params = {k: v for k, v in {"startPeriod": start_period, "endPeriod": end_period}.items() if v}
    query = f"?{urlencode(params)}" if params else ""
    return f"{base}/data/{dataflow}/{key}{query}"


def normalise_column_name(header: str) -> str:
    """'TIME_PERIOD: Time Period' -> 'time_period'; 'OBS_VALUE' -> 'obs_value'."""
    return header.split(":", 1)[0].strip().lower()


def validate_sdmx_csv(content: bytes) -> int:
    """Check a response looks like SDMX-CSV with data. Returns the data row count.

    Raises ValueError for HTML error pages, empty bodies or missing columns.
    """
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        raise ValueError("Empty response: no CSV header")
    codes = {normalise_column_name(h).upper() for h in header}
    missing = [c for c in REQUIRED_COLUMNS if c not in codes]
    if missing:
        raise ValueError(f"Not SDMX-CSV: missing columns {missing}; header={header[:5]}")
    row_count = sum(1 for row in reader if row)
    if row_count == 0:
        raise ValueError("SDMX-CSV has a header but no data rows")
    return row_count
