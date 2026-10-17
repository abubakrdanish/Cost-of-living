"""Data quality report written after every pipeline run.

Writes reports/quality_report.md and .json, plus a timestamped copy in
reports/history/. A missing table or dbt artifact is reported as unavailable
rather than raising, so a failed run still produces a report.

Run on its own: python -m orchestration.quality_report
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from ingestion.config import DB_PATH, PROJECT_ROOT
from orchestration.dbt import (
    RUN_RESULTS, SOURCES, TARGET_DIR, summarise_freshness, summarise_run_results,
)

log = logging.getLogger(__name__)

REPORTS_DIR = PROJECT_ROOT / "reports"
SCHEMAS = ("raw", "reference", "staging", "intermediate", "marts")
SNAPSHOT_TABLES = ("abs_cpi_all_groups", "abs_cpi_rents",
                   "abs_cpi_capital_cities_quarterly_2025q3", "abs_wpi")

# Label -> query returning one value, for "Latest period per source".
LATEST_PERIOD_QUERIES = {
    "CPI all groups, monthly": "select max(time_period) from staging.stg_abs__cpi_all_groups where frequency_code = 'M'",
    "CPI all groups, quarterly": "select max(time_period) from staging.stg_abs__cpi_all_groups where frequency_code = 'Q'",
    "CPI rents, monthly": "select max(time_period) from staging.stg_abs__cpi_rents where frequency_code = 'M'",
    "CPI rents, last complete quarter": (
        "select strftime(max(quarter_start_date), '%Y') || '-Q' || quarter(max(quarter_start_date)) "
        "from intermediate.int_rents_monthly_to_quarterly"),
    "Rents archive (frozen)": (
        "select strftime(max(quarter_start_date), '%Y') || '-Q' || quarter(max(quarter_start_date)) "
        "from staging.stg_abs__cpi_rents_archive"),
    "WPI, quarterly": "select max(time_period) from staging.stg_abs__wpi",
    "Mart first quarter": "select min(quarter_label) from marts.mart_cost_of_living_quarterly",
    "Mart last quarter": "select max(quarter_label) from marts.mart_cost_of_living_quarterly",
}


def _scalar(con: duckdb.DuckDBPyConnection, sql: str):
    try:
        row = con.execute(sql).fetchone()
        return row[0] if row else None
    except duckdb.Error:
        return None


def table_row_counts(con: duckdb.DuckDBPyConnection) -> list[dict]:
    placeholders = ", ".join("?" for _ in SCHEMAS)
    tables = con.execute(
        "select table_schema, table_name, table_type from information_schema.tables "
        f"where table_catalog = current_database() and table_schema in ({placeholders}) "
        "order by table_schema, table_name", list(SCHEMAS)).fetchall()
    order = {s: i for i, s in enumerate(SCHEMAS)}
    rows = [{"schema": s, "table": t, "type": "view" if ty == "VIEW" else "table",
             "rows": _scalar(con, f'select count(*) from "{s}"."{t}"')} for s, t, ty in tables]
    return sorted(rows, key=lambda r: (order[r["schema"]], r["table"]))


def raw_snapshots(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Rows in the newest download vs the one before, per raw table."""
    result = []
    for table in SNAPSHOT_TABLES:
        try:
            files = con.execute(
                f"select _source_file, count(*) from raw.{table} "
                "group by 1 order by 1 desc limit 2").fetchall()
        except duckdb.Error:
            continue
        latest = files[0] if files else (None, None)
        previous = files[1] if len(files) > 1 else (None, None)
        result.append({
            "table": table, "snapshots": _scalar(con, f"select count(distinct _source_file) from raw.{table}"),
            "latest_file": latest[0], "latest_rows": latest[1],
            "previous_file": previous[0], "previous_rows": previous[1],
            "row_change": (latest[1] - previous[1]) if previous[1] is not None else None,
        })
    return result


