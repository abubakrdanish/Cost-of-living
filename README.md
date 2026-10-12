# Australian Cost-of-Living Pipeline

An end-to-end data engineering portfolio project: ingest public Australian economic data, transform and test it with dbt, store it in DuckDB, and serve it in a dashboard.

**Question:** How have rents, wages and inflation changed over time, by state and capital city?

> Personal portfolio project using public data only. Not financial or immigration advice.

## Stack
- **Warehouse:** DuckDB (local, free)
- **Transform and tests:** dbt Core (dbt-duckdb)
- **Orchestration:** Prefect (week 3)
- **Dashboard:** Evidence, Metabase or Looker Studio (week 4; see plan below)
- **Language:** Python 3.11+ (developed on 3.12)

## Architecture
`ABS Data API + ABS release files` -> `ingestion/` -> `data/raw/<source>/` (unchanged, date-stamped) -> DuckDB `raw` schema -> dbt `staging` -> dbt `marts` -> dashboard

## Project structure
| Path | Purpose |
|---|---|
| `data/raw/` | Downloaded source files, saved unchanged with a `.meta.json` sidecar (not committed) |
| `warehouse/` | Local DuckDB file (not committed) |
| `ingestion/` | Download and load code (see below) |
| `tests/` | Offline pytest suite and small fixtures |
| `dbt_project/` | Staging and mart models, dbt tests |
| `orchestration/` | Scheduled Prefect flows (week 3) |
| `docs/` | Data sources, data dictionary, diagrams |

### `ingestion/`
| Module | Role |
|---|---|
| `cpi.py`, `wpi.py`, `rents.py` | One module per source: which ABS dataflow or file to fetch |
| `run_all.py` | CLI that runs every source (download, then load) |
| `pipeline.py` | Shared runner used by the source modules and `run_all` |
| `http_client.py` | User-Agent, timeouts, retries with backoff, polite request rate |
| `raw_files.py` | Date-stamped raw files; identical downloads are not saved twice |
| `abs_sdmx.py`, `abs_timeseries_xlsx.py` | ABS format helpers (SDMX-CSV, time series workbooks) |
| `load_raw.py` | Loads raw files into `raw.*` tables with `_source_file` and `_loaded_at` |
| `init_duckdb.py` | Creates the database and the `raw`, `staging` and `marts` schemas |
| `config.py` | Paths, `.env` overrides, logging (to stderr and `logs/ingestion.log`) |

## Setup (from a clean clone)
```bash
python3.12 -m venv .venv                 # any Python 3.11+
source .venv/bin/activate
pip install -r requirements.txt          # also installs this repo as the `ingestion` package
cp .env.example .env                     # optional; no secrets needed
python ingestion/init_duckdb.py          # create the DuckDB file and schemas
cp dbt_project/profiles.yml.example dbt_project/profiles.yml
(cd dbt_project && dbt debug --profiles-dir .)
```

## Run
```bash
python -m ingestion.run_all                      # download + load all sources
python -m ingestion.run_all --sources wpi        # one source (cpi | wpi | rents)
python -m ingestion.run_all --skip-download      # reload from data/raw/ only
python -m ingestion.cpi                          # each source also runs on its own
pytest                                           # offline tests (network is blocked)
```
Re-running is safe. A download identical to a saved file isn't saved again, and a file already in DuckDB isn't loaded twice. When the ABS revises data, the pipeline saves a new date-stamped file and loads it as a new snapshot.

## Raw tables (after the first run, 2026-10-12)
| Table | Rows | Contents |
|---|---|---|
| `raw.abs_cpi_all_groups` | 2,941 | All groups CPI, Australia + 8 capitals; quarterly 1948-Q3 to 2026-Q2, monthly 2024-04 to 2026-08 |
| `raw.abs_cpi_rents` | 1,382 | CPI Rents, monthly for Australia + 8 capitals from 2022-07; quarterly for Australia from 1972-Q3 |
| `raw.abs_cpi_capital_cities_quarterly_2025q3` | 231,122 | Final quarterly CPI release, Table 9: all CPI groups by capital city, 1948 to 2025-Q3 (long format) |
| `raw.abs_wpi` | 15,312 | WPI quarterly index, by state, sector and industry, 1997-Q3 to 2026-Q2 |

See `docs/data_sources.md` for dataflow IDs, licences and known data issues.

## Progress
- [x] Day 1: project scaffold and DuckDB initialised
- [x] Week 1: ingest three datasets (CPI, WPI, CPI rents) into `data/raw/` and DuckDB `raw`; offline tests
- [ ] Week 2: dbt staging and mart models
- [ ] Week 3: tests, incremental loads, orchestration
- [ ] Week 4: dashboard and documentation

## Plan for weeks 2-4 (not built yet)
**Week 2: dbt models**
- Fix schema naming first. `+schema: staging` currently creates `main_staging` (dbt's default naming), so add a `generate_schema_name` macro to get plain `staging` and `marts`.
- Staging, one model per raw table: pick the latest snapshot, split `code: label` columns, cast values and periods to typed dates (quarter end), and use Rents code `30014`.
- `int_rents_quarterly`: splice the archived quarterly capital-city rents (to 2025-Q3) onto quarterly averages of monthly rents (from 2025-Q4), rebasing on the overlap and flagging spliced quarters.
- `mart_cost_of_living_quarterly`: quarter × region with CPI, rents and WPI index values and year-on-year changes. Map capital cities to states and label it as an approximation.

**Week 3: tests and automation**
- dbt tests: not null, unique (region, quarter), accepted ranges, and source freshness against the release calendar.
- Incremental loading: only load new snapshots.
- A Prefect flow with retries and a schedule after each ABS release.
- GitHub Actions running pytest and `dbt build` against fixtures.

**Week 4: presentation.** Dashboard, architecture diagram, data dictionary, and a findings write-up.

## Data and attribution
Based on Australian Bureau of Statistics data: Consumer Price Index, Australia (6401.0) and Wage Price Index, Australia (6345.0), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
