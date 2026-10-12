import shutil
from datetime import datetime, timezone

import duckdb
import pytest

from ingestion.dataset import RawDataset
from ingestion.load_raw import load_dataset
from tests.conftest import FIXTURES, build_abs_workbook

CSV_DATASET = RawDataset(name="abs_cpi_rents", source="abs_cpi_rents",
                         url="https://example/csv", kind="sdmx_csv", description="test")
XLSX_DATASET = RawDataset(name="abs_archive", source="abs_cpi_rents",
                          url="https://example/xlsx", kind="abs_xlsx", description="test")
LOADED_AT = datetime(2026, 10, 12, tzinfo=timezone.utc)


@pytest.fixture
def con():
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA raw")
    yield connection
    connection.close()


@pytest.fixture
def raw_root(tmp_path):
    directory = tmp_path / "abs_cpi_rents"
    directory.mkdir()
    shutil.copy(FIXTURES / "sdmx_cpi_sample.csv", directory / "abs_cpi_rents_20261012.csv")
    return tmp_path


def test_csv_load_normalises_columns_and_adds_lineage(con, raw_root):
    summary = load_dataset(con, CSV_DATASET, root=raw_root, loaded_at=LOADED_AT)
    assert summary.total_rows == 3
    columns = [r[0] for r in con.execute("DESCRIBE raw.abs_cpi_rents").fetchall()]
    assert columns[:3] == ["dataflow", "measure", "index"]
    assert columns[-2:] == ["_source_file", "_loaded_at"]
    row = con.execute(
        "SELECT region, time_period, obs_value, obs_status, _source_file FROM raw.abs_cpi_rents "
        "WHERE region = '50: Australia'"
    ).fetchone()
    # values are stored exactly as in the file
    assert row == ("50: Australia", "2022-07", "83.04", "r: revised", "abs_cpi_rents_20261012.csv")


def test_reloading_same_file_does_not_duplicate(con, raw_root):
    load_dataset(con, CSV_DATASET, root=raw_root, loaded_at=LOADED_AT)
    second = load_dataset(con, CSV_DATASET, root=raw_root, loaded_at=LOADED_AT)
    assert second.files_loaded == []
    assert second.files_skipped == ["abs_cpi_rents_20261012.csv"]
    assert second.total_rows == 3


def test_new_snapshot_is_appended(con, raw_root):
    load_dataset(con, CSV_DATASET, root=raw_root, loaded_at=LOADED_AT)
    shutil.copy(FIXTURES / "sdmx_cpi_sample.csv",
                raw_root / "abs_cpi_rents" / "abs_cpi_rents_20261112.csv")
    summary = load_dataset(con, CSV_DATASET, root=raw_root, loaded_at=LOADED_AT)
    assert summary.files_loaded == ["abs_cpi_rents_20261112.csv"]
    assert summary.total_rows == 6


def test_xlsx_load(con, raw_root):
    build_abs_workbook(raw_root / "abs_cpi_rents" / "abs_archive_20261012.xlsx")
    summary = load_dataset(con, XLSX_DATASET, root=raw_root, loaded_at=LOADED_AT)
    assert summary.total_rows == 5
    types = dict(con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'abs_archive'").fetchall())
    assert types["period"] == "DATE"
    assert types["value"] == "DOUBLE"
    # CSV dataset in the same folder is not picked up by the XLSX dataset
    assert con.execute("SELECT count(DISTINCT _source_file) FROM raw.abs_archive").fetchone()[0] == 1


def test_failed_file_leaves_no_partial_rows(con, raw_root):
    (raw_root / "abs_cpi_rents" / "abs_archive_20261012.xlsx").write_bytes(b"not an xlsx")
    with pytest.raises(Exception):
        load_dataset(con, XLSX_DATASET, root=raw_root, loaded_at=LOADED_AT)
    tables = con.execute("SELECT count(*) FROM information_schema.tables "
                         "WHERE table_name = 'abs_archive'").fetchone()[0]
    assert tables == 0