def snapshot_changes(con: duckdb.DuckDBPyConnection) -> dict | None:
    try:
        counts = con.execute(
            "select raw_table, change_type, count(*) from intermediate.int_raw_snapshot_changes "
            "group by all order by all").fetchall()
        examples = con.execute(
            "select raw_table, observation_key, previous_value, latest_value, latest_obs_status "
            "from intermediate.int_raw_snapshot_changes where change_type = 'changed' "
            "order by raw_table, observation_key limit 10").fetchall()
    except duckdb.Error:
        return None
    return {
        "counts": [{"table": t, "change_type": c, "rows": n} for t, c, n in counts],
        "changed_examples": [
            {"table": t, "observation": k, "previous": p, "latest": v, "abs_status": s}
            for t, k, p, v, s in examples],
    }


def collect(steps: dict, db_path: Path = DB_PATH, target_dir: Path = TARGET_DIR,
            now: datetime | None = None) -> dict:
    """Gather everything the report shows. `steps` holds the flow's step results."""
    now = now or datetime.now(timezone.utc)
    report: dict = {
        "generated_at_utc": now.isoformat(timespec="seconds"),
        "status": "failed" if steps.get("failures") else "success",
        "steps": steps,
        "row_counts": [], "raw_snapshots": [], "latest_periods": {},
        "snapshot_changes": None,
        "freshness": summarise_freshness(target_dir / SOURCES),
        "dbt_build": summarise_run_results(target_dir / RUN_RESULTS),
    }
    if db_path.exists():
        with duckdb.connect(str(db_path), read_only=True) as con:
            report["row_counts"] = table_row_counts(con)
            report["raw_snapshots"] = raw_snapshots(con)
            report["latest_periods"] = {k: _scalar(con, q) for k, q in LATEST_PERIOD_QUERIES.items()}
            report["snapshot_changes"] = snapshot_changes(con)
    report["warnings"] = find_warnings(report, db_exists=db_path.exists())
    return report


def find_warnings(report: dict, db_exists: bool = True) -> list[str]:
    """Plain-English list of everything a person should look at."""
    # Step failures about dbt or freshness are listed in more detail below.
    warnings = [f for f in report["steps"].get("failures", [])
                if not f.startswith(("dbt ", "Freshness ERROR"))]
    if not db_exists:
        warnings.append("DuckDB file not found: nothing could be checked")
    freshness = report["freshness"]
    if freshness is None:
        warnings.append("No freshness results (dbt source freshness did not run)")
    else:
        for s in freshness["sources"]:
            if s["status"] != "pass":
                warnings.append(
                    f"Freshness {s['status'].upper()}: {s['source']} newest period ends "
                    f"{s['newest_period_end']} ({s['age_days']} days old; warn > "
                    f"{s['warn_after_days']}, error > {s['error_after_days']})")
    build = report["dbt_build"]
    if build is None:
        warnings.append("No dbt build results (dbt build did not run)")
    else:
        skipped_tests = 0
        for p in build["problems"]:
            if p["status"] == "skipped" and p["type"] == "test":
                skipped_tests += 1
                continue
            warnings.append(f"dbt {p['type']} {p['status'].upper()}: {p['node']}"
                            + (f" ({p['failures']} failing rows)" if p["failures"] else ""))
        if skipped_tests:
            warnings.append(f"{skipped_tests} dbt test(s) skipped because something upstream "
                            "failed; skipped models keep their previous contents")
    for snap in report["raw_snapshots"]:
        if snap["row_change"] is not None and snap["row_change"] < 0:
            warnings.append(f"raw.{snap['table']} newest download has {-snap['row_change']} "
                            "fewer rows than the previous one")
    for label, value in report["latest_periods"].items():
        if value is None:
            warnings.append(f"Latest period unavailable for: {label}")
    changes = report["snapshot_changes"]
    if changes:
        revised = sum(c["rows"] for c in changes["counts"] if c["change_type"] == "changed")
        if revised:
            warnings.append(f"{revised} observation(s) revised since the previous download "
                            "(see 'Changes since previous download'); staging uses the new values")
    return warnings


