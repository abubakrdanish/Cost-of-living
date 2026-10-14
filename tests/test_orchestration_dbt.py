import json
import sys

import pytest

from orchestration import dbt
from orchestration.dbt import (
    DBT_PROJECT_DIR, build_dbt_command, ensure_profiles, summarise_freshness,
    summarise_run_results,
)


def _write(path, data):
    path.write_text(json.dumps(data))
    return path


def test_build_dbt_command_points_at_project():
    cmd = build_dbt_command(["build"], executable="dbt")
    assert cmd[:2] == ["dbt", "build"]
    assert cmd[cmd.index("--profiles-dir") + 1] == str(DBT_PROJECT_DIR)
    assert cmd[cmd.index("--project-dir") + 1] == str(DBT_PROJECT_DIR)
    assert "--vars" not in cmd


def test_build_dbt_command_serialises_vars():
    cmd = build_dbt_command(["build"], {"mart_start_quarter": "2021-07-01"}, executable="dbt")
    assert json.loads(cmd[cmd.index("--vars") + 1]) == {"mart_start_quarter": "2021-07-01"}


def test_ensure_profiles_explains_fix(tmp_path):
    with pytest.raises(FileNotFoundError, match="profiles.yml.example"):
        ensure_profiles(tmp_path)


def test_run_dbt_returns_exit_code_and_output(monkeypatch, tmp_path):
    """run_dbt never raises on a dbt failure; it reports the code and output tail."""
    fake = tmp_path / "fake_dbt.py"
    fake.write_text("import sys\nprint('line one')\nprint('Done. ERROR=1')\nsys.exit(1)\n")
    monkeypatch.setattr(dbt, "ensure_profiles", lambda: None)
    monkeypatch.setattr(dbt, "build_dbt_command",
                        lambda args, dbt_vars=None: [sys.executable, str(fake)])
    result = dbt.run_dbt(["build"])
    assert result.returncode == 1 and not result.ok
    assert result.output_tail[-1] == "Done. ERROR=1"


def test_summarise_run_results(tmp_path):
    path = _write(tmp_path / "run_results.json", {
        "metadata": {"generated_at": "2026-10-14T00:00:00Z"},
        "args": {"which": "build"},
        "results": [
            {"unique_id": "model.p.mart", "status": "success", "failures": None, "message": "OK"},
            {"unique_id": "test.p.not_null_x", "status": "pass", "failures": 0, "message": None},
            {"unique_id": "test.p.assert_y", "status": "fail", "failures": 7, "message": "Got 7"},
            {"unique_id": "test.p.warn_z", "status": "warn", "failures": 1, "message": None},
            {"unique_id": "test.p.after", "status": "skipped", "failures": None, "message": None},
        ],
    })
    summary = summarise_run_results(path)
    assert summary["command"] == "build"
    assert summary["counts"] == {"success": 1, "pass": 1, "fail": 1, "warn": 1, "skipped": 1}
    assert {p["node"] for p in summary["problems"]} == {"assert_y", "warn_z", "after"}
    assert summary["has_failures"] is True


def test_summarise_run_results_warn_only_is_not_failure(tmp_path):
    path = _write(tmp_path / "run_results.json", {"metadata": {}, "args": {"which": "build"},
        "results": [{"unique_id": "test.p.w", "status": "warn", "failures": 2, "message": None}]})
    assert summarise_run_results(path)["has_failures"] is False


def test_summarise_missing_artifacts(tmp_path):
    assert summarise_run_results(tmp_path / "nope.json") is None
    assert summarise_freshness(tmp_path / "nope.json") is None


def test_summarise_freshness(tmp_path):
    def result(name, status, age_days):
        return {"unique_id": f"source.p.raw.{name}", "status": status,
                "max_loaded_at": "2026-08-31T00:00:00+00:00",
                "max_loaded_at_time_ago_in_s": age_days * 86400,
                "criteria": {"warn_after": {"count": 65, "period": "day"},
                             "error_after": {"count": 95, "period": "day"}}}
    path = _write(tmp_path / "sources.json", {"metadata": {}, "results": [
        result("abs_cpi_rents", "pass", 44), result("abs_wpi", "warn", 70),
        result("abs_cpi_all_groups", "error", 100)]})
    summary = summarise_freshness(path)
    by_source = {s["source"]: s for s in summary["sources"]}
    assert by_source["abs_cpi_rents"] == {
        "source": "abs_cpi_rents", "status": "pass", "newest_period_end": "2026-08-31",
        "age_days": 44.0, "warn_after_days": 65, "error_after_days": 95, "message": None}
    assert summary["has_errors"] and summary["has_warnings"]
