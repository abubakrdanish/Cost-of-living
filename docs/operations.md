# How to operate this pipeline

Everything runs locally and needs no accounts or keys. Commands assume the repo root with the virtualenv active (`source .venv/bin/activate`) and `dbt_project/profiles.yml` copied from the example.

## 1. Run it once

```bash
python -m orchestration.flow                    # download, load, freshness, dbt build, report
python -m orchestration.flow --skip-download    # reuse files already in data/raw/
python -m orchestration.flow --sources wpi      # one source (cpi | rents | wpi)
```

The flow runs these steps in order:

| Step | What it does | On failure |
|---|---|---|
| Download | 4 polite requests to the ABS, one source at a time, at least 2 s apart. Identical files aren't saved again. | The HTTP client retries 5 times with backoff, then Prefect retries the source twice (after 60 s and 120 s). If it still fails, the other sources continue and the run fails at the end. |
| Load raw | New files are appended to DuckDB `raw`. Files already loaded are skipped. | dbt is skipped and the run fails. |
| `dbt source freshness` | Checks how old the newest data period is (see section 4). | Error: the run fails. Warning: it's listed in the report only. |
| `dbt build` | Builds seeds and models and runs every test (128 checks). | Any failed or errored test or model fails the run. Models downstream of a failure are **skipped and keep their previous contents**. |
| Quality report | Writes `reports/quality_report.md` and `.json`. | It's written **even when an earlier step failed**. |

**What "fails loudly" means:**
- The process exits with code 1.
- `PIPELINE FAILED: <reasons>` is printed to stderr.
- The Prefect run ends in state `Failed`.
- The report is headed `FAILED`.

To prove it, tighten a test threshold for one run: `python -m orchestration.flow --skip-download --vars '{"rents_splice_tolerance_pct": 0.3}'`.

## 2. Schedule it (local)

The schedule is **weekdays at 13:00 Australia/Sydney**. The ABS publishes at 11:30 Canberra time, so a release is picked up the same day. On days with no release, a run makes 4 small requests and changes nothing.

You need three things running:

```bash
# Terminal 1: a local Prefect server (API + UI at http://127.0.0.1:4200), data in ~/.prefect
export PREFECT_SERVER_ANALYTICS_ENABLED=false    # Prefect's server sends anonymous analytics unless you turn it off
prefect server start

# Terminal 2: register the deployment and wait for scheduled runs (runs execute in this process)
export PREFECT_API_URL=http://127.0.0.1:4200/api
python -m orchestration.serve
```

1. **The Prefect server** stores the schedule and creates the upcoming runs.
2. **The `serve` process** polls the server and executes the runs. If it isn't running, nothing executes. On Ctrl+C, the deployment's schedule is paused, and starting `serve` again resumes it.
3. **The computer must be awake at 13:00.** Missed runs aren't caught up, but the next run fetches anything missed, because ingestion is idempotent.

Useful commands (with `PREFECT_API_URL` set):

```bash
prefect deployment ls                                              # should list cost-of-living-pipeline/weekdays-1pm-sydney
prefect deployment run cost-of-living-pipeline/weekdays-1pm-sydney # run now via the schedule path
prefect flow-run ls                                                # recent and upcoming runs
```

Verified on 2026-10-14: the server created upcoming runs for Thu 15 Oct, Fri 16 Oct and Mon 19 Oct at 13:00 AEDT, and a run triggered through the deployment completed.

**Troubleshooting:**
- **No runs are scheduled.** Check the server log for `Can't evaluate bulk DML statement`. That's Prefect 3.8.8 on SQLAlchemy 2.1, and `requirements.lock` pins SQLAlchemy 2.0.54 to avoid it. Reinstall with `pip-sync requirements.lock`.
- **Prefer cron or launchd?** `python -m orchestration.flow` is a normal command that returns exit code 1 on failure, so a plain crontab entry works without a Prefect server. You lose the Prefect UI and run history, though.

## 3. Read the quality report

The latest report is `reports/quality_report.md` (and `.json`). Every run is also kept in `reports/history/`. All of these are git-ignored. To regenerate the report without running the flow: `python -m orchestration.quality_report`.

