"""Download and load every source.

Usage:
    python -m ingestion.run_all                 # download + load all sources
    python -m ingestion.run_all --sources cpi   # just one source
    python -m ingestion.run_all --skip-download # reload from files in data/raw/
"""
from __future__ import annotations

import argparse

from ingestion import cpi, rents, wpi
from ingestion.pipeline import run

SOURCES = {"cpi": cpi.DATASETS, "wpi": wpi.DATASETS, "rents": rents.DATASETS}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", nargs="+", choices=sorted(SOURCES), default=sorted(SOURCES))
    parser.add_argument("--skip-download", action="store_true", help="only load existing raw files")
    parser.add_argument("--skip-load", action="store_true", help="only download")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    datasets = [ds for name in args.sources for ds in SOURCES[name]]
    run(datasets, download=not args.skip_download, load=not args.skip_load)


if __name__ == "__main__":
    main()
