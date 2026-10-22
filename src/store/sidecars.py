"""Sidecar JSON persistence for sensory records.

One file per roast, ``<roastUUID>.json`` inside the sensory folder, UTF-8
with ``indent=2`` (human-readable, git- and sync-friendly). Writes are
atomic: the payload goes to a temporary file in the same folder, is
flushed and fsynced, and is then moved into place with ``os.replace`` --
a crash mid-write can never truncate or corrupt an existing sidecar, and
the failed temp file is cleaned up. This layer never touches ``.alog``
files.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

from .errors import SensoryStoreError
from .schema import check_roast_uuid, normalize_record, refresh_record

PathLike = Union[str, Path]


def record_path(sensory_dir: PathLike, roast_uuid: str) -> Path:
    """Sidecar path for ``roast_uuid`` inside ``sensory_dir``."""
    return Path(sensory_dir) / f"{check_roast_uuid(roast_uuid)}.json"


def read_record(
    sensory_dir: PathLike, roast_uuid: str
) -> Optional[dict[str, Any]]:
    """Load and normalize the sidecar for ``roast_uuid``.

    Returns ``None`` when no sidecar exists -- a roast without annotations
    is a normal state, not an error. Raises
    :class:`SensoryStoreError` (with the filename in the message) when
    the file exists but cannot be read, parsed or validated.
    """
    path = record_path(sensory_dir, roast_uuid)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SensoryStoreError(f"{path}: cannot read sidecar ({exc})") from exc
    try:
        return normalize_record(raw, roast_uuid=roast_uuid)
    except SensoryStoreError as exc:
        raise SensoryStoreError(f"{path}: {exc}") from exc


def write_record(sensory_dir: PathLike, record: dict[str, Any]) -> Path:
    """Atomically write ``record`` to its sidecar, refreshed and normalized.

    Returns the sidecar path. The write is atomic (temp file +
    ``os.replace``); any failure raises :class:`SensoryStoreError`,
    leaves an existing sidecar untouched and removes the temp file.
    """
    path = record_path(sensory_dir, record["roast_uuid"])
    payload = refresh_record(record)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.stem}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if isinstance(exc, OSError):
            raise SensoryStoreError(
                f"{path}: atomic write failed ({exc})"
            ) from exc
        raise
    return path


def delete_record(sensory_dir: PathLike, roast_uuid: str) -> bool:
    """Delete the sidecar for ``roast_uuid``; ``False`` if it did not exist."""
    path = record_path(sensory_dir, roast_uuid)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
