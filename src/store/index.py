"""SQLite index over the sensory sidecars, for listing and searching.

The index lives in ``sensory_index.sqlite`` inside the sensory folder
(portable: the whole folder can be copied or synced). Three tables:

- ``roasts`` -- the universe of known roast uuids (registered from the
  alog index or the app), used to also list roasts *without* annotations;
- ``annotations`` -- one summary row per sidecar (roast ref, cupping
  count, best total score, last cupping date);
- ``descriptors`` -- one row per (roast, descriptor), for descriptor
  search.

The ``annotations``/``descriptors`` tables are rebuilt from the sidecar
files every time a store is opened, then kept in sync per mutation --
the sidecars remain the system of record, and the index is always
derivable from them.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional, Union

from .errors import SensoryStoreError
from .schema import _parse_iso_date
from .sidecars import read_record

PathLike = Union[str, Path]

_INDEX_FILENAME = "sensory_index.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS roasts (
    roast_uuid TEXT PRIMARY KEY,
    source_file TEXT,
    roast_date TEXT
);
CREATE TABLE IF NOT EXISTS annotations (
    roast_uuid TEXT PRIMARY KEY,
    source_file TEXT,
    roast_date TEXT,
    n_cuppings INTEGER NOT NULL DEFAULT 0,
    best_total REAL,
    last_cupping_date TEXT
);
CREATE TABLE IF NOT EXISTS descriptors (
    roast_uuid TEXT NOT NULL,
    descriptor TEXT NOT NULL,
    PRIMARY KEY (roast_uuid, descriptor)
);
"""

_INSERT_ANNOTATION = (
    "INSERT OR REPLACE INTO annotations"
    " (roast_uuid, source_file, roast_date, n_cuppings, best_total,"
    "  last_cupping_date) VALUES (?,?,?,?,?,?)"
)


# ---------------------------------------------------------------------------
# Connection and summary rows
# ---------------------------------------------------------------------------

def index_path(sensory_dir: PathLike) -> Path:
    """Path of the SQLite index file inside ``sensory_dir``."""
    return Path(sensory_dir) / _INDEX_FILENAME


def open_index(sensory_dir: PathLike) -> sqlite3.Connection:
    """Open (creating if needed) the index database inside ``sensory_dir``."""
    path = index_path(sensory_dir)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _annotation_row(record: dict[str, Any]) -> tuple:
    ref = record.get("roast_ref") or {}
    cuppings = record.get("cuppings") or []
    totals = [c["scores"]["total"] for c in cuppings
              if c.get("scores", {}).get("total") is not None]
    dates = [c["date"] for c in cuppings if c.get("date")]
    return (
        record["roast_uuid"],
        ref.get("file"),
        ref.get("date"),
        len(cuppings),
        max(totals) if totals else None,
        max(dates) if dates else None,
    )


def _descriptor_rows(record: dict[str, Any]) -> list[tuple[str, str]]:
    uuid = record["roast_uuid"]
    seen = sorted({
        d
        for c in record.get("cuppings") or []
        for d in c.get("descriptors") or []
    })
    return [(uuid, d) for d in seen]


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def rebuild_annotations(conn: sqlite3.Connection, sensory_dir: PathLike) -> int:
    """Rebuild ``annotations``/``descriptors`` from the sidecar files.

    Corrupt sidecars are skipped, never fatal (a bad file must not break
    listing for the other roasts). Returns the number of indexed records.
    """
    rows: list[tuple] = []
    descriptors: list[tuple[str, str]] = []
    for path in sorted(Path(sensory_dir).glob("*.json")):
        try:
            record = read_record(sensory_dir, path.stem)
        except SensoryStoreError:
            continue
        if record is None:
            continue
        rows.append(_annotation_row(record))
        descriptors.extend(_descriptor_rows(record))
    with conn:
        conn.execute("DELETE FROM annotations")
        conn.execute("DELETE FROM descriptors")
        conn.executemany(_INSERT_ANNOTATION, rows)
        conn.executemany(
            "INSERT OR REPLACE INTO descriptors (roast_uuid, descriptor)"
            " VALUES (?,?)",
            descriptors,
        )
    return len(rows)


