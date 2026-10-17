"""The pipeline as one Prefect flow: download, load raw, dbt source freshness,
dbt build, then the quality report (written even when an earlier step fails).

The run fails (PipelineFailed, exit code 1) if a download or load fails, a dbt
model or test fails, or a source is past its freshness error threshold.
Freshness warnings only go in the report. Usage: docs/operations.md.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field

# Prefect reads settings at import time, so set these first: no anonymous
# analytics from a local server, and send our loggers to Prefect's run logs.
os.environ.setdefault("PREFECT_SERVER_ANALYTICS_ENABLED", "false")
os.environ.setdefault("PREFECT_LOGGING_EXTRA_LOGGERS", "ingestion,orchestration")
# Those loggers also run outside flows (e.g. in tests); don't warn about it.
os.environ.setdefault("PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW", "ignore")
# Without an explicit level these inherit root's WARNING and drop INFO lines.
for _name in ("ingestion", "orchestration"):
    logging.getLogger(_name).setLevel(logging.INFO)

from prefect import flow, get_run_logger, task  # noqa: E402
from prefect.tasks import exponential_backoff  # noqa: E402

from ingestion.dataset import fetch  # noqa: E402
from ingestion.http_client import PoliteClient  # noqa: E402
from ingestion.pipeline import load_all  # noqa: E402
from ingestion.run_all import SOURCES  # noqa: E402
from orchestration import quality_report  # noqa: E402
from orchestration.dbt import (  # noqa: E402
    BUILD_FAILURE_STATUSES, FRESHNESS_FAILURE_STATUSES, RUN_RESULTS, SOURCES as SOURCES_JSON,
    TARGET_DIR, run_dbt, summarise_freshness, summarise_run_results,
)

# On top of the HTTP client's own retries: if a whole source still fails,
# Prefect retries it after 60 s and then 120 s.
DOWNLOAD_RETRIES = 2
DOWNLOAD_RETRY_DELAYS = exponential_backoff(backoff_factor=60)

_client: PoliteClient | None = None


def shared_client() -> PoliteClient:
    """One HTTP client per process, so the 2 s request spacing spans all sources."""
    global _client
    if _client is None:
        _client = PoliteClient()
    return _client


class PipelineFailed(RuntimeError):
    """Raised at the end of a run when any step, test or freshness check failed."""


@dataclass
class RunOutcome:
    """What happened in each step; drives the report and the final pass/fail."""

    downloads: dict[str, str] = field(default_factory=dict)
    load: str = "not run"
    freshness: str = "not run"
    dbt_build: str = "not run"
    failures: list[str] = field(default_factory=list)

    def as_steps(self) -> dict:
        steps = {f"download {name}": result for name, result in self.downloads.items()}
        steps.update({"load raw": self.load, "dbt source freshness": self.freshness,
                      "dbt build": self.dbt_build, "failures": self.failures})
        return steps


@task(retries=DOWNLOAD_RETRIES, retry_delay_seconds=DOWNLOAD_RETRY_DELAYS)
def download_source(source: str) -> str:
    """Download every dataset of one source. Raises if any dataset fails."""
    results = []
    for dataset in SOURCES[source]:
        saved = fetch(dataset, shared_client())
        results.append(f"{dataset.name}: {'new file ' if saved.written else 'unchanged '}"
                       f"{saved.path.name}")
    return "; ".join(results)


@task
def load_raw(sources: list[str]) -> str:
    datasets = [d for s in sources for d in SOURCES[s]]
    failed = load_all(datasets)
    if failed:
        raise RuntimeError(f"Raw load failed for: {', '.join(failed)}")
    return f"loaded {len(datasets)} dataset(s)"


@task
def dbt_source_freshness() -> dict | None:
    run_dbt(["source", "freshness"])
    return summarise_freshness(TARGET_DIR / SOURCES_JSON)


@task
def dbt_build(dbt_vars: dict | None) -> dict | None:
    result = run_dbt(["build"], dbt_vars)
    summary = summarise_run_results(TARGET_DIR / RUN_RESULTS)
    if summary is None or summary.get("command") != "build":
        # dbt died before writing results (e.g. a parse error): use its output.
        return {"counts": {}, "problems": [], "has_failures": not result.ok,
                "output_tail": result.output_tail}
    if not result.ok:
        summary["has_failures"] = True
    return summary


@task
def write_quality_report(steps: dict) -> str:
    return str(quality_report.write(quality_report.collect(steps)))


def describe_freshness(summary: dict | None) -> tuple[str, list[str]]:
    if summary is None:
        return "no results", ["dbt source freshness produced no results"]
    statuses = ", ".join(f"{s['source']}={s['status']}" for s in summary["sources"])
    errors = [f"Freshness ERROR: {s['source']} newest data ends {s['newest_period_end']} "
              f"({s['age_days']} days old, limit {s['error_after_days']})"
              for s in summary["sources"] if s["status"] in FRESHNESS_FAILURE_STATUSES]
    return statuses, errors


def describe_build(summary: dict | None) -> tuple[str, list[str]]:
    if summary is None:
        return "no results", ["dbt build produced no results"]
    counts = ", ".join(f"{k}={v}" for k, v in sorted(summary["counts"].items())) or "no results"
    failed = [f"dbt {p['type']} {p['status']}: {p['node']}" for p in summary["problems"]
              if p["status"] in BUILD_FAILURE_STATUSES]
    if summary["has_failures"] and not failed:
        failed = ["dbt build failed (see dbt output in the logs)"]
    return counts, failed


@flow(name="cost-of-living-pipeline")
def cost_of_living_pipeline(sources: list[str] | None = None, skip_download: bool = False,
                            dbt_vars: dict | None = None) -> dict:
    """Ingest ABS data, load raw, check freshness, dbt build, write the quality report."""
    logger = get_run_logger()
    sources = sources or sorted(SOURCES)
    outcome = RunOutcome()
    try:
        if skip_download:
            outcome.downloads = {s: "skipped" for s in sources}
        else:
            for source in sources:  # one at a time, to be polite to the ABS
                try:
                    outcome.downloads[source] = download_source(source)
                except Exception as exc:  # recorded; the flow fails at the end
                    outcome.downloads[source] = f"FAILED: {exc}"
                    outcome.failures.append(f"Download failed for {source}: {exc}")

        try:
            outcome.load = load_raw(sources)
        except Exception as exc:
            outcome.load = f"FAILED: {exc}"
            outcome.failures.append(str(exc))

        if outcome.load.startswith("FAILED"):
            logger.error("Skipping dbt because the raw load failed")
        else:
            outcome.freshness, errors = describe_freshness(dbt_source_freshness())
            outcome.failures += errors
            outcome.dbt_build, errors = describe_build(dbt_build(dbt_vars))
            outcome.failures += errors
    finally:
        report_path = write_quality_report(outcome.as_steps())
        logger.info("Quality report written to %s", report_path)

    if outcome.failures:
        for failure in outcome.failures:
            logger.error(failure)
        raise PipelineFailed(f"{len(outcome.failures)} problem(s); see {report_path}: "
                             + " | ".join(outcome.failures))
    logger.info("Pipeline succeeded: %s", outcome.dbt_build)
    return {"report": report_path, **outcome.as_steps()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the cost-of-living pipeline once.")
    parser.add_argument("--sources", nargs="+", choices=sorted(SOURCES))
    parser.add_argument("--skip-download", action="store_true", help="reuse files in data/raw/")
    parser.add_argument("--vars", type=json.loads, default=None,
                        help="dbt vars as JSON, e.g. for CI fixtures")
    args = parser.parse_args(argv)
    try:
        cost_of_living_pipeline(sources=args.sources, skip_download=args.skip_download,
                                dbt_vars=args.vars)
    except PipelineFailed as exc:
        print(f"\nPIPELINE FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
