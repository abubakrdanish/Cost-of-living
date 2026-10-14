# Australian Cost-of-Living Pipeline

![CI](https://github.com/<your-github-user>/<your-repo>/actions/workflows/ci.yml/badge.svg)
<!-- Replace <your-github-user>/<your-repo> after pushing to GitHub. -->

An end-to-end data engineering portfolio project. It ingests public Australian economic data, transforms and tests it with dbt, stores it in DuckDB, runs on a schedule with Prefect, is tested in CI, and feeds a dashboard.

**Question:** How have rents, wages and inflation changed over time, by state and capital city?

> Personal portfolio project using public data only. Not financial or immigration advice.

## Stack
Everything is free and runs locally, with no accounts or keys.
- **Warehouse:** DuckDB
- **Transform and tests:** dbt Core (dbt-duckdb)
- **Orchestration:** Prefect 3 (local server, cron schedule)
- **CI:** GitHub Actions (pytest + `dbt build` on committed fixtures)
- **Dashboard:** Evidence (Week 4)
- **Language:** Python 3.12

## Architecture

```
ABS Data API (CPI, WPI)      ABS release file (final quarterly CPI, Table 9)
          \                       /
           ingestion/   polite HTTP: User-Agent, 2 s spacing, retries with backoff
                |
           data/raw/<source>/   files saved unchanged, date-stamped, .meta.json sidecar
                |               (identical downloads are not saved again)
           DuckDB raw.*         append-only: one batch per new file, _source_file + _loaded_at
                |
           dbt source freshness   age of the newest data period vs the ABS release lag
                |
           dbt staging        latest snapshot, typed, decoded, correct series chosen
           dbt intermediate   rents splice (archive quarterly + monthly averages), snapshot diff
           dbt marts          dim_region, dim_quarter, mart_cost_of_living_quarterly
                |             (119 nodes built and tested on every run)
           reports/quality_report.md   written every run, pass or fail
                |
           dashboard (Evidence, Week 4)
```

**Orchestration:** `orchestration/flow.py` runs the whole chain as one Prefect flow, scheduled for weekdays at 13:00 Sydney time.

**CI:** `.github/workflows/ci.yml` runs pytest and `dbt build` against small, committed fixture files on every push. It makes no live ABS calls.

## Project structure
| Path | Purpose |
|---|---|
| `ingestion/` | Download and load code, one module per source; CI fixture tool (`ci_fixtures.py`) |
| `orchestration/` | Prefect flow (`flow.py`), schedule (`serve.py`), dbt runner (`dbt.py`), quality report (`quality_report.py`) |
| `dbt_project/` | Seeds, staging, intermediate and mart models; generic and singular tests; source freshness |
| `tests/` | Offline pytest suite; `fixtures/ci_raw/` holds the CI fixtures |
| `.github/workflows/` | `ci.yml` (every push/PR) and `live-ingestion.yml` (manual) |
| `docs/` | Data sources, data dictionary, operations guide |
| `data/raw/`, `warehouse/`, `reports/`, `logs/` | Generated locally; git-ignored |

## Setup (from a clean clone)
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock         # exact pinned versions; installs this repo's packages (editable)
cp .env.example .env                     # optional; no secrets needed
cp dbt_project/profiles.yml.example dbt_project/profiles.yml
python ingestion/init_duckdb.py          # create the DuckDB file and schemas
```

**Dependencies:** `requirements.txt` lists the top-level packages for people to read. `requirements.lock` pins every package and is what you install. It was resolved on macOS and checked package by package for Linux x86_64 / Python 3.12, which is what CI uses. To upgrade:
```bash
pip-compile --strip-extras requirements.txt -o requirements.lock
pip-sync requirements.lock
```
`sqlalchemy<2.1` is pinned on purpose: Prefect 3.8.8's scheduler crashes on SQLAlchemy 2.1.

## Run

**Everything, once.** This downloads, loads, checks freshness, runs `dbt build` and writes the report:
```bash
python -m orchestration.flow                    # exits 1 and prints PIPELINE FAILED on any failed test
python -m orchestration.flow --skip-download    # reuse data/raw/
```

**On a schedule** (weekdays at 13:00 Australia/Sydney), using two terminals:
```bash
PREFECT_SERVER_ANALYTICS_ENABLED=false prefect server start          # terminal 1
PREFECT_API_URL=http://127.0.0.1:4200/api python -m orchestration.serve   # terminal 2
```
See [`docs/operations.md`](docs/operations.md) for what must stay running, how to read the report, and what to do when a check fails.

**Individual steps:**
```bash
python -m ingestion.run_all [--sources cpi wpi rents] [--skip-download]   # download + load raw
(cd dbt_project && dbt source freshness --profiles-dir .)                 # freshness checks
(cd dbt_project && dbt build --profiles-dir .)                            # models + tests
python -m orchestration.quality_report                                    # report from current state
(cd dbt_project && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .)
pytest                                                                    # 63 offline tests
```

Re-running is safe:
- A download identical to a saved file isn't saved again.
- A file already in DuckDB isn't loaded twice.
- An ABS revision becomes a new snapshot. Staging uses the newest one, and the report lists what changed.

## Data quality
- **dbt build** builds 13 models and seeds and runs 106 tests:
  - Generic tests: not_null, unique grain, relationships, accepted values and ranges.
  - Splice: overlap within 0.5%; spliced Australia rents within 0.5% of the official series (warning only).
  - Mart: no quarter gaps per region; every index = 100 at the base quarter.
  - Archive: series IDs match their city.
  - Raw row counts: never shrink between downloads; growth over 25% gives a warning.
  - Revisions: staging reads only the newest download; ABS revision flags reach the mart.
- **Source freshness** checks the age of the newest data period. CPI and rents warn after 65 days and error after 95. WPI warns after 150 days and errors after 240. The thresholds come from the ABS release lags.
- **Quality report** (`reports/quality_report.md`, every run, plus history): row counts, latest period per source, freshness, test results, newest vs previous download, and revised observations.

## Raw tables (2026-10-12 download)
| Table | Rows | Contents |
|---|---|---|
| `raw.abs_cpi_all_groups` | 2,941 | All groups CPI, Australia + 8 capitals; quarterly 1948-Q3 to 2026-Q2, monthly 2024-04 to 2026-08 |
| `raw.abs_cpi_rents` | 1,382 | CPI Rents; monthly for Australia + 8 capitals from 2022-07, quarterly for Australia from 1972-Q3 |
| `raw.abs_cpi_capital_cities_quarterly_2025q3` | 231,122 | Final quarterly CPI release, Table 9: all CPI groups by capital city (long format) |
| `raw.abs_wpi` | 15,312 | WPI quarterly index, by state, sector and industry, 1997-Q3 to 2026-Q2 |

See [`docs/data_sources.md`](docs/data_sources.md) for dataflow IDs, licences and known data issues.

## dbt models
| Schema | Models |
|---|---|
| `reference` (seeds) | `region_mapping`, `abs_archive_rents_series` |
| `staging` (views) | `stg_abs__cpi_all_groups`, `stg_abs__cpi_rents`, `stg_abs__cpi_rents_archive`, `stg_abs__wpi` |
| `intermediate` (views) | `int_rents_monthly_to_quarterly`, `int_rents_splice_overlap`, `int_rents_quarterly_spliced`, `int_raw_snapshot_changes` |
| `marts` (tables) | `dim_region`, `dim_quarter`, **`mart_cost_of_living_quarterly`** |

The main output is `marts.mart_cost_of_living_quarterly`:
- **Grain:** one row per quarter × region.
- **Range:** 1997-Q3 to the latest quarter that all three series cover (1,044 rows).
- **Contents:** CPI, rents and WPI rebased to 1997-Q3 = 100, annual % changes, and real wage growth.
- **Flags:** rents splice flags, revision flags, and `missing_reason`.

No dbt model is incremental; the raw layer is. The reasons for each model are in [`docs/data_dictionary.md`](docs/data_dictionary.md), along with the columns and caveats.

## Progress
- [x] Day 1: project scaffold and DuckDB initialised
- [x] Week 1: ingest three datasets (CPI, WPI, CPI rents) into `data/raw/` and DuckDB `raw`; offline tests
- [x] Week 2: dbt staging, rents splice, dimensions and quarterly mart, with tests and a data dictionary; lock file
- [x] Week 3: freshness, row-count and revision checks, quality report, Prefect flow and schedule, CI with fixtures
- [ ] Week 4: dashboard (Evidence), architecture diagram, findings write-up

## Data and attribution
Based on Australian Bureau of Statistics data: Consumer Price Index, Australia (6401.0) and Wage Price Index, Australia (6345.0), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