def _table(headers: list[str], rows: list[list]) -> str:
    def cell(v):
        return "" if v is None else (f"{v:,}" if isinstance(v, int) and not isinstance(v, bool) else str(v))
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def render_markdown(report: dict) -> str:
    out = [f"# Data quality report: {report['status'].upper()}",
           f"Generated {report['generated_at_utc']} (UTC).", ""]

    out += ["## Warnings"]
    out += [f"- {w}" for w in report["warnings"]] or ["- None"]
    out += [""]

    out += ["## Steps", _table(["Step", "Result"], [[k, v] for k, v in report["steps"].items()
                                                   if k != "failures"]), ""]

    out += ["## Latest period per source",
            _table(["Source", "Latest"], [[k, v] for k, v in report["latest_periods"].items()]), ""]

    fresh = report["freshness"]
    out += ["## Freshness (age of newest data period)"]
    out += [_table(["Source", "Status", "Newest period ends", "Age (days)", "Warn after", "Error after"],
                   [[s["source"], s["status"], s["newest_period_end"], s["age_days"],
                     s["warn_after_days"], s["error_after_days"]] for s in fresh["sources"]])
            if fresh else "Not available."]
    out += [""]

    build = report["dbt_build"]
    out += ["## dbt build"]
    if build:
        out += ["Results: " + ", ".join(f"{k}={v}" for k, v in sorted(build["counts"].items()))]
        if build["problems"]:
            out += ["", _table(["Node", "Type", "Status", "Failing rows", "Message"],
                               [[p["node"], p["type"], p["status"], p["failures"], p["message"]]
                                for p in build["problems"]])]
    else:
        out += ["Not available."]
    out += [""]

    out += ["## Raw downloads: newest vs previous",
            _table(["Raw table", "Snapshots", "Newest file", "Rows", "Previous file", "Rows", "Change"],
                   [[s["table"], s["snapshots"], s["latest_file"], s["latest_rows"],
                     s["previous_file"], s["previous_rows"], s["row_change"]]
                    for s in report["raw_snapshots"]]), ""]

    changes = report["snapshot_changes"]
    out += ["## Changes since previous download"]
    if changes is None:
        out += ["Not available."]
    elif not changes["counts"]:
        out += ["No changes (or only one download so far)."]
    else:
        out += [_table(["Raw table", "Change", "Observations"],
                       [[c["table"], c["change_type"], c["rows"]] for c in changes["counts"]])]
        if changes["changed_examples"]:
            out += ["", "Revised values (up to 10):", "",
                    _table(["Raw table", "Observation", "Previous", "Latest", "ABS status"],
                           [[e["table"], e["observation"], e["previous"], e["latest"], e["abs_status"]]
                            for e in changes["changed_examples"]])]
    out += [""]

    out += ["## Row counts", _table(["Schema", "Table", "Type", "Rows"],
                                    [[r["schema"], r["table"], r["type"], r["rows"]]
                                     for r in report["row_counts"]]), ""]
    return "\n".join(out)


def write(report: dict, reports_dir: Path = REPORTS_DIR) -> Path:
    """Write latest + timestamped copies. Returns the latest Markdown path."""
    history = reports_dir / "history"
    history.mkdir(parents=True, exist_ok=True)
    stamp = report["generated_at_utc"].replace("-", "").replace(":", "").replace("+0000", "Z")
    markdown = render_markdown(report)
    as_json = json.dumps(report, indent=2, default=str)
    for directory, name in [(reports_dir, "quality_report"), (history, f"quality_report_{stamp}")]:
        (directory / f"{name}.md").write_text(markdown, encoding="utf-8")
        (directory / f"{name}.json").write_text(as_json, encoding="utf-8")
    latest = reports_dir / "quality_report.md"
    log.info("Quality report: %s (%s, %d warning(s))", latest, report["status"], len(report["warnings"]))
    return latest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    path = write(collect(steps={"note": "standalone report (no flow run)"}))
    print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
