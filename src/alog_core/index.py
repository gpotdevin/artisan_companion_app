"""SQLite roast index built from a folder of .alog files."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from .model import parse_profile
from .parser import PathLike

_SCHEMA = """
CREATE TABLE roasts (
    roast_id TEXT,
    source_file TEXT NOT NULL,
    title TEXT,
    beans TEXT,
    roast_isodate TEXT,
    green_weight_g REAL,
    roasted_weight_g REAL,
    drop_bt_c REAL,
    fcs_time_s REAL,
    total_time_s REAL,
    parse_ok INTEGER NOT NULL,
    error_msg TEXT
)
"""

_INSERT = (
    "INSERT INTO roasts (roast_id, source_file, title, beans, roast_isodate,"
    " green_weight_g, roasted_weight_g, drop_bt_c, fcs_time_s, total_time_s,"
    " parse_ok, error_msg) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
)


def _file_hash(name: str) -> str:
    """First 16 hex chars of the SHA-256 of a filename (fallback roast id)."""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]


def build_index(logs_dir: PathLike, db_path: PathLike) -> int:
    """(Re)build the SQLite roast index from every ``*.alog`` in ``logs_dir``.

    The scan is non-recursive and one row is stored per scanned file:
    ``roast_id`` is the file's ``roastUUID`` or, failing that, the first 16
    hex chars of the SHA-256 of the filename. A file that fails to parse is
    recorded with ``parse_ok = 0`` and its error message; it never aborts
    the scan. The ``roasts`` table is dropped and recreated on every call,
    making rebuilds idempotent. Returns the number of files scanned.
    """
    logs = Path(logs_dir)
    db = Path(db_path)
    if db.parent and not db.parent.exists():
        db.parent.mkdir(parents=True, exist_ok=True)

    rows: list[tuple] = []
    for path in sorted(p for p in logs.glob("*.alog") if p.is_file()):
        try:
            profile = parse_profile(path)
            meta = profile.meta
            drop = profile.markers.get("DROP")
            fcs = profile.markers.get("FCs")
            total_time_s = None
            if profile.phases is not None:
                total_time_s = profile.phases.get("total_s")
            if total_time_s is None and drop is not None:
                total_time_s = drop.time_s
            rows.append((
                meta.roast_uuid or _file_hash(path.name),
                path.name,
                meta.title,
                meta.beans,
                meta.roast_isodate,
                meta.green_weight_g,
                meta.roasted_weight_g,
                drop.temp_bt_c if drop is not None else None,
                fcs.time_s if fcs is not None else None,
                total_time_s,
                1,
                None,
            ))
        except Exception as exc:  # one bad file must not abort the scan
            rows.append((
                _file_hash(path.name),
                path.name,
                None, None, None, None, None, None, None, None,
                0,
                str(exc),
            ))

    conn = sqlite3.connect(db)
    try:
        with conn:
            conn.execute("DROP TABLE IF EXISTS roasts")
            conn.execute(_SCHEMA.strip())
            conn.executemany(_INSERT, rows)
    finally:
        conn.close()
    return len(rows)


def list_roasts(db_path: PathLike) -> list[dict[str, Any]]:
    """Return every roast row from the index as a list of dicts.

    Rows are ordered by roast date (NULLs last) then source filename.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM roasts"
            " ORDER BY roast_isodate IS NULL, roast_isodate, source_file"
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