| Section | What to look for |
|---|---|
| **Warnings** | Read this first. Each line is something a person should check. "None" means a clean run. |
| Steps | The result of each step: new file or unchanged per source, rows loaded, freshness status, and dbt counts. |
| Latest period per source | The newest month or quarter of each series, and the mart's first and last quarter. |
| Freshness | The age of the newest data period vs the warn and error limits. |
| dbt build | Counts by status, and every test or model that didn't pass. |
| Raw downloads: newest vs previous | Row counts of the two newest downloads per table. Growth is normal; shrinking is a problem. |
| Changes since previous download | Observations added (new periods), removed, or **revised**, with up to 10 examples of revised values. |
| Row counts | Every table and view in each schema. |

## 4. Freshness: what it checks

Freshness measures **the age of the newest data period**: today minus the last day of the newest month or quarter. It doesn't measure when the data was downloaded. That way it catches both a broken pipeline and a late or missing ABS release.

| Source | Normal age | Warn | Error | Why |
|---|---|---|---|---|
| CPI all groups, CPI rents (monthly) | 31–61 days | > 65 days | > 95 days | A month is published about 4 weeks after it ends, so the newest month is at most about 2 months old. Warn means one release was missed; error means two. |
| WPI (quarterly) | 49–141 days | > 150 days | > 240 days | A quarter is published about 7 weeks after it ends, and the next release follows 3 months later. |
| Rents archive | n/a | none | none | A frozen release, so it's never refreshed. |

`dbt build` doesn't run freshness checks, and CI doesn't either: the fixtures age by design. They run in the flow.

## 5. When something fails

| Symptom (in the report) | Likely cause | What to do |
|---|---|---|
| `Download failed for <source>` | ABS API down (it's in beta), network issue, or the URL changed | Open the URL from the log in a browser. If the ABS is down, rerun later. If you get a 404, check the release page and the dataflow version in `docs/data_sources.md`. Don't loop retries against the ABS. |
| `Freshness WARN` | One ABS release isn't in yet | Compare with the ABS release calendar. If the release is out, rerun the flow. If the ABS is late, no action is needed. |
| `Freshness ERROR` (run fails) | Two releases missed: ingestion is broken, or the ABS changed or stopped the series | Check that recent runs actually downloaded data (Steps section). Check the dataflow still exists (`GET https://data.api.abs.gov.au/rest/dataflow/ABS/CPI`) and isn't marked CEASED. |
| `raw.<table> newest download has N fewer rows` / `assert_raw_row_counts_not_shrinking` fails | A series was dropped, the query key changed, or the download was truncated | Compare the newest and previous files in `data/raw/<source>/`. If the ABS really changed the data, update the ingestion key or the docs. If the file is just bad, delete it and its `.meta.json`, remove its rows from `raw` (`delete from raw.<table> where _source_file = '<file>'`), and rerun. |
| `assert_raw_row_count_growth_reasonable` warning | More than 25% more rows than before | Usually new ABS series. Check that the staging filters still pick the right series. |
| `N observation(s) revised` | Normal: the ABS revises recent values | No action needed. Staging uses the newest values. The table lists them if you want to note big revisions. |
| `assert_rents_splice_overlap_within_tolerance` fails | The ABS revised the archive-overlap quarters, or monthly rents behave differently | Look at `intermediate.int_rents_splice_overlap` (column `deviation_pct`). If it's a genuine methodology shift, discuss before raising `rents_splice_tolerance_pct` in `dbt_project.yml`. |
| Other `dbt test FAIL` | The data broke an assumption (range, uniqueness, gaps) | Run `dbt test --select <test> --store-failures` in `dbt_project/`, or `dbt show` the test's SQL, to see the failing rows. Fix the data or code. Only change a threshold if the data is genuinely right. |
| `dbt build failed (see dbt output in the logs)` | A compile or parse error before tests ran | Run `dbt build --profiles-dir .` by hand in `dbt_project/` to see the error. |
| `dbt model SKIPPED: mart_cost_of_living_quarterly` | Something upstream failed | The mart still holds the last good build. Fix the upstream failure and rerun. |

## 6. CI (GitHub Actions)

- **`ci.yml`** runs on every push and pull request. It installs `requirements.lock` on Ubuntu, runs `pytest` (network blocked), loads `tests/fixtures/ci_raw` and runs `dbt build`, then uploads the quality report and `run_results.json` as an artifact. It never calls the ABS.
- **`live-ingestion.yml`** is manual only (Actions tab → "Live ingestion check" → Run workflow). It runs the real flow, then checks the CI fixtures still match the real ABS file layout.
- **Keeping the fixtures current:** if `ingestion.ci_fixtures check` fails, run the ingestion locally, then `python -m ingestion.ci_fixtures generate`. Review the diff and commit. See `tests/fixtures/ci_raw/README.md`.
