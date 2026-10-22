"""Sensory record schema v1: constants, validation, defensive normalization.

A sensory record is the JSON sidecar defined in
``docs/implementation-plan.md`` section 2: one file per roast, keyed by
``roastUUID``, holding cupping sessions, the flavor radar, defect
observations, native-sync bookkeeping and media references.

Records read from disk (possibly hand-edited or written by a future
version) are normalized key by key: unknown keys are dropped and known
keys are coerced; only integrity failures -- an unsupported
``schema_version``, a mismatched ``roast_uuid`` or an invalid cupping --
raise :class:`~store.errors.SensoryStoreError`. Derived fields are never
trusted from disk: ``cuppings[i].total`` is recomputed from the stored
scores and ``cuppings[i].days_after_roast`` from the cupping date minus
the roast date, so the two can never go inconsistent. When the roast
date is unknown, ``days_after_roast`` is stored as ``null``.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from .errors import SensoryStoreError

SCHEMA_VERSION = 1

#: Sidecar filename bodies are restricted to a safe filename charset:
#: corpus ``roastUUID`` values are 32-hex, the alog_core fallback ids are
#: 16-hex, and anything else must at least not escape the sensory folder.
_UUID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")

#: Artisan's default radar axis labels (``flavorlabels``).
DEFAULT_RADAR_LABELS: tuple[str, ...] = (
    "Acidity", "Aftertaste", "Clean Cup", "Head", "Fragrance",
    "Sweetness", "Aroma", "Balance", "Body",
)

#: The ten native Artisan defect flags.
DEFECT_KEYS: tuple[str, ...] = (
    "heavyFC", "lowFC", "lightCut", "darkCut", "drops",
    "oily", "uneven", "tipping", "scorching", "divots",
)

#: The ten SCA attribute score keys of a cupping (0-10 each). The
#: ``defects`` score is a non-negative penalty and ``total`` is derived.
SCORE_KEYS: tuple[str, ...] = (
    "fragrance_aroma", "flavor", "aftertaste", "acidity", "body",
    "balance", "uniformity", "clean_cup", "sweetness", "overall",
)


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------

def check_roast_uuid(value: Any) -> str:
    """Return ``value`` as a validated sidecar key (roastUUID).

    Raises :class:`SensoryStoreError` for anything that is not a non-empty
    string of filename-safe characters; this keeps sidecar paths inside the
    sensory folder.
    """
    if not isinstance(value, str) or not _UUID_RE.match(value):
        raise SensoryStoreError(f"invalid roast_uuid {value!r}")
    return value


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None


def _as_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, (bool, int)) else False


def _parse_iso_date(value: Any, what: str) -> Optional[date]:
    """Parse an ISO 8601 calendar date (``YYYY-MM-DD``).

    Raises :class:`SensoryStoreError` when ``value`` is not a string or
    not a valid ISO date. Used for dates the store must be able to trust
    (cupping dates, search filters); roast-ref dates use the lenient
    :func:`_parse_roast_date` instead.
    """
    if not isinstance(value, str):
        raise SensoryStoreError(f"{what}: expected an ISO date string, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise SensoryStoreError(f"{what}: invalid ISO date {value!r}") from None


def _parse_roast_date(value: Any) -> Optional[date]:
    """Lenient variant for roast-ref dates (return ``None`` when unusable)."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Section normalizers (defensive: unknown keys dropped, bad values coerced)
# ---------------------------------------------------------------------------

def normalize_roast_ref(raw: Any) -> dict[str, Optional[str]]:
    ref = raw if isinstance(raw, dict) else {}
    return {
        "file": _as_str(ref.get("file")),
        "date": _as_str(ref.get("date")),
    }


def normalize_radar(raw: Any) -> dict[str, list]:
    """Normalize a radar section; non-numeric values are dropped silently."""
    d = raw if isinstance(raw, dict) else {}
    labels = [
        s for s in (_as_str(v) for v in d.get("labels") or [])
        if s is not None
    ]
    values = [
        v for v in (_as_float(x) for x in d.get("values") or [])
        if v is not None
    ]
    return {"labels": labels, "values": values}


def normalize_defects(raw: Any) -> dict[str, bool]:
    d = raw if isinstance(raw, dict) else {}
    return {key: _as_bool(d.get(key)) for key in DEFECT_KEYS}


def normalize_native_sync(raw: Any) -> dict[str, Any]:
    d = raw if isinstance(raw, dict) else {}
    fields = [
        s for s in (_as_str(v) for v in d.get("fields") or [])
        if s is not None
    ]
    return {"last_synced": _as_str(d.get("last_synced")), "fields": fields}


def normalize_media(raw: Any) -> list[dict[str, Any]]:
    entries = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        path = _as_str(item.get("path"))
        if path is None:
            continue
        entry = {"kind": _as_str(item.get("kind")), "path": path}
        # Unknown keys ride along: the schema may grow additive fields.
        entry.update({k: v for k, v in item.items() if k not in entry})
        entries.append(entry)
    return entries


