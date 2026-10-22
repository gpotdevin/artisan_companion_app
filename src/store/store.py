"""The sensory store facade: CRUD and search over one sensory folder.

:class:`SensoryStore` owns a ``sensory/`` folder of JSON sidecars (one
per roast, keyed by ``roastUUID``) plus the SQLite index inside it. The
sidecars are the system of record; the index is rebuilt from them on
every open and updated on every mutation. The store never reads or
writes ``.alog`` files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from . import index, sidecars
from .errors import SensoryStoreError
from .schema import (
    DEFAULT_RADAR_LABELS,
    _parse_roast_date,
    check_roast_uuid,
    new_record,
    normalize_cupping,
    normalize_media,
    normalize_radar,
    normalize_roast_ref,
)

PathLike = Union[str, Path]


class SensoryStore:
    """Sensory sidecar store rooted at one folder (default ``sensory``).

    The folder is created if missing. Use as a context manager, or call
    :meth:`close` to release the index database::

        with SensoryStore(logs_dir / "sensory") as store:
            record = store.add_cupping(uuid, {...})

    All mutating methods return the freshly stored record as it now
    exists on disk (derived fields recomputed). A roast with no sidecar
    yet is a normal state: :meth:`get` returns ``None`` for it, and
    :meth:`get_or_create` builds the empty record on first annotation.
    """

    def __init__(self, sensory_dir: PathLike = "sensory") -> None:
        self._dir = Path(sensory_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._conn = index.open_index(self._dir)
        index.rebuild_annotations(self._conn, self._dir)

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the index database. The store must not be used after."""
        self._conn.close()

    def __enter__(self) -> "SensoryStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @property
    def sensory_dir(self) -> Path:
        """The folder holding the sidecars and the index file."""
        return self._dir

    # -- record-level CRUD --------------------------------------------------

    def create(
        self, roast_uuid: str, roast_ref: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Create an empty record for ``roast_uuid``; error if one exists.

        ``roast_ref`` (``{"file": ..., "date": ...}``) is filled from the
        registered roast data when not provided (see
        :meth:`register_roast`). Returns the stored record.
        """
        uuid = check_roast_uuid(roast_uuid)
        if sidecars.record_path(self._dir, uuid).exists():
            raise SensoryStoreError(f"{uuid}: sensory record already exists")
        record = new_record(uuid, roast_ref)
        self._backfill_roast_ref(record)
        return self._save(record)

    def get(self, roast_uuid: str) -> Optional[dict[str, Any]]:
        """Return the record for ``roast_uuid``, or ``None`` if unannotated."""
        return sidecars.read_record(self._dir, roast_uuid)

    def get_or_create(
        self, roast_uuid: str, roast_ref: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Return the record, creating an empty one if needed."""
        record = self.get(roast_uuid)
        if record is not None:
            return record
        return self.create(roast_uuid, roast_ref)

    def update(
        self,
        roast_uuid: str,
        roast_ref: Optional[dict[str, Any]] = None,
        radar: Optional[dict[str, Any]] = None,
        defects_observed: Optional[dict[str, bool]] = None,
        media: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Update top-level sections of an existing record.

        ``roast_ref`` and ``defects_observed`` are merged key by key
        (omitted keys keep their value); ``radar`` and ``media`` replace
        the stored section wholesale when given. Returns the stored
        record. Changing the roast date recomputes every cupping's
        ``days_after_roast``.
        """
        record = self._require(roast_uuid)
        if roast_ref is not None:
            new_ref = normalize_roast_ref(roast_ref)
            for key, value in new_ref.items():
                if value is not None:
                    record["roast_ref"][key] = value
        if radar is not None:
            record["radar"] = normalize_radar(radar)
        if defects_observed is not None:
            record["defects_observed"] = {
                **record["defects_observed"],
                **defects_observed,
            }
        if media is not None:
            record["media"] = normalize_media(media)
        return self._save(record)

    def delete(self, roast_uuid: str) -> bool:
        """Delete the record and its index rows; ``False`` if none existed."""
        uuid = check_roast_uuid(roast_uuid)
        existed = sidecars.delete_record(self._dir, uuid)
        if existed:
            index.remove_annotation(self._conn, uuid)
        return existed

    # -- cupping sessions ----------------------------------------------------

    def add_cupping(
        self, roast_uuid: str, cupping: dict[str, Any]
    ) -> dict[str, Any]:
        """Append a cupping session (``date`` required, ISO) to the record.

        ``days_after_roast`` is computed from the record's roast date;
        ``total`` from the scores. Returns the stored record.
        """
        record = self._require(roast_uuid)
        roast_date = _parse_roast_date(record["roast_ref"].get("date"))
        record["cuppings"].append(
            normalize_cupping(cupping, roast_date=roast_date)
        )
        return self._save(record)

    def edit_cupping(
        self, roast_uuid: str, cupping_index: int, changes: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge ``changes`` into the cupping at ``cupping_index`` (0-based).

        ``scores`` merges key by key; ``date``, ``descriptors`` and
        ``notes`` replace when present. Derived fields are recomputed.
        """
        record = self._require(roast_uuid)
        cuppings = record["cuppings"]
        if not isinstance(cupping_index, int) or isinstance(cupping_index, bool) \
                or not 0 <= cupping_index < len(cuppings):
            raise SensoryStoreError(
                f"{roast_uuid}: no cupping at index {cupping_index!r}"
            )
        current = cuppings[cupping_index]
        merged = {
            k: v for k, v in changes.items()
            if k not in ("scores", "days_after_roast", "total")
        }
        if "scores" in changes:
            merged["scores"] = {**current["scores"], **changes["scores"]}
        cuppings[cupping_index] = {**current, **merged}
        return self._save(record)

    def remove_cupping(self, roast_uuid: str, cupping_index: int) -> dict[str, Any]:
        """Remove the cupping at ``cupping_index`` (0-based)."""
        record = self._require(roast_uuid)
        cuppings = record["cuppings"]
        if not isinstance(cupping_index, int) or isinstance(cupping_index, bool) \
                or not 0 <= cupping_index < len(cuppings):
            raise SensoryStoreError(
                f"{roast_uuid}: no cupping at index {cupping_index!r}"
            )
        del cuppings[cupping_index]
        return self._save(record)

    # -- radar and native sync -------------------------------------------------

    def update_radar(
        self,
        roast_uuid: str,
        values: list[float],
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Update the flavor radar ``values`` (and ``labels`` when given).

        ``labels`` default to the stored labels (the Artisan defaults for
        a fresh record). Returns the stored record.
        """
        record = self._require(roast_uuid)
        record["radar"] = normalize_radar({
            "labels": list(labels) if labels is not None
            else record["radar"]["labels"] or list(DEFAULT_RADAR_LABELS),
            "values": list(values) if values is not None else [],
        })
        return self._save(record)

    def set_native_sync(
        self, roast_uuid: str, fields: list[str]
    ) -> dict[str, Any]:
        """Stamp a native sync of ``fields`` with the current UTC time.

        ``native_sync.last_synced`` is stored in ISO 8601 UTC. Returns
        the stored record.
        """
        record = self._require(roast_uuid)
        record["native_sync"] = {
            "last_synced": datetime.now(timezone.utc).isoformat(),
            "fields": [str(f) for f in fields],
        }
        return self._save(record)

    # -- roast registry and queries --------------------------------------------

    def register_roast(
        self,
        roast_uuid: str,
        source_file: Optional[str] = None,
        roast_date: Optional[str] = None,
    ) -> None:
        """Register a roast in the universe of known roasts.

        Filled from the alog roast index; lets :meth:`list_roasts` report
        roasts without annotations, and backfills ``roast_ref`` of an
        existing record when its file/date are still unknown.
        """
        uuid = check_roast_uuid(roast_uuid)
        index.upsert_roast(self._conn, uuid, source_file, roast_date)
        record = self.get(uuid)
        if record is None:
            return
        ref = record["roast_ref"]
        changed = False
        if ref["file"] is None and source_file:
            ref["file"], changed = source_file, True
        if ref["date"] is None and roast_date:
            ref["date"], changed = roast_date, True
        if changed:
            self._save(record)

    def list_roasts(
        self, annotated: Optional[bool] = None
    ) -> list[dict[str, Any]]:
        """List known roasts with annotation status (see ``index.list_roasts``)."""
        return index.list_roasts(self._conn, annotated)

    def search(
        self,
        descriptor: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Search annotated records (see ``index.search_records``)."""
        return index.search_records(
            self._conn,
            descriptor=descriptor,
            date_from=date_from,
            date_to=date_to,
            min_score=min_score,
            max_score=max_score,
        )

    # -- internals -------------------------------------------------------------

    def _require(self, roast_uuid: str) -> dict[str, Any]:
        """Load the record or raise -- mutations need an existing record."""
        record = self.get(roast_uuid)
        if record is None:
            raise SensoryStoreError(f"{roast_uuid}: no sensory record")
        return record

    def _backfill_roast_ref(self, record: dict[str, Any]) -> None:
        """Fill a new record's roast_ref from the registry when possible."""
        reg = index.get_roast(self._conn, record["roast_uuid"])
        if reg is None:
            return
        ref = record["roast_ref"]
        if ref["file"] is None and reg["source_file"]:
            ref["file"] = reg["source_file"]
        if ref["date"] is None and reg["roast_date"]:
            ref["date"] = reg["roast_date"]

    def _save(self, record: dict[str, Any]) -> dict[str, Any]:
        """Persist a record atomically and sync the index with the result."""
        sidecars.write_record(self._dir, record)
        stored = sidecars.read_record(self._dir, record["roast_uuid"])
        if stored is None:  # pragma: no cover - write just succeeded
            raise SensoryStoreError(
                f"{record['roast_uuid']}: sidecar missing after write"
            )
        index.upsert_annotation(self._conn, stored)
        return stored
