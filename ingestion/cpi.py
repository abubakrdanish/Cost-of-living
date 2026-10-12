"""ABS Consumer Price Index (6401.0): All groups CPI, Australia and 8 capital cities.

Dataflow ABS,CPI,2.0.0 (verified 2026-10-12). Key dimensions are
MEASURE.INDEX.TSEST.REGION.FREQ; we request:
    MEASURE 1      index numbers (Sep 2025 = 100)
    INDEX   10001  All groups CPI
    TSEST, REGION, FREQ  all values (monthly from 2024-04, quarterly from 1948-Q3)

Run: python -m ingestion.cpi
"""
from __future__ import annotations

from ingestion.abs_sdmx import data_url
from ingestion.dataset import RawDataset
from ingestion.pipeline import run

CPI_ALL_GROUPS = RawDataset(
    name="abs_cpi_all_groups",
    source="abs_cpi",
    url=data_url("ABS,CPI,2.0.0", "1.10001..."),
    kind="sdmx_csv",
    description="All groups CPI index numbers, Australia + capital cities, monthly and quarterly",
)

DATASETS = [CPI_ALL_GROUPS]

if __name__ == "__main__":
    run(DATASETS)