def _normalize_scores(raw: Any) -> dict[str, float]:
    """Validate/coerce a cupping's scores; ``total`` is recomputed here."""
    d = raw if isinstance(raw, dict) else {}
    scores: dict[str, float] = {}
    for key in SCORE_KEYS:
        if key not in d:
            continue
        v = _as_float(d[key])
        if v is None or not 0.0 <= v <= 10.0:
            raise SensoryStoreError(
                f"scores.{key}: expected a number in 0-10, got {d[key]!r}"
            )
        scores[key] = v
    if "defects" in d:
        v = _as_float(d["defects"])
        if v is None or v < 0.0:
            raise SensoryStoreError(
                f"scores.defects: expected a non-negative penalty, got {d['defects']!r}"
            )
        scores["defects"] = v
    attrs = sum(scores.get(k, 0.0) for k in SCORE_KEYS if k in scores)
    if scores:
        scores["total"] = round(attrs - scores.get("defects", 0.0), 2)
    return scores


# ---------------------------------------------------------------------------
# Records and cuppings
# ---------------------------------------------------------------------------

def new_record(roast_uuid: str, roast_ref: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Build a fresh, empty schema-v1 record for ``roast_uuid``."""
    return {
        "schema_version": SCHEMA_VERSION,
        "roast_uuid": check_roast_uuid(roast_uuid),
        "roast_ref": normalize_roast_ref(roast_ref),
        "cuppings": [],
        "radar": normalize_radar({"labels": list(DEFAULT_RADAR_LABELS)}),
        "defects_observed": {key: False for key in DEFECT_KEYS},
        "native_sync": normalize_native_sync(None),
        "media": [],
    }


def normalize_cupping(
    raw: Any, roast_date: Optional[date] = None
) -> dict[str, Any]:
    """Normalize one cupping session against ``roast_date``.

    ``date`` must be a valid ISO date (raises otherwise). ``scores`` is
    validated per key (see :func:`_normalize_scores`); unknown keys are
    dropped. ``days_after_roast`` and ``total`` are always recomputed and
    any values supplied for them in ``raw`` are ignored.
    """
    if not isinstance(raw, dict):
        raise SensoryStoreError(f"cupping: expected an object, got {raw!r}")
    cup_date = _parse_iso_date(raw.get("date"), "cupping.date")
    descriptors = [
        s for s in (_as_str(v) for v in raw.get("descriptors") or [])
        if s is not None
    ]
    notes = _as_str(raw.get("notes")) or ""
    cupping = {
        "date": cup_date.isoformat(),
        "days_after_roast": (
            (cup_date - roast_date).days if roast_date is not None else None
        ),
        "scores": _normalize_scores(raw.get("scores")),
        "descriptors": descriptors,
        "notes": notes,
    }
    return cupping


def normalize_record(raw: Any, roast_uuid: Optional[str] = None) -> dict[str, Any]:
    """Normalize a full sidecar payload as read from disk (never mutated).

    ``roast_uuid`` is the expected key (the sidecar filename); a record
    carrying a different ``roast_uuid`` raises. A missing
    ``schema_version`` is tolerated as the current version; a different
    one raises. Missing or partial sections come back as defaults.
    """
    if not isinstance(raw, dict):
        raise SensoryStoreError(f"record: expected an object, got {raw!r}")
    version = raw.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise SensoryStoreError(
            f"record: unsupported schema_version {version!r}"
            f" (expected {SCHEMA_VERSION})"
        )
    uuid = check_roast_uuid(raw.get("roast_uuid") or roast_uuid)
    if roast_uuid is not None and raw.get("roast_uuid") not in (None, roast_uuid):
        raise SensoryStoreError(
            f"record: roast_uuid {raw.get('roast_uuid')!r} does not"
            f" match expected {roast_uuid!r}"
        )
    roast_ref = normalize_roast_ref(raw.get("roast_ref"))
    roast_date = _parse_roast_date(roast_ref["date"])
    cuppings = [
        normalize_cupping(c, roast_date=roast_date)
        for c in (raw.get("cuppings") or [])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "roast_uuid": uuid,
        "roast_ref": roast_ref,
        "cuppings": cuppings,
        "radar": normalize_radar(raw.get("radar")),
        "defects_observed": normalize_defects(raw.get("defects_observed")),
        "native_sync": normalize_native_sync(raw.get("native_sync")),
        "media": normalize_media(raw.get("media")),
    }


def refresh_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a fully re-normalized copy of ``record``.

    Called before every write: every section is coerced and every derived
    field (``cuppings[i].total``, ``cuppings[i].days_after_roast``) is
    recomputed, so nothing can ever be stored inconsistently.
    """
    return normalize_record(record, roast_uuid=record.get("roast_uuid"))
