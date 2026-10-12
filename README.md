# Australian Cost-of-Living Pipeline

An end-to-end data engineering portfolio project: ingest public Australian economic data, transform and test it with dbt, store it in DuckDB, and serve it in a dashboard.

**Question:** How have rents, wages and inflation changed over time, by state?

> Personal portfolio project using public data only. Not financial or immigration advice.

## Stack
- **Warehouse:** DuckDB (local, free)
- **Transform and tests:** dbt Core (dbt-duckdb)
- **Orchestration:** Prefect
- **Dashboard:** Evidence, Metabase or Looker Studio (decide in week 4)
- **Language:** Python

## Architecture (planned)
`ABS / data.gov.au` -> `ingestion/` -> `data/raw/` -> DuckDB `raw` schema -> dbt `staging` -> dbt `marts` -> dashboard

## Project structure
| Folder | Purpose |
|---|---|
| `data/raw/` | Downloaded source files (not committed) |
| `warehouse/` | Local DuckDB file (not committed) |
| `ingestion/` | Download and load scripts |
| `dbt_project/` | Staging and mart models, tests |
| `orchestration/` | Scheduled Prefect flows |
| `docs/` | Data sources, data dictionary, diagrams |

## Setup
1. Create a virtual environment and activate it.
2. `pip install -r requirements.txt`
3. `python ingestion/init_duckdb.py` to create the local database and schemas.
4. Copy `dbt_project/profiles.yml.example` to `dbt_project/profiles.yml`.
5. From `dbt_project/`, run `dbt debug` to confirm the connection.

## Progress
- [x] Day 1: project scaffold and DuckDB initialised
- [ ] Week 1: ingest three datasets
- [ ] Week 2: dbt staging and mart models
- [ ] Week 3: tests, incremental loads, orchestration
- [ ] Week 4: dashboard and documentation

## Data sources
See `docs/data_sources.md`.
