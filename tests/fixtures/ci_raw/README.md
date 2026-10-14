# CI raw fixtures

GitHub Actions runs `dbt build` against these files instead of calling the ABS. They're cut from real downloads (2026-10-12) by `python -m ingestion.ci_fixtures generate`, and they use the same folder layout and file names as `data/raw/`.

| File | Rows | What it is |
|---|---|---|
| `abs_cpi/abs_cpi_all_groups_20261012.csv` | 477 | Real lines, unchanged: All groups CPI, Original, quarterly from 2020-Q3 and every monthly row (from 2024-04). |
| `abs_cpi_rents/abs_cpi_rents_20261012.csv` | 556 | Real lines, unchanged: Rents `30014` Original, monthly from 2020-07 (data starts 2022-07) and quarterly from 2020-Q3. Also some 2026 decoys that staging must drop: code `115522` and seasonally adjusted. |
| `abs_cpi_rents/abs_cpi_rents_20260915.csv` | 537 | **Edited on purpose.** An "earlier download" of the file above: the newest month (2026-08, 19 rows) removed, and one value changed. Melbourne, Jul 2026, Rents Original monthly was **102.04 and is changed to 101.54**. This exercises revision handling (staging must use the newer file; `int_raw_snapshot_changes` must report 19 added + 1 changed) and the row-count check. |
| `abs_cpi_rents/abs_cpi_capital_cities_quarterly_2025q3_20261012.xlsx` | 399 values | Real ABS workbook layout and metadata rows, quarters from 2020-Q3 to 2025-Q3. It has the 18 Rents columns (two identical per city) plus one unrelated series (All groups, Melbourne). `Series Start`, `Series End` and `No. Obs` still describe the full real series. |
| `abs_wpi/abs_wpi_20261012.csv` | 224 | Real lines, unchanged: WPI THRPEB, Private and Public, All industries, Original, from 2020-Q3. Also decoys from 2025-Q3: Victoria private sector, and Australia seasonally adjusted. |

Every CSV line except the one edited value is byte-for-byte identical to the real file, including ABS's CRLF line endings. For each file, `comm -23` against the real download returns 0 lines.

## How CI uses them

```bash
COL_RAW_DATA_DIR=tests/fixtures/ci_raw python -m ingestion.run_all --skip-download
cd dbt_project && dbt build --profiles-dir . \
  --vars '{mart_start_quarter: "2021-07-01", index_base_quarter: "2021-07-01"}'
```

The vars move the mart's start and base quarter to 2021-Q3, because the fixtures start in 2020-Q3 and annual changes need a year of history. Production keeps 1997-Q3, which is checked by local runs and the manual live workflow. Freshness isn't run in CI: fixtures age by design.

## Keeping them in sync with the real schema

- `python -m ingestion.ci_fixtures check` compares the fixtures with the newest files in `data/raw/`: the CSV headers, and the XLSX metadata rows the parser depends on. It exits 1 on any difference.
- The manual **Live ingestion check** GitHub workflow downloads real data and runs `check`. If the ABS changes a column, that workflow fails.
- To refresh: run the ingestion, then `python -m ingestion.ci_fixtures generate`, review the diff, and commit.
- `tests/test_ci_fixtures.py` checks offline that every dataset has a fixture, that the fixtures parse and load, and that the deliberate edit is still exactly one value.
