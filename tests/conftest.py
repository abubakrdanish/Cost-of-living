"""Shared fixtures. Network access is blocked so every test proves it runs offline."""
from __future__ import annotations

import socket
from datetime import datetime
from pathlib import Path

import openpyxl
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def guard(*args, **kwargs):
        raise RuntimeError("Network access attempted during tests")

    monkeypatch.setattr(socket.socket, "connect", guard)


@pytest.fixture
def sdmx_csv_bytes() -> bytes:
    return (FIXTURES / "sdmx_cpi_sample.csv").read_bytes()


def build_abs_workbook(path: Path) -> Path:
    """A tiny workbook in the ABS 'Time Series Workbook' layout (2 series, 3 quarters)."""
    wb = openpyxl.Workbook()
    wb.active.title = "Index"
    ws = wb.create_sheet("Data1")
    ws.append([None, "Index Numbers ;  Rents ;  Sydney ;", "Index Numbers ;  Rents ;  Darwin ;"])
    ws.append(["Unit", "Index Numbers", "Index Numbers"])
    ws.append(["Series Type", "Original", "Original"])
    ws.append(["Data Type", "INDEX", "INDEX"])
    ws.append(["Frequency", "Quarter", "Quarter"])
    ws.append(["Collection Month", 3, 3])
    ws.append(["Series Start", datetime(1980, 6, 1), datetime(1980, 9, 1)])
    ws.append(["Series End", datetime(1980, 12, 1), datetime(1980, 12, 1)])
    ws.append(["No. Obs", 3, 2])
    ws.append(["Series ID", "A0000001A", "A0000002B"])
    ws.append([datetime(1980, 6, 1), 10.5, None])  # Darwin not yet published
    ws.append([datetime(1980, 9, 1), 10.7, 9.9])
    ws.append([datetime(1980, 12, 1), 10.9, 10.1])
    ws.append([None, None, None])  # trailing blank row, as in real files
    wb.create_sheet("Enquiries")
    wb.save(path)
    return path


@pytest.fixture
def abs_workbook(tmp_path) -> Path:
    return build_abs_workbook(tmp_path / "sample.xlsx")
