"""Rents: the CPI 'Rents' component, Australia and 8 capital cities.

Two raw datasets, because the ABS moved to a monthly CPI in late 2025:

1. Current series, ABS Data API ABS,CPI,2.0.0 (verified 2026-10-12)
   INDEX 30014 (expenditure class 'Rents') and 115522 (sub-group 'Rents').
   Capital cities: monthly from 2022-07 only. Australia: also quarterly from 1972-Q3.

2. Historical quarterly series by capital city, 1972-Q3 to 2025-Q3:
   6401.0 Sep quarter 2025 (the final quarterly CPI release), Table 9,
   'Group, Sub-group and Expenditure Class, Index Numbers by Capital City'.
   This release is frozen, so the file is downloaded once and then deduplicated.
   Note: its index base (2011-12 = 100) differs from the current API (Sep 2025 = 100).

Run: python -m ingestion.rents
"""
from __future__ import annotations

from ingestion.abs_sdmx import data_url
from ingestion.dataset import RawDataset
from ingestion.pipeline import run

CPI_RENTS = RawDataset(
    name="abs_cpi_rents",
    source="abs_cpi_rents",
    url=data_url("ABS,CPI,2.0.0", "1.30014+115522..."),
    kind="sdmx_csv",
    description="CPI Rents index numbers, Australia + capital cities (API)",
)

CPI_CAPITAL_CITIES_QUARTERLY_ARCHIVE = RawDataset(
    name="abs_cpi_capital_cities_quarterly_2025q3",
    source="abs_cpi_rents",
    url=(
        "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/"
        "consumer-price-index-australia/sep-quarter-2025/640107.xlsx"
    ),
    kind="abs_xlsx",
    description="CPI Table 9, quarterly index numbers by capital city, final quarterly release",
)

DATASETS = [CPI_RENTS, CPI_CAPITAL_CITIES_QUARTERLY_ARCHIVE]

if __name__ == "__main__":
    run(DATASETS)
