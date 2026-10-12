import json
from datetime import datetime, timezone

from ingestion.raw_files import list_data_files, save_raw, stamped_filename

NOW = datetime(2026, 10, 12, 7, 30, 0, tzinfo=timezone.utc)
LATER_SAME_DAY = datetime(2026, 10, 12, 9, 15, 0, tzinfo=timezone.utc)
NEXT_MONTH = datetime(2026, 11, 12, 7, 30, 0, tzinfo=timezone.utc)


def _save(tmp_path, content, now):
    return save_raw(content, tmp_path / "abs_cpi", "abs_cpi", "csv", "https://example/x", now=now)


def test_stamped_filename():
    assert stamped_filename("abs_cpi", ".csv", NOW) == "abs_cpi_20261012.csv"


def test_save_writes_unchanged_bytes_and_sidecar(tmp_path):
    result = _save(tmp_path, b"a,b\n1,2\n", NOW)
    assert result.written
    assert result.path.name == "abs_cpi_20261012.csv"
    assert result.path.read_bytes() == b"a,b\n1,2\n"
    meta = json.loads(result.path.with_name(result.path.name + ".meta.json").read_text())
    assert meta["source_url"] == "https://example/x"
    assert meta["bytes"] == 8


def test_identical_content_is_not_saved_twice(tmp_path):
    first = _save(tmp_path, b"same", NOW)
    second = _save(tmp_path, b"same", NEXT_MONTH)
    assert not second.written
    assert second.path == first.path
    assert len(list_data_files(tmp_path / "abs_cpi", "abs_cpi", "csv")) == 1


def test_revised_content_gets_new_file(tmp_path):
    _save(tmp_path, b"v1", NOW)
    revised = _save(tmp_path, b"v2", NEXT_MONTH)
    assert revised.written
    assert revised.path.name == "abs_cpi_20261112.csv"
    assert len(list_data_files(tmp_path / "abs_cpi", "abs_cpi", "csv")) == 2


def test_changed_content_same_day_does_not_overwrite(tmp_path):
    first = _save(tmp_path, b"v1", NOW)
    second = _save(tmp_path, b"v2", LATER_SAME_DAY)
    assert second.path.name == "abs_cpi_20261012T091500.csv"
    assert first.path.read_bytes() == b"v1"


def test_list_data_files_ignores_sidecars_and_other_datasets(tmp_path):
    directory = tmp_path / "abs_cpi_rents"
    save_raw(b"x", directory, "abs_cpi_rents", "csv", "u", now=NOW)
    save_raw(b"y", directory, "abs_cpi_capital_cities", "xlsx", "u", now=NOW)
    names = [p.name for p in list_data_files(directory, "abs_cpi_rents", "csv")]
    assert names == ["abs_cpi_rents_20261012.csv"]


def test_list_data_files_missing_directory(tmp_path):
    assert list_data_files(tmp_path / "nope", "abs_cpi", "csv") == []
