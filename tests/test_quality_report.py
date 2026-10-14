import json
from datetime import datetime, timezone

import duckdb
import pytest

from orchestration import quality_report as qr

NOW = datetime(2026, 10, 14, 3, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def small_db(tmp_path):
    """A tiny warehouse: two raw snapshots (the newer one smaller), one staging view."""
    path = tmp_path / "w.duckdb"
    with duckdb.connect(str(path)) as con:
        for schema in ("raw", "staging", "intermediate", "marts"):
            con.execute(f"create schema {schema}")
        con.execute("create table raw.abs_wpi as select * from (values "
                    "('abs_wpi_20260901.csv'), ('abs_wpi_20260901.csv'), ('abs_wpi_20260901.csv'), "
                    "('abs_wpi_20261012.csv'), ('abs_wpi_20261012.csv')) t(_source_file)")
        con.execute("create view staging.stg_abs__wpi as select '2026-Q2' as time_period")
        con.execute("create table intermediate.int_raw_snapshot_changes as select * from (values "
                    "('abs_wpi', 'k1', '10.0', '10.5', 'r: revised', 'changed')) "
                    "t(raw_table, observation_key, previous_value, latest_value, latest_obs_status, change_type)")
    return path


@pytest.fixture
def artifacts(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "run_results.json").write_text(json.dumps({
        "metadata": {}, "args": {"which": "build"}, "results": [
            {"unique_id": "test.p.assert_x", "status": "fail", "failures": 3, "message": "Got 3"},
            {"unique_id": "test.p.t1", "status": "skipped", "failures": None, "message": None},
            {"unique_id": "test.p.t2", "status": "skipped", "failures": None, "message": None},
            {"unique_id": "model.p.m", "status": "success", "failures": None, "message": "OK"}]}))
    (target / "sources.json").write_text(json.dumps({"metadata": {}, "results": [
        {"unique_id": "source.p.raw.abs_wpi", "status": "warn",
         "max_loaded_at": "2026-04-30T00:00:00+00:00", "max_loaded_at_time_ago_in_s": 167 * 86400,
         "criteria": {"warn_after": {"count": 150}, "error_after": {"count": 240}}}]}))
    return target


def test_collect_reports_everything_and_never_crashes(small_db, artifacts):
    report = qr.collect({"load raw": "ok", "failures": ["Download failed for cpi: timeout"]},
                        db_path=small_db, target_dir=artifacts, now=NOW)
    assert report["status"] == "failed"
    wpi = next(s for s in report["raw_snapshots"] if s["table"] == "abs_wpi")
    assert (wpi["latest_rows"], wpi["previous_rows"], wpi["row_change"]) == (2, 3, -1)
    assert report["latest_periods"]["WPI, quarterly"] == "2026-Q2"
    assert report["latest_periods"]["Mart last quarter"] is None  # table missing: no crash

    warnings = "\n".join(report["warnings"])
    assert "Download failed for cpi" in warnings
    assert "Freshness WARN: abs_wpi" in warnings
    assert "dbt test FAIL: assert_x (3 failing rows)" in warnings
    assert "2 dbt test(s) skipped" in warnings
    assert "1 fewer rows" in warnings
    assert "1 observation(s) revised" in warnings
    assert "Latest period unavailable for: Mart last quarter" in warnings


def test_clean_run_has_no_step_warnings(small_db, tmp_path):
    report = qr.collect({"load raw": "ok", "failures": []}, db_path=small_db,
                        target_dir=tmp_path, now=NOW)
    assert report["status"] == "success"
    assert "No freshness results (dbt source freshness did not run)" in report["warnings"]


def test_missing_database_is_reported(tmp_path):
    report = qr.collect({"failures": []}, db_path=tmp_path / "none.duckdb",
                        target_dir=tmp_path, now=NOW)
    assert "DuckDB file not found: nothing could be checked" in report["warnings"]


def test_write_creates_latest_and_history(small_db, artifacts, tmp_path):
    report = qr.collect({"failures": []}, db_path=small_db, target_dir=artifacts, now=NOW)
    latest = qr.write(report, reports_dir=tmp_path / "reports")
    assert latest.read_text().startswith("# Data quality report: SUCCESS")
    history = tmp_path / "reports" / "history"
    assert (history / "quality_report_20261014T030000Z.md").exists()
    assert json.loads((history / "quality_report_20261014T030000Z.json").read_text())["status"] == "success"


def test_markdown_has_all_sections(small_db, artifacts):
    markdown = qr.render_markdown(qr.collect({"failures": []}, db_path=small_db,
                                             target_dir=artifacts, now=NOW))
    for heading in ["## Warnings", "## Steps", "## Latest period per source",
                    "## Freshness", "## dbt build", "## Raw downloads", "## Changes since",
                    "## Row counts"]:
        assert heading in markdown
