"""Run dbt as a subprocess and read its JSON artifacts.

dbt runs in its own process (cwd = dbt_project/) so the relative DuckDB path
in profiles.yml resolves the same way as when you run dbt by hand, and so the
flow never holds the DuckDB file open while dbt writes to it.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ingestion.config import PROJECT_ROOT

log = logging.getLogger(__name__)

DBT_PROJECT_DIR = PROJECT_ROOT / "dbt_project"
TARGET_DIR = DBT_PROJECT_DIR / "target"
RUN_RESULTS = "run_results.json"
SOURCES = "sources.json"

# dbt result statuses that count as problems.
TEST_FAILURE_STATUSES = {"fail", "error", "runtime error"}
FRESHNESS_FAILURE_STATUSES = {"error", "runtime error"}


@dataclass
class DbtResult:
    command: list[str]
    returncode: int
    output_tail: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def dbt_executable() -> str:
    """dbt from the same virtualenv as this Python, falling back to PATH."""
    candidate = Path(sys.executable).with_name("dbt")
    if candidate.exists():
        return str(candidate)
    found = shutil.which("dbt")
    if not found:
        raise FileNotFoundError("dbt executable not found; install requirements.lock")
    return found


def build_dbt_command(args: list[str], dbt_vars: dict | None = None,
                      executable: str | None = None) -> list[str]:
    """e.g. ['build'] -> [dbt, 'build', '--profiles-dir', ..., '--project-dir', ...]."""
    command = [executable or dbt_executable(), *args,
               "--profiles-dir", str(DBT_PROJECT_DIR),
               "--project-dir", str(DBT_PROJECT_DIR)]
    if dbt_vars:
        command += ["--vars", json.dumps(dbt_vars, sort_keys=True)]
    return command


def ensure_profiles(project_dir: Path = DBT_PROJECT_DIR) -> None:
    if not (project_dir / "profiles.yml").exists():
        raise FileNotFoundError(
            f"{project_dir / 'profiles.yml'} is missing. Run: "
            "cp dbt_project/profiles.yml.example dbt_project/profiles.yml"
        )


def run_dbt(args: list[str], dbt_vars: dict | None = None, tail_lines: int = 40) -> DbtResult:
    """Run a dbt command, streaming its output to the log. Never raises on dbt failure."""
    ensure_profiles()
    command = build_dbt_command(args, dbt_vars)
    log.info("Running: dbt %s%s", " ".join(args),
             f" --vars {json.dumps(dbt_vars, sort_keys=True)}" if dbt_vars else "")
    tail: list[str] = []
    env = {**os.environ, "DBT_USE_COLORS": "false"}  # plain text in the logs
    with subprocess.Popen(command, cwd=DBT_PROJECT_DIR, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, env=env) as process:
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            log.info("dbt | %s", line)
            tail = (tail + [line])[-tail_lines:]
    log.info("dbt %s exited with code %d", " ".join(args), process.returncode)
    return DbtResult(command=command, returncode=process.returncode, output_tail=tail)


# ---- Artifacts ---------------------------------------------------------------

def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _short_name(unique_id: str) -> str:
    """'test.au_cost_of_living.not_null_x' -> 'not_null_x'."""
    return unique_id.split(".", 2)[-1]


def summarise_run_results(path: Path) -> dict | None:
    """Counts by status, and every node that did not pass/succeed."""
    data = _load(path)
    if data is None:
        return None
    counts: dict[str, int] = {}
    problems = []
    for result in data["results"]:
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1
        if status not in {"pass", "success"}:  # warn, fail, error, skipped
            problems.append({
                "node": _short_name(result["unique_id"]),
                "type": result["unique_id"].split(".", 1)[0],
                "status": status,
                "failures": result.get("failures"),
                "message": (result.get("message") or "")[:300],
            })
    return {
        "command": data.get("args", {}).get("which"),
        "generated_at": data.get("metadata", {}).get("generated_at"),
        "counts": counts,
        "problems": problems,
        "has_failures": any(p["status"] in TEST_FAILURE_STATUSES for p in problems),
    }


def summarise_freshness(path: Path) -> dict | None:
    """One entry per source with status, newest period and age in days."""
    data = _load(path)
    if data is None:
        return None
    sources = []
    for result in data["results"]:
        criteria = result.get("criteria") or {}
        age_s = result.get("max_loaded_at_time_ago_in_s")
        sources.append({
            "source": _short_name(result["unique_id"]).split(".", 1)[-1],
            "status": result["status"],
            "newest_period_end": (result.get("max_loaded_at") or "")[:10] or None,
            "age_days": round(age_s / 86400, 1) if age_s is not None else None,
            "warn_after_days": (criteria.get("warn_after") or {}).get("count"),
            "error_after_days": (criteria.get("error_after") or {}).get("count"),
            "message": (result.get("message") or "")[:300] or None,
        })
    return {
        "generated_at": data.get("metadata", {}).get("generated_at"),
        "sources": sources,
        "has_errors": any(s["status"] in FRESHNESS_FAILURE_STATUSES for s in sources),
        "has_warnings": any(s["status"] == "warn" for s in sources),
    }
