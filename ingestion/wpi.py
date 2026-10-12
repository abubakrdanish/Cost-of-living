"""ABS Wage Price Index (6345.0): quarterly index numbers.

Dataflow ABS,WPI,1.2.0 (verified 2026-10-12). Key dimensions are
MEASURE.INDEX.SECTOR.INDUSTRY.TSEST.REGION.FREQ; we request MEASURE 1
(quarterly index, 2008-09 = 100) with every other dimension open, FREQ=Q.

What exists (checked against the API, 1997-Q3 to 2026-Q2):
  - states/territories: original series only, all industries, by sector
  - industries (ANZSIC divisions): Australia only
  - seasonally adjusted / trend: Australia only

Run: python -m ingestion.wpi
"""
from __future__ import annotations

from ingestion.abs_sdmx import data_url
from ingestion.dataset import RawDataset
from ingestion.pipeline import run

WPI_INDEX = RawDataset(
    name="abs_wpi",
    source="abs_wpi",
    url=data_url("ABS,WPI,1.2.0", "1......Q"),
    kind="sdmx_csv",
    description="WPI quarterly index numbers, all sectors/industries/states",
)

DATASETS = [WPI_INDEX]

if __name__ == "__main__":
    run(DATASETS)
