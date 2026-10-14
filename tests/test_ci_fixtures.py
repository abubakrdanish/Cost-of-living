"""The committed CI fixtures must stay loadable and match what CI expects."""
import csv
import shutil

import duckdb
import pytest

from ingestion import ci_fixtures
from ingestion.abs_sdmx import validate_sdmx_csv
from ingestion.abs_timeseries_xlsx import parse_workbook
from ingestion.ci_fixtures import FIXTURE_DIR, OLDER_RENTS_FILE, REVISED_KEY
from ingestion.load_raw import load_dataset
from ingestion.raw_files import list_data_files


@pytest.mark.parametrize("dataset", ci_fixtures.all_datasets(), ids=lambda d: d.name)
def test_every_dataset_has_a_parseable_fixture(dataset):
    path = ci_fixtures.latest_file(dataset, FIXTURE_DIR)
    if dataset.kind == "sdmx_csv":
        assert validate_sdmx_csv(path.read_bytes()) > 0
    else:
        frame = parse_workbook(path)
        assert frame["series_description"].str.contains("Rents").any()


def test_fixtures_load_into_duckdb():
    with duckdb.connect(":memory:") as con:
        con.execute("create schema raw")
        totals = {d.name: load_dataset(con, d, root=FIXTURE_DIR).total_rows
                  for d in ci_fixtures.all_datasets()}
    assert all(n > 0 for n in totals.values()), totals


def test_rents_has_two_snapshots_older_first():
    files = list_data_files(FIXTURE_DIR / "abs_cpi_rents", "abs_cpi_rents", "csv")
    assert [f.name for f in files][0] == OLDER_RENTS_FILE
    assert len(files) == 2


def _rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        idx = {h.split(":", 1)[0]: i for i, h in enumerate(header)}
        out = {}
        for r in reader:
            key = tuple(r[idx[c]].split(":", 1)[0].strip()
                        for c in ("INDEX", "TSEST", "REGION", "FREQ")) + (r[idx["TIME_PERIOD"]],)
            out[key] = r[idx["OBS_VALUE"]]
        return out


def test_older_rents_snapshot_differs_by_exactly_one_value():
    older_path, newer_path = list_data_files(FIXTURE_DIR / "abs_cpi_rents", "abs_cpi_rents", "csv")
    older, newer = _rows(older_path), _rows(newer_path)
    changed = [k for k in older if older[k] != newer[k]]
    assert changed == [REVISED_KEY]
    assert set(older) < set(newer)  # newest month missing from the older file


def test_check_detects_a_changed_header(tmp_path):
    real_root = tmp_path / "raw"
    shutil.copytree(FIXTURE_DIR, real_root)
    assert ci_fixtures.check(raw_root=real_root, fixture_root=FIXTURE_DIR) == []

    wpi = ci_fixtures.latest_file(ci_fixtures.wpi.WPI_INDEX, real_root)
    text = wpi.read_bytes().decode("utf-8")
    wpi.write_bytes(text.replace("OBS_VALUE", "OBS_VAL", 1).encode("utf-8"))
    problems = ci_fixtures.check(raw_root=real_root, fixture_root=FIXTURE_DIR)
    assert len(problems) == 1 and "abs_wpi: layout differs" in problems[0]
