from pathlib import Path

import pytest

from ingestion import config, cpi, rents, wpi
from ingestion.dataset import fetch
from ingestion.http_client import Downloaded
from ingestion.raw_files import list_data_files


class FakeClient:
    """Stands in for PoliteClient; returns canned bytes."""

    def __init__(self, content: bytes):
        self.content = content
        self.calls = []

    def get(self, url, accept=None):
        self.calls.append((url, accept))
        return Downloaded(url=url, content=self.content, content_type="text/csv", last_modified=None)


def test_fetch_saves_valid_csv(tmp_path, sdmx_csv_bytes):
    client = FakeClient(sdmx_csv_bytes)
    result = fetch(rents.CPI_RENTS, client, root=tmp_path)
    assert result.written
    assert result.path.parent == tmp_path / "abs_cpi_rents"
    assert client.calls[0][1].startswith("application/vnd.sdmx.data+csv")


def test_fetch_rejects_error_page_and_saves_nothing(tmp_path):
    with pytest.raises(ValueError):
        fetch(cpi.CPI_ALL_GROUPS, FakeClient(b"<html>error</html>"), root=tmp_path)
    assert list_data_files(tmp_path / "abs_cpi", "abs_cpi_all_groups", "csv") == []


def test_fetch_rejects_non_xlsx(tmp_path):
    with pytest.raises(ValueError, match="not an XLSX"):
        fetch(rents.CPI_CAPITAL_CITIES_QUARTERLY_ARCHIVE, FakeClient(b"<html/>"), root=tmp_path)


def test_dataset_names_are_unique():
    names = [d.name for d in cpi.DATASETS + wpi.DATASETS + rents.DATASETS]
    assert len(names) == len(set(names))


def test_relative_paths_resolve_from_project_root():
    assert config._resolve_path("warehouse/x.duckdb") == config.PROJECT_ROOT / "warehouse/x.duckdb"
    assert config._resolve_path("/abs/x.duckdb") == Path("/abs/x.duckdb")
