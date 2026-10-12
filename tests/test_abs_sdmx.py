import pytest

from ingestion.abs_sdmx import data_url, normalise_column_name, validate_sdmx_csv


def test_data_url_without_periods():
    assert data_url("ABS,CPI,2.0.0", "1.10001...", base="https://x/rest") == (
        "https://x/rest/data/ABS,CPI,2.0.0/1.10001..."
    )


def test_data_url_with_periods():
    url = data_url("ABS,WPI,1.2.0", "1......Q", start_period="2020-Q1", base="https://x/rest")
    assert url.endswith("/data/ABS,WPI,1.2.0/1......Q?startPeriod=2020-Q1")


@pytest.mark.parametrize(
    "header, expected",
    [
        ("TIME_PERIOD: Time Period", "time_period"),
        ("OBS_VALUE", "obs_value"),
        ("REGION: Region", "region"),
        ("BASE_PERIOD: Reference Base Period", "base_period"),
    ],
)
def test_normalise_column_name(header, expected):
    assert normalise_column_name(header) == expected


def test_validate_counts_rows(sdmx_csv_bytes):
    assert validate_sdmx_csv(sdmx_csv_bytes) == 3


def test_validate_rejects_html():
    with pytest.raises(ValueError, match="Not SDMX-CSV"):
        validate_sdmx_csv(b"<!DOCTYPE html><html><body>Service unavailable</body></html>")


def test_validate_rejects_empty_body():
    with pytest.raises(ValueError, match="Empty response"):
        validate_sdmx_csv(b"")


def test_validate_rejects_header_only(sdmx_csv_bytes):
    header_only = sdmx_csv_bytes.splitlines()[0] + b"\n"
    with pytest.raises(ValueError, match="no data rows"):
        validate_sdmx_csv(header_only)
