# Australian Cost-of-Living Pipeline

[![CI](https://github.com/abubakrdanish/Cost-of-living/actions/workflows/ci.yml/badge.svg)](https://github.com/abubakrdanish/Cost-of-living/actions/workflows/ci.yml)

How have rents, wages and inflation changed over time, by state and capital city in Australia?

This project pulls official Australian Bureau of Statistics (ABS) data, keeps the raw files unchanged, models them with dbt in DuckDB and tests every layer (128 dbt checks, 70 offline Python tests). A Prefect flow runs it on a local schedule, GitHub Actions tests every change, and an Evidence dashboard shows the results. Everything is free, runs locally and needs no accounts or keys.

![Dashboard overview: latest annual change in prices, rents and wages for Australia, and key findings](docs/images/overview.png)

![Line chart of prices, rents and wages for Australia since 1997, each indexed to 100 in 1997-Q3](docs/images/over-time.png)

![Line chart of annual rent growth for Australia, with the 2025-Q4 splice point marked](docs/images/rents.png)

> Personal portfolio project using public data only. Not financial advice.

## Findings

As of the June quarter 2026 data, covering 1997-Q3 to 2026-Q2. Each figure comes from a named query in [`docs/findings_queries.sql`](docs/findings_queries.sql), shown in brackets after each finding (F1 to F8); `python -m orchestration.findings` re-runs them. [`docs/findings.md`](docs/findings.md) has the full table and what the data does not show.

1. Over the whole period, wages rose a little faster than prices. In Australia, prices rose +121.1%, rents +139.4% and wages +141.7%, so wages relative to prices ended 9.3% higher. (query F1)
2. Most of that gain was lost after 2021. Wages relative to prices peaked in 2020-Q2 and fell 7.4% to a low in 2023-Q2. Real wage growth was negative for 10 quarters in a row, from 2021-Q2 to 2023-Q3. The 2020 peak partly reflects a temporary COVID-period dip in prices. (queries F2, F4)
3. Prices are again outpacing wages in every region. Real wage growth has been negative since 2025-Q4, and in 2026-Q2 it was below zero in all 9 regions, from −0.47 points (Victoria) to −1.77 (Tasmania). (queries F4, F5)
4. Rent growth varied widely by capital. Since 1997-Q3 rents rose +155.5% in Brisbane but +90.5% in Darwin. Rents outpaced the state's wages only in Brisbane and Sydney. (query F6)

These describe how the indexes moved, not why. They are index changes, not dollar levels or affordability, and CPI rents are not advertised market rents.

## Architecture

```mermaid
flowchart TB
    subgraph ABS["ABS: public data, CC BY 4.0"]
        API["ABS Data API<br/>CPI 2.0.0 and WPI 1.2.0"]
        XLSX["Final quarterly CPI<br/>Table 9 (XLSX)"]
    end

    subgraph ING["ingestion/ (Python)"]
        DL["Download<br/>polite HTTP, retries"]
        FILES[("data/raw/<br/>unchanged, date-stamped")]
    end

    subgraph WH["DuckDB warehouse, modelled with dbt"]
        RAW[("raw<br/>append-only snapshots")]
        STG["staging<br/>latest snapshot, typed"]
        INT["intermediate<br/>rents splice, snapshot diff"]
        MART[("marts<br/>mart_cost_of_living_quarterly<br/>dim_region, dim_quarter<br/>mart_rents_splice_check")]
    end

    DASH["dashboard/ (Evidence)<br/>static site, reads marts only"]
    REPORT["reports/<br/>quality_report.md"]

    API --> DL
    XLSX --> DL
    DL --> FILES --> RAW --> STG --> INT --> MART
    STG --> MART
    MART --> DASH

    PREFECT(["Prefect flow<br/>weekdays 13:00 Sydney"])
    PREFECT -. "1. download + load" .-> DL
    PREFECT -. "2. freshness + dbt build (tests)" .-> WH
    PREFECT -. "3. write" .-> REPORT

    CI(["GitHub Actions CI<br/>every push and PR"])
    FIX[("tests/fixtures/ci_raw<br/>trimmed real ABS files")]
    FIX --> CI
    CI -. "pytest + dbt build, no live ABS calls" .-> WH
```

## Tech stack

| Tool | Why |
|---|---|
| Python 3.12 + `requests` | Typed ingestion with retries, timeouts and a polite request rate. |
| DuckDB | A single-file analytical database with no server. dbt and Evidence both read it directly. |
| dbt Core (dbt-duckdb) | SQL models with tests, docs and lineage, so each layer can be tested. |
| Prefect 3 | One local flow with retries, logs, a cron schedule and a local UI. No cloud; analytics are off. |
| pytest | 70 tests that run offline (external network is blocked in tests). |
| GitHub Actions | Free CI that runs pytest and `dbt build` against small committed fixtures, never the live ABS. |
| Evidence 40 (pinned) | Dashboards as SQL and Markdown, built to a static site that reads DuckDB read-only. |
| pip-tools | A readable `requirements.txt` and a fully pinned `requirements.lock`. |

## Run it from scratch

You need Python 3.12, Node.js 18 or newer (tested on 22) and git, on macOS or Linux.

```bash
git clone https://github.com/abubakrdanish/Cost-of-living.git && cd Cost-of-living
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
cp dbt_project/profiles.yml.example dbt_project/profiles.yml
python ingestion/init_duckdb.py
python -m orchestration.flow          # download ABS data (4 requests), load, freshness, dbt build, quality report
pytest                                # 70 offline tests
```

The flow exits with code 1 and prints `PIPELINE FAILED` if any test or freshness check fails. It always writes `reports/quality_report.md`.

### View the dashboard locally

```bash
cd dashboard
npm ci                                # exact pinned versions from the lock file
npm run sources                       # read the marts (read-only)
npm run dev                           # live preview: http://localhost:3000
# or build the static site and serve it:
npm run build:strict && npm run preview
```

### Schedule it (optional)

```bash
PREFECT_SERVER_ANALYTICS_ENABLED=false prefect server start                # terminal 1
PREFECT_API_URL=http://127.0.0.1:4200/api python -m orchestration.serve    # terminal 2
```

It runs on weekdays at 13:00 Australia/Sydney while both processes are running and the computer is awake. See [`docs/operations.md`](docs/operations.md).

### Publish the dashboard on GitHub Pages (manual, optional)

Nothing deploys automatically. To publish a copy yourself:

```bash
# 1. Build with the repo name as base path (GitHub project pages live under /<your-repo>/)
cd dashboard
cp evidence.config.yaml /tmp/evidence.config.yaml.bak
printf '\ndeployment:\n  basePath: /%s\n' "<your-repo>" >> evidence.config.yaml
npm run sources && npm run build:strict
cp /tmp/evidence.config.yaml.bak evidence.config.yaml   # restore the local config

# 2. Put the built files on an orphan gh-pages branch, from a separate clone
cd /tmp && git clone https://github.com/<your-github-user>/<your-repo>.git site && cd site
git switch --orphan gh-pages
cp -R "<path-to-your-repo>/dashboard/build/." .
touch .nojekyll                                 # keep the _app/ folder (GitHub Pages would hide it)
git add . && git commit -m "Publish dashboard" && git push origin gh-pages
```

Then, in the repository's Settings → Pages, deploy from the `gh-pages` branch, `(root)` folder. The published site contains the mart data (public ABS data, CC BY 4.0), and viewers' browsers fetch DuckDB's Parquet extension from `extensions.duckdb.org`.

## Design decisions

**Splicing the rents series.** The ABS moved the CPI to monthly in late 2025 and stopped publishing quarterly capital-city tables after 2025-Q3, while monthly city rents only go back to 2022-07. The rents series therefore joins the archived quarterly series (to 2025-Q3) to quarterly averages of the monthly series (from 2025-Q4), linked at 2025-Q3. In the overlap the two drift apart by 0.14% to 0.41%. That gap is measured in `mart_rents_splice_check`, tested against a 0.5% tolerance and flagged on every affected row. Details: [`docs/data_dictionary.md`](docs/data_dictionary.md#how-the-rents-splice-works).

**Rebasing to 1997-Q3 = 100.** The three series use different bases (Sep 2025, 2008-09 and 2011-12). 1997-Q3 is the first quarter in which all three exist, because the WPI starts then. Rebasing there makes every line start together, so charts read as cumulative change. Annual % changes are unaffected.

**No dbt incremental models.** A full dbt build takes about 4 seconds, and the ABS revises history, so staging must re-read the newest download in full. Incremental models would need merge keys and frequent full refreshes for no gain. Incremental loading happens in the raw loader instead, which appends each new file once.

**Evidence, pinned at 40.1.8.** Evidence keeps dashboards in git as SQL and Markdown, reads DuckDB read-only and builds a plain static site. In August 2026 Evidence moved to a new CLI tied to its cloud product, so the project pins the last open-source npm release and installs it from the lock file. That release is frozen and its build toolchain has 58 known npm advisories; see [`dashboard/README.md`](dashboard/README.md).

**Telemetry off.** Prefect's server, dbt and Evidence each send anonymous usage data by default. All three are switched off. Evidence's telemetry module is also replaced with a no-op, because its environment-variable opt-out is ignored on the code paths that send events.

**Every number traces to a query.** Deriving the findings from queries caught two errors in earlier versions of the docs: the real-wage approximation error is 0.40 points, not about 0.3, and the ABS revision flags were on a series the project does not use.

## Limitations

- CPI and rents are measured for capital cities and the WPI for whole states, so each region's comparison is an approximation.
- CPI rents cover all renting households, net of Commonwealth Rent Assistance, so CRA increases push them down. They are not market rents.
- Annual rent changes from 2025-Q4 compare the new and archived series, so treat them as ±0.4 points.
- Real wage growth is a simple difference (WPI % − CPI %). The exact ratio form differs by up to 0.40 points (2022-Q4).
- Original series only. The WPI is the price of labour for the same jobs, not average earnings.
- ABS revisions change recent values. The pipeline keeps every download and reports what changed.
- Hobart rents fell in the December quarter 2024, and the cause hasn't been verified.

The full list is in [`docs/data_dictionary.md`](docs/data_dictionary.md#known-limitations) and on the dashboard's Methodology page.

## What I would improve next

- Self-host DuckDB's Parquet extension in the static site, so viewers' browsers contact no third-party host.
- Move off the frozen Evidence 40, either to the new Evidence or to a small Python static-site generator, and clear the npm advisories.
- Add a dollar-level view (for example ABS median rents or average weekly earnings) to show affordability, not just growth.
- Add regional (non-capital) data where the ABS publishes it, to narrow the city-versus-state approximation.
- Build and publish the dashboard in CI as a manual-approval GitHub Pages workflow.

## Project structure

| Path | Purpose |
|---|---|
| `ingestion/` | Download and load code, one module per source, plus the CI fixture tool |
| `dbt_project/` | Seeds; staging, intermediate and mart models; generic and singular tests; freshness |
| `orchestration/` | Prefect flow and schedule, dbt runner, quality report, findings runner |
| `dashboard/` | Evidence site: `sources/` (marts only) and `pages/` |
| `tests/` | Offline pytest suite and CI fixtures |
| `docs/` | Data sources, data dictionary, operations guide, findings and their queries |
| `.github/workflows/` | `ci.yml` (every push and PR), `live-ingestion.yml` (manual) |

## Data and attribution

Based on Australian Bureau of Statistics data: Consumer Price Index, Australia (6401.0) and Wage Price Index, Australia (6345.0), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The figures shown are derived (rebased, averaged, spliced and differenced) and are not ABS publications. Dataflow IDs, URLs and licence notes are in [`docs/data_sources.md`](docs/data_sources.md).

The code is released under the MIT License (see [`LICENSE`](LICENSE)). The ABS data keeps its own CC BY 4.0 licence.
