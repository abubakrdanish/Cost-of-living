"""The dashboard must read only from the dbt marts (never raw/staging/intermediate)."""
import re
from pathlib import Path

import yaml

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"
SOURCES = DASHBOARD / "sources"
TABLE_REF = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)", re.IGNORECASE)


def _strip_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def test_every_source_query_reads_marts_only():
    files = sorted(SOURCES.rglob("*.sql"))
    assert files, "no dashboard source queries found"
    for path in files:
        refs = TABLE_REF.findall(_strip_comments(path.read_text()))
        assert refs, f"{path.name}: no schema-qualified table found"
        bad = [f"{s}.{t}" for s, t in refs if s.lower() != "marts"]
        assert not bad, f"{path.name} reads outside marts: {bad}"


def test_connection_is_the_project_warehouse_by_relative_path():
    conn = yaml.safe_load((SOURCES / "marts" / "connection.yaml").read_text())
    assert conn["type"] == "duckdb"
    filename = conn["options"]["filename"]
    assert not filename.startswith("/"), "absolute paths leak the local machine layout"
    assert (SOURCES / "marts" / filename).resolve().name == "cost_of_living.duckdb"


def test_telemetry_is_disabled():
    import json
    settings = json.loads((DASHBOARD / "evidence.settings.json").read_text())
    assert settings["send_anonymous_usage_stats"] == "no"
    package = json.loads((DASHBOARD / "package.json").read_text())
    assert package["overrides"]["@evidence-dev/telemetry"] == "$@evidence-dev/telemetry"
    assert package["dependencies"]["@evidence-dev/telemetry"] == "file:vendor/telemetry-noop"
    noop = (DASHBOARD / "vendor" / "telemetry-noop" / "index.cjs").read_text()
    assert "require(" not in noop, "the no-op telemetry module must not import anything"
