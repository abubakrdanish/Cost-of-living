"""Save downloaded files unchanged under data/raw/<source>/ with a date stamp.

Idempotency rule: a download whose bytes match a file already saved for the
same dataset is not written again. New content gets a new date-stamped file,
so revisions are kept side by side instead of overwriting history.

Each data file gets a `<file>.meta.json` sidecar recording where and when it
was downloaded.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

META_SUFFIX = ".meta.json"


@dataclass(frozen=True)
class SaveResult:
    path: Path
    written: bool  # False when identical content was already on disk


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stamped_filename(stem: str, ext: str, now: datetime) -> str:
    """`abs_cpi` + `csv` -> `abs_cpi_20261012.csv`."""
    return f"{stem}_{now:%Y%m%d}.{ext.lstrip('.')}"


def list_data_files(directory: Path, stem: str, ext: str) -> list[Path]:
    """Data files for one dataset (sidecars excluded), oldest name first."""
    if not directory.exists():
        return []
    pattern = f"{stem}_*.{ext.lstrip('.')}"
    return sorted(p for p in directory.glob(pattern) if p.is_file())


def find_identical(directory: Path, stem: str, ext: str, digest: str) -> Path | None:
    for existing in list_data_files(directory, stem, ext):
        if sha256_file(existing) == digest:
            return existing
    return None


def choose_new_path(directory: Path, stem: str, ext: str, now: datetime) -> Path:
    """Date-stamped path; add a time suffix if today's name is already taken."""
    path = directory / stamped_filename(stem, ext, now)
    if path.exists():
        path = directory / f"{stem}_{now:%Y%m%dT%H%M%S}.{ext.lstrip('.')}"
    return path


def _write_atomic(path: Path, content: bytes) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(content)
    os.replace(tmp, path)


def save_raw(
    content: bytes,
    directory: Path,
    stem: str,
    ext: str,
    source_url: str,
    now: datetime | None = None,
    extra_meta: dict | None = None,
) -> SaveResult:
    """Save bytes unchanged unless an identical file already exists."""
    now = now or datetime.now(timezone.utc)
    directory.mkdir(parents=True, exist_ok=True)
    digest = sha256_bytes(content)

    existing = find_identical(directory, stem, ext, digest)
    if existing is not None:
        log.info("Unchanged since %s; not saving a duplicate", existing.name)
        return SaveResult(path=existing, written=False)

    path = choose_new_path(directory, stem, ext, now)
    _write_atomic(path, content)
    meta = {
        "source_url": source_url,
        "downloaded_at_utc": now.isoformat(timespec="seconds"),
        "sha256": digest,
        "bytes": len(content),
        **(extra_meta or {}),
    }
    path.with_name(path.name + META_SUFFIX).write_text(json.dumps(meta, indent=2) + "\n")
    log.info("Saved %s/%s (%d bytes)", directory.name, path.name, len(content))
    return SaveResult(path=path, written=True)