def upsert_annotation(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    """Sync the index with one stored (or updated) record."""
    with conn:
        conn.execute(_INSERT_ANNOTATION, _annotation_row(record))
        conn.execute(
            "DELETE FROM descriptors WHERE roast_uuid = ?",
            (record["roast_uuid"],),
        )
        conn.executemany(
            "INSERT OR REPLACE INTO descriptors (roast_uuid, descriptor)"
            " VALUES (?,?)",
            _descriptor_rows(record),
        )


def remove_annotation(conn: sqlite3.Connection, roast_uuid: str) -> None:
    """Drop a record's index rows (after sidecar deletion)."""
    with conn:
        conn.execute(
            "DELETE FROM annotations WHERE roast_uuid = ?", (roast_uuid,)
        )
        conn.execute(
            "DELETE FROM descriptors WHERE roast_uuid = ?", (roast_uuid,)
        )


def upsert_roast(
    conn: sqlite3.Connection,
    roast_uuid: str,
    source_file: Optional[str] = None,
    roast_date: Optional[str] = None,
) -> None:
    """Insert or update a roast in the universe of known roasts."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO roasts (roast_uuid, source_file, roast_date)"
            " VALUES (?,?,?)",
            (roast_uuid, source_file, roast_date),
        )


def get_roast(conn: sqlite3.Connection, roast_uuid: str) -> Optional[dict[str, Any]]:
    """Return the registered roast row for ``roast_uuid``, or ``None``."""
    cur = conn.execute(
        "SELECT * FROM roasts WHERE roast_uuid = ?", (roast_uuid,)
    )
    row = cur.fetchone()
    return dict(row) if row is not None else None


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def list_roasts(
    conn: sqlite3.Connection, annotated: Optional[bool] = None
) -> list[dict[str, Any]]:
    """List known roasts with their annotation summary.

    The result is the union of the registered roast universe and the
    annotated records (a sidecar may exist for a roast never registered).
    Each row carries ``annotated`` plus the annotation summary columns
    (``None`` when unannotated). ``annotated`` filters to roasts with
    (``True``) or without (``False``) a sidecar; ``None`` returns all.
    Rows are ordered by roast date (unknown dates last) then uuid.
    """
    registered: dict[str, dict[str, Any]] = {
        row["roast_uuid"]: dict(row)
        for row in conn.execute("SELECT * FROM roasts")
    }
    annotations: dict[str, dict[str, Any]] = {
        row["roast_uuid"]: dict(row)
        for row in conn.execute("SELECT * FROM annotations")
    }

    merged: dict[str, dict[str, Any]] = {}
    for uuid, reg in registered.items():
        ann = annotations.get(uuid)
        merged[uuid] = {
            "roast_uuid": uuid,
            "source_file": ann["source_file"] if ann else reg["source_file"],
            "roast_date": ann["roast_date"] if ann else reg["roast_date"],
            "annotated": ann is not None,
            "n_cuppings": ann["n_cuppings"] if ann else None,
            "best_total": ann["best_total"] if ann else None,
            "last_cupping_date": ann["last_cupping_date"] if ann else None,
        }
    for uuid, ann in annotations.items():
        if uuid in merged:
            continue
        merged[uuid] = {
            "roast_uuid": uuid,
            "source_file": ann["source_file"],
            "roast_date": ann["roast_date"],
            "annotated": True,
            "n_cuppings": ann["n_cuppings"],
            "best_total": ann["best_total"],
            "last_cupping_date": ann["last_cupping_date"],
        }

    rows = [
        r for r in merged.values()
        if annotated is None or r["annotated"] == annotated
    ]
    rows.sort(
        key=lambda r: (
            r["roast_date"] is None, r["roast_date"] or "", r["roast_uuid"]
        )
    )
    return rows


def search_records(
    conn: sqlite3.Connection,
    descriptor: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Search annotated records; all filters are AND-combined.

    ``descriptor`` is a case-insensitive substring match over the
    descriptors of any cupping. ``date_from``/``date_to`` bound the roast
    date (inclusive, ISO dates); records without a roast date are excluded
    by any date filter. ``min_score``/``max_score`` bound a record's best
    cupping total. Invalid dates raise :class:`SensoryStoreError`.
    """
    where: list[str] = []
    params: list[Any] = []
    if descriptor is not None:
        escaped = (
            descriptor.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        where.append(
            "roast_uuid IN (SELECT d.roast_uuid FROM descriptors d"
            " WHERE LOWER(d.descriptor) LIKE '%' || LOWER(?) || '%'"
            " ESCAPE '\\')"
        )
        params.append(escaped)
    if date_from is not None:
        _parse_iso_date(date_from, "date_from")
        where.append("roast_date >= ?")
        params.append(date_from)
    if date_to is not None:
        _parse_iso_date(date_to, "date_to")
        where.append("roast_date <= ?")
        params.append(date_to)
    if min_score is not None:
        where.append("best_total >= ?")
        params.append(min_score)
    if max_score is not None:
        where.append("best_total <= ?")
        params.append(max_score)

    sql = "SELECT * FROM annotations"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY roast_date IS NULL, roast_date, roast_uuid"
    return [dict(row) for row in conn.execute(sql, params)]
