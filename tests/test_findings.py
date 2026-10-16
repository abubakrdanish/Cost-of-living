"""The findings queries are parseable, read marts only, and run against a mart."""
import re

import duckdb

from orchestration import findings

TABLE_REF = re.compile(r"\b(?:from|join)\s+([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)", re.IGNORECASE)


def _queries():
    return findings.parse_queries(findings.QUERIES_FILE.read_text(encoding="utf-8"))


def test_all_findings_queries_are_named_and_present():
    names = list(_queries())
    assert names[0] == "F0_range"
    assert {f"F{i}" for i in range(9)} == {n.split("_")[0] for n in names}


def test_findings_queries_read_marts_only():
    for name, sql in _queries().items():
        refs = TABLE_REF.findall(re.sub(r"--[^\n]*", "", sql))
        assert refs, name
        assert all(schema == "marts" for schema, _ in refs), (name, refs)


def test_parse_queries_splits_on_name_lines():
    text = "-- preamble\n-- name: A_one\nselect 1;\n\n-- name: B_two\n-- note\nselect 2;\n"
    assert findings.parse_queries(text) == {"A_one": "select 1", "B_two": "-- note\nselect 2"}


def test_run_against_a_tiny_mart(tmp_path):
    db = tmp_path / "w.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("create schema marts")
        con.execute("create table marts.mart_cost_of_living_quarterly as "
                    "select '1997-Q3' as quarter_label, date '1997-07-01' as quarter_start_date, 'AUS' as region_key")
    queries = tmp_path / "q.sql"
    queries.write_text("-- name: F0_range\nselect min(quarter_label) as first_quarter, "
                       "count(*) as n from marts.mart_cost_of_living_quarterly;\n")
    result = findings.run(["F0"], db_path=db, queries_file=queries)
    assert result["F0_range"].fetchall() == [("1997-Q3", 1)]
