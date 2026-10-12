"""Project paths, environment overrides and logging setup.

Values can be overridden with environment variables or a git-ignored `.env`
file at the repo root (see `.env.example`). No secrets are needed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
LOG_DIR = PROJECT_ROOT / "logs"

DEFAULT_USER_AGENT = (
    "cost-of-living-portfolio/0.1 (personal data engineering project; python-requests)"
)
ABS_DATA_API_BASE = "https://data.api.abs.gov.au/rest"


def _resolve_path(value: str) -> Path:
    """Treat relative paths as relative to the project root, not the cwd."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


DB_PATH = _resolve_path(os.getenv("DUCKDB_PATH", "warehouse/cost_of_living.duckdb"))
USER_AGENT = os.getenv("COL_USER_AGENT", DEFAULT_USER_AGENT)


def setup_logging(level: int = logging.INFO) -> None:
    """Log to stderr and to logs/ingestion.log (git-ignored)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "ingestion.log", encoding="utf-8"),
        ],
        force=True,
    )
