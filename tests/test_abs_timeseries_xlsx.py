from datetime import date

import openpyxl
import pytest

from ingestion.abs_timeseries_xlsx import looks_like_xlsx, parse_workbook


def test_parse_workbook_long_format(abs_workbook):
    frame = parse_workbook(abs_workbook)
    # 3 Sydney + 2 Darwin values; blank cells and the trailing blank row are skipped
    assert len(frame) == 5
    assert set(frame["series_id"]) == {"A0000001A", "A0000002B"}
    darwin = frame[frame["series_id"] == "A0000002B"].sort_values("period")
    assert list(darwin["period"]) == [date(1980, 9, 1), date(1980, 12, 1)]
    assert list(darwin["value"]) == [9.9, 10.1]


def test_parse_workbook_keeps_metadata(abs_workbook):
    row = parse_workbook(abs_workbook).iloc[0]
    assert row["series_description"] == "Index Numbers ;  Rents ;  Sydney ;"
    assert row["frequency"] == "Quarter"
    assert row["series_start"] == date(1980, 6, 1)
    assert row["sheet"] == "Data1"


def test_parse_workbook_rejects_unexpected_layout(abs_workbook):
    wb = openpyxl.load_workbook(abs_workbook)
    wb["Data1"]["A2"] = "Units"  # ABS changed a label: fail loudly, don't guess
    wb.save(abs_workbook)
    with pytest.raises(ValueError, match="Unexpected ABS metadata rows"):
        parse_workbook(abs_workbook)


def test_looks_like_xlsx(abs_workbook):
    assert looks_like_xlsx(abs_workbook.read_bytes())
    assert not looks_like_xlsx(b"<html>Not found</html>")
