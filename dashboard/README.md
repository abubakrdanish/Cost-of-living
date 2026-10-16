# Dashboard (Evidence)

A static site with five pages: Overview, Prices, rents and wages over time, Real wage growth, Rents, and Methodology and limitations. It is built with [Evidence](https://github.com/evidence-dev/evidence) (SQL + Markdown) from the pipeline's DuckDB warehouse.

## Run it

You need the warehouse built first (from the repo root: `python -m orchestration.flow`) and Node.js 18 or newer (tested on Node 22.23.1).

```bash
cd dashboard
npm ci                 # exact versions from package-lock.json (about 720 MB in node_modules)
npm run sources        # read the marts (read-only) into the site's data files
npm run dev            # live preview at http://localhost:3000
npm run build:strict   # static site in dashboard/build/ (fails on any query or component error)
npm run preview        # serve the built site locally
```

`build/` is plain static files. You can host it anywhere static (for example GitHub Pages; see the main README for manual steps) or open it with any local web server.

## What it reads

- **Marts only.** `sources/marts/*.sql` select from `marts.mart_cost_of_living_quarterly`, `marts.dim_region` and `marts.mart_rents_splice_check`. `tests/test_dashboard_sources.py` fails if any source query references another schema.
- **Read-only.** The Evidence DuckDB connector opens any database file in `READ_ONLY` mode. Run `npm run sources` when the pipeline is not writing to the warehouse; DuckDB allows one writer at a time.
- Page queries (the `sql` blocks in `pages/*.md`) run in the browser against the extracted data, not against the warehouse.

## Why this Evidence version (pinned)

On 2026-08-20 Evidence replaced its npm workflow with a new CLI tied to Evidence Studio: installed with `curl | sh`, self-hosting runs as a Docker server rather than static files, and local DuckDB support is not documented. The project therefore pins the last open-source npm release, **`@evidence-dev/evidence` 40.1.8** (MIT, released 2026-02-06), installed only with `npm ci` from the committed lock file.

- A fresh `npm install` without the lock fails today: it resolves TypeScript 7, which Evidence 40's peer ranges reject. Always use `npm ci`.
- `npm audit` reports known advisories in this frozen toolchain (58 on 2026-10-16, 9 critical). They affect the local build tools, not the generated static pages, but don't run `npm run dev` exposed to a network.
- Upstream will not fix these. If the project moves on, the options are the new Evidence CLI or a small Python static-site generator.

## Privacy and network use

- **Evidence telemetry is off, two ways.** Evidence 40 sends anonymous usage events to Segment by default (on every build, sources run and dev-server start). They contain an MD5 of your home directory path, hashed source and query names, OS and Node version.
  1. `package.json` overrides `@evidence-dev/telemetry` with the local no-op in `vendor/telemetry-noop/`. Check with `npm ls @evidence-dev/telemetry` (shows `2.1.3-noop`) and `npm ls @segment/analytics-node` (empty).
  2. `evidence.settings.json` sets the documented opt-out, `"send_anonymous_usage_stats": "no"`.
  The `SEND_ANONYMOUS_USAGE_STATS` environment variable is **not** enough on its own: Evidence ignores it on these code paths.
- **One external request from the built site.** When the site opens, the viewer's browser downloads DuckDB's Parquet extension (`parquet.duckdb_extension.wasm`) from `https://extensions.duckdb.org`, so that the in-browser DuckDB can read the data files. It is a static file from DuckDB's official CDN, not tracking, but it does mean the viewer's browser contacts that host. This was observed with a headless browser on 2026-10-16; no other external host was contacted.

## Chart rules used

- Colour follows the entity on every page: prices (CPI) blue, rents orange, wages (WPI) aqua. These are slots 1 to 3 of a colour-blind-safe palette, validated for all pairs in light and dark mode, with separate dark-mode steps (see `evidence.config.yaml`).
- Colour is never the only cue. Prices are solid lines, rents dashed and wages dotted; every chart has a legend or a single named series, and a data table.
- One y-axis per chart (no dual axes). Bar charts start at zero. Index charts state the base: 1997-Q3 = 100.
- Missing values are gaps, not zeros (`handleMissing=gap`). Every chart has a source line with the CC BY 4.0 attribution.
