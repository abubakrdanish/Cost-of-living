"""The Prefect flow, run for real on a temporary local Prefect server, with every
step that touches the network, DuckDB or dbt replaced by a fake."""
from __future__ import annotations

import pytest

from orchestration import flow as flow_module
from orchestration.dbt import DbtResult
from orchestration.flow import (
    PipelineFailed, cost_of_living_pipeline, describe_build, describe_freshness,
)
from ingestion.raw_files import SaveResult


@pytest.fixture(scope="session")
def prefect_server():
    from prefect.testing.utilities import prefect_test_harness
    with prefect_test_harness():
        yield


def _freshness(status="pass"):
    return {"sources": [{"source": "abs_wpi", "status": status, "newest_period_end": "2026-06-30",
                         "age_days": 106.0, "error_after_days": 240}],
            "has_errors": status == "error", "has_warnings": status == "warn"}


def _build(failed=False):
    problems = [{"node": "assert_x", "type": "test", "status": "fail", "failures": 3}] if failed else []
    return {"counts": {"pass": 10, **({"fail": 1} if failed else {})},
            "problems": problems, "has_failures": failed}


class FakePipeline:
    """Records calls and plays back canned results for each step."""

    def __init__(self, monkeypatch, tmp_path, *, download_fails=(), load_fails=False,
                 freshness="pass", build_fails=False):
        self.calls: list[str] = []
        self.report_steps: dict | None = None

        def fake_fetch(dataset, client):
            self.calls.append(f"fetch {dataset.name}")
            if dataset.source in download_fails:
                raise ConnectionError("ABS unreachable")
            return SaveResult(path=tmp_path / f"{dataset.name}.csv", written=False)

        def fake_load_all(datasets):
            self.calls.append("load")
            return [d.name for d in datasets] if load_fails else []

        def fake_run_dbt(args, dbt_vars=None):
            self.calls.append("dbt " + " ".join(args))
            return DbtResult(command=["dbt", *args], returncode=1 if build_fails else 0)

        def fake_write(report, reports_dir=None):
            self.report_steps = report["steps"]
            return tmp_path / "quality_report.md"

        monkeypatch.setattr(flow_module, "fetch", fake_fetch)
        monkeypatch.setattr(flow_module, "load_all", fake_load_all)
        monkeypatch.setattr(flow_module, "run_dbt", fake_run_dbt)
        monkeypatch.setattr(flow_module, "summarise_freshness", lambda path: _freshness(freshness))
        monkeypatch.setattr(flow_module, "summarise_run_results",
                            lambda path: {**_build(build_fails), "command": "build"})
        monkeypatch.setattr(flow_module.quality_report, "collect",
                            lambda steps: {"steps": steps})
        monkeypatch.setattr(flow_module.quality_report, "write", fake_write)
        # No real waiting between retries in tests.
        monkeypatch.setattr(flow_module, "download_source",
                            flow_module.download_source.with_options(retries=0))


# ---- Pure outcome rules ----------------------------------------------------------

def test_describe_freshness_errors_only_on_error():
    assert describe_freshness(_freshness("warn"))[1] == []
    _, errors = describe_freshness(_freshness("error"))
    assert errors and "Freshness ERROR: abs_wpi" in errors[0]
    assert describe_freshness(None)[1] == ["dbt source freshness produced no results"]


def test_describe_build():
    assert describe_build(_build(False)) == ("pass=10", [])
    assert describe_build(_build(True))[1] == ["dbt test fail: assert_x"]
    crashed = {"counts": {}, "problems": [], "has_failures": True}
    assert describe_build(crashed)[1] == ["dbt build failed (see dbt output in the logs)"]


def test_download_task_retries_with_backoff():
    task = flow_module.download_source
    assert task.retries == 2
    assert flow_module.DOWNLOAD_RETRY_DELAYS(2)[:2] == [60, 120]


# ---- The flow end to end (fakes, real Prefect engine) ------------------------------

def test_flow_succeeds_and_writes_report(prefect_server, monkeypatch, tmp_path):
    fake = FakePipeline(monkeypatch, tmp_path)
    result = cost_of_living_pipeline()
    assert fake.calls[-3:] == ["load", "dbt source freshness", "dbt build"]
    assert sum(c.startswith("fetch") for c in fake.calls) == 4  # every dataset, one at a time
    assert result["report"] == str(tmp_path / "quality_report.md")
    assert fake.report_steps["failures"] == []


def test_flow_fails_loudly_when_a_dbt_test_fails(prefect_server, monkeypatch, tmp_path):
    fake = FakePipeline(monkeypatch, tmp_path, build_fails=True)
    with pytest.raises(PipelineFailed, match="dbt test fail: assert_x"):
        cost_of_living_pipeline(skip_download=True)
    assert fake.report_steps is not None, "report must be written even when the run fails"
    assert fake.report_steps["failures"] == ["dbt test fail: assert_x"]


def test_flow_fails_on_freshness_error_but_not_warning(prefect_server, monkeypatch, tmp_path):
    FakePipeline(monkeypatch, tmp_path, freshness="warn")
    cost_of_living_pipeline(skip_download=True)  # warning: no exception
    FakePipeline(monkeypatch, tmp_path, freshness="error")
    with pytest.raises(PipelineFailed, match="Freshness ERROR"):
        cost_of_living_pipeline(skip_download=True)


def test_failed_download_still_builds_then_fails(prefect_server, monkeypatch, tmp_path):
    fake = FakePipeline(monkeypatch, tmp_path, download_fails={"abs_wpi"})
    with pytest.raises(PipelineFailed, match="Download failed for wpi"):
        cost_of_living_pipeline()
    assert "dbt build" in fake.calls  # other sources were still processed
    assert fake.report_steps["download wpi"].startswith("FAILED")


def test_failed_load_skips_dbt(prefect_server, monkeypatch, tmp_path):
    fake = FakePipeline(monkeypatch, tmp_path, load_fails=True)
    with pytest.raises(PipelineFailed, match="Raw load failed"):
        cost_of_living_pipeline(skip_download=True)
    assert not any(c.startswith("dbt") for c in fake.calls)
    assert fake.report_steps is not None


def test_cli_returns_exit_code_1_on_failure(prefect_server, monkeypatch, tmp_path, capsys):
    FakePipeline(monkeypatch, tmp_path, build_fails=True)
    assert flow_module.main(["--skip-download"]) == 1
    assert "PIPELINE FAILED" in capsys.readouterr().err
