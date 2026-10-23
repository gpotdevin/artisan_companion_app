"""Native Android facade over the artisan-companion core (Chaquopy).

The native Kotlin UI (Jetpack Compose) calls these functions through
Chaquopy and parses the returned JSON strings with kotlinx.serialization.
The data contract is identical to the FastAPI app in ``src/app/main.py``, so
the native app and the web app stay interchangeable.

The core (``alog_core``, ``store``, ``sync``) is used unchanged -- this module
only wires on-device paths and serializes results. It needs no third-party
packages (everything is stdlib), so the Chaquopy ``pip`` block can stay empty.

State is module-level (like the FastAPI app): call :func:`init` once with the
on-device ``logs_dir`` / ``sensory_dir`` before anything else.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from alog_core import build_index, list_roasts as alog_list_roasts, parse_profile
from store import (
    DEFAULT_RADAR_LABELS,
    DEFECT_KEYS,
    SCORE_KEYS,
    SensoryStore,
    SensoryStoreError,
)

_LOGS_DIR: Optional[Path] = None
_SENSORY_DIR: Optional[Path] = None
_ROAST_INDEX: dict[str, dict[str, Any]] = {}
_STORE: Optional[SensoryStore] = None


def _ensure_init() -> None:
    if _LOGS_DIR is None or _SENSORY_DIR is None or _STORE is None:
        raise RuntimeError("api.init(logs_dir, sensory_dir) was not called")


def _roast_ref_for(roast_uuid: str) -> dict[str, Optional[str]]:
    idx = _ROAST_INDEX[roast_uuid]
    return {"file": idx.get("source_file"), "date": idx.get("roast_isodate")}


def _ensure_record(roast_uuid: str) -> None:
    """Create an empty sensory record if the roast has none yet."""
    assert _STORE is not None
    if _STORE.get(roast_uuid) is None:
        if roast_uuid not in _ROAST_INDEX:
            raise RuntimeError("roast not found in logs")
        _STORE.create(roast_uuid, _roast_ref_for(roast_uuid))


# ---------------------------------------------------------------
# Lifecycle / index
# ---------------------------------------------------------------

def init(logs_dir: str, sensory_dir: str) -> str:
    """Point the facade at on-device storage and build the roast index."""
    global _LOGS_DIR, _SENSORY_DIR, _STORE
    logs = Path(logs_dir)
    sensory = Path(sensory_dir)
    logs.mkdir(parents=True, exist_ok=True)
    sensory.mkdir(parents=True, exist_ok=True)
    _LOGS_DIR = logs
    _SENSORY_DIR = sensory
    _STORE = SensoryStore(sensory)
    rebuild_index()
    return json.dumps({"ok": True, "roast_count": len(_ROAST_INDEX)})


def rebuild_index() -> str:
    """Re-scan the logs folder and refresh the roast index + registry."""
    _ensure_init()
    assert _LOGS_DIR is not None and _SENSORY_DIR is not None and _STORE is not None
    index_db = _SENSORY_DIR / "roast_index.sqlite"
    build_index(_LOGS_DIR, index_db)
    rows = alog_list_roasts(index_db)
    _ROAST_INDEX.clear()
    _ROAST_INDEX.update({r["roast_id"]: r for r in rows})
    for roast_id, roast_data in _ROAST_INDEX.items():
        try:
            _STORE.register_roast(
                roast_id,
                source_file=roast_data.get("source_file"),
                roast_date=roast_data.get("roast_isodate"),
            )
        except SensoryStoreError:
            pass
    return json.dumps({"ok": True, "roast_count": len(_ROAST_INDEX)})


# ---------------------------------------------------------------
# Roast listing
# ---------------------------------------------------------------

def list_roasts() -> str:
    """All roasts from the alog index, merged with annotation status."""
    _ensure_init()
    assert _STORE is not None
    annotated = {r["roast_uuid"]: r for r in _STORE.list_roasts()}
    result: list[dict[str, Any]] = []
    for roast_id, idx in _ROAST_INDEX.items():
        ann = annotated.get(roast_id)
        # store.list_roasts() returns a row for every registered roast; the row's
        # own "annotated" flag says whether a sidecar actually exists.
        is_ann = bool(ann and ann.get("annotated"))
        result.append({
            "roast_uuid": roast_id,
            "source_file": idx.get("source_file"),
            "title": idx.get("title"),
            "beans": idx.get("beans"),
            "roast_date": idx.get("roast_isodate"),
            "green_weight_g": idx.get("green_weight_g"),
            "roasted_weight_g": idx.get("roasted_weight_g"),
            "drop_bt_c": idx.get("drop_bt_c"),
            "fcs_time_s": idx.get("fcs_time_s"),
            "total_time_s": idx.get("total_time_s"),
            "parse_ok": bool(idx.get("parse_ok")),
            "error_msg": idx.get("error_msg"),
            "annotated": is_ann,
            "n_cuppings": (ann.get("n_cuppings") or 0) if is_ann else 0,
            "best_total": ann.get("best_total") if is_ann else None,
            "last_cupping_date": ann.get("last_cupping_date") if is_ann else None,
        })
    result.sort(
        key=lambda r: (r.get("roast_date") or "", r.get("source_file") or ""),
        reverse=True,
    )
    return json.dumps({"roasts": result})


# ---------------------------------------------------------------
# Sensory record CRUD
# ---------------------------------------------------------------

def get_sensory(roast_uuid: str) -> str:
    """The sensory record for a roast, or ``null`` when unannotated."""
    _ensure_init()
    assert _STORE is not None
    return json.dumps(_STORE.get(roast_uuid))


def create_sensory(roast_uuid: str) -> str:
    _ensure_init()
    assert _STORE is not None
    if roast_uuid not in _ROAST_INDEX:
        raise RuntimeError("roast not found in logs")
    if _STORE.get(roast_uuid) is not None:
        raise RuntimeError("sensory record already exists")
    return json.dumps(_STORE.create(roast_uuid, _roast_ref_for(roast_uuid)))


def update_sensory(roast_uuid: str, body_json: str) -> str:
    """Update top-level sections. ``body_json`` is a JSON object with any of
    ``roast_ref``, ``radar``, ``defects_observed``, ``media``."""
    _ensure_init()
    assert _STORE is not None
    body = json.loads(body_json)
    record = _STORE.update(
        roast_uuid,
        roast_ref=body.get("roast_ref"),
        radar=body.get("radar"),
        defects_observed=body.get("defects_observed"),
        media=body.get("media"),
    )
    return json.dumps(record)


def delete_sensory(roast_uuid: str) -> str:
    _ensure_init()
    assert _STORE is not None
    existed = _STORE.delete(roast_uuid)
    return json.dumps({"deleted": existed, "roast_uuid": roast_uuid})


# ---------------------------------------------------------------
# Cupping sessions
# ---------------------------------------------------------------

def add_cupping(roast_uuid: str, cupping_json: str) -> str:
    _ensure_init()
    assert _STORE is not None
    cupping = json.loads(cupping_json)
    if "date" not in cupping:
        raise RuntimeError("cupping date is required")
    _ensure_record(roast_uuid)
    return json.dumps(_STORE.add_cupping(roast_uuid, cupping))


def edit_cupping(roast_uuid: str, cupping_index: int, changes_json: str) -> str:
    _ensure_init()
    assert _STORE is not None
    return json.dumps(
        _STORE.edit_cupping(roast_uuid, cupping_index, json.loads(changes_json))
    )


def remove_cupping(roast_uuid: str, cupping_index: int) -> str:
    _ensure_init()
    assert _STORE is not None
    return json.dumps(_STORE.remove_cupping(roast_uuid, cupping_index))


# ---------------------------------------------------------------
# Radar
# ---------------------------------------------------------------

def update_radar(roast_uuid: str, values_json: str, labels_json: str = "null") -> str:
    """Update the flavor radar. ``labels_json`` is a JSON array or ``"null"``."""
    _ensure_init()
    assert _STORE is not None
    values = json.loads(values_json)
    labels = None if labels_json in (None, "null") else json.loads(labels_json)
    _ensure_record(roast_uuid)
    return json.dumps(_STORE.update_radar(roast_uuid, values, labels))


def radar_labels() -> str:
    return json.dumps({"labels": list(DEFAULT_RADAR_LABELS)})


def score_keys() -> str:
    return json.dumps({"keys": list(SCORE_KEYS)})


def defect_keys() -> str:
    return json.dumps({"keys": list(DEFECT_KEYS)})


# ---------------------------------------------------------------
# Profile viewer
# ---------------------------------------------------------------

def get_profile(roast_uuid: str) -> str:
    """Full profile for the viewer: curves, markers, events, phases, sensory,
    background comparison and meta. Same shape as ``GET /api/roasts/{uuid}/profile``."""
    _ensure_init()
    assert _LOGS_DIR is not None and _STORE is not None
    if roast_uuid not in _ROAST_INDEX:
        raise RuntimeError("roast not found")
    idx = _ROAST_INDEX[roast_uuid]
    source_file = idx.get("source_file")
    alog_path = _LOGS_DIR / source_file
    if not alog_path.exists():
        raise RuntimeError("roast file not found")

    profile = parse_profile(alog_path)
    ror_json = [v if v is not None else None for v in profile.ror_c_per_min]
    markers = {
        name: {
            "time_s": m.time_s,
            "temp_bt_c": m.temp_bt_c,
            "temp_et_c": m.temp_et_c,
        }
        for name, m in profile.markers.items()
    }
    events = [
        {
            "time_s": e.time_s,
            "index": e.index,
            "type_label": e.type_label,
            "slider_value": e.slider_value,
            "label": e.label,
        }
        for e in profile.events
    ]

    phases: dict[str, Any] = {}
    if profile.phases:
        phases = {
            "drying_s": profile.phases.get("dry_s"),
            "maillard_s": profile.phases.get("mid_s"),
            "development_s": profile.phases.get("finish_s"),
            "total_s": profile.phases.get("total_s"),
        }
    else:
        charge = markers.get("CHARGE")
        dry = markers.get("DRY")
        fcs = markers.get("FCs")
        drop = markers.get("DROP")
        if charge and dry:
            phases["drying_s"] = dry["time_s"] - charge["time_s"]
        if dry and fcs:
            phases["maillard_s"] = fcs["time_s"] - dry["time_s"]
        if fcs and drop:
            phases["development_s"] = drop["time_s"] - fcs["time_s"]
        if charge and drop:
            phases["total_s"] = drop["time_s"] - charge["time_s"]

    rec = _STORE.get(roast_uuid)
    sensory = None
    if rec:
        sensory = {
            "cuppings": rec.get("cuppings", []),
            "radar": rec.get("radar", {}),
            "defects_observed": rec.get("defects_observed", {}),
            "best_total": rec.get("best_total"),
            "n_cuppings": len(rec.get("cuppings", [])),
        }

    background = None
    bg_uuid = profile.meta.backgroundUUID
    if bg_uuid and bg_uuid in _ROAST_INDEX:
        bg_file = _ROAST_INDEX[bg_uuid].get("source_file")
        bg_path = _LOGS_DIR / bg_file
        if bg_path.exists():
            try:
                bg = parse_profile(bg_path)
                bg_charge = (
                    bg.markers["CHARGE"].time_s
                    if bg.markers and "CHARGE" in bg.markers
                    else 0.0
                )
                background = {
                    "times_s": [t - bg_charge for t in bg.times_s],
                    "bt_c": bg.bt_c,
                }
            except Exception:
                pass

    response = {
        "roast_uuid": roast_uuid,
        "source_file": source_file,
        "title": idx.get("title"),
        "beans": idx.get("beans"),
        "roast_date": idx.get("roast_isodate"),
        "green_weight_g": idx.get("green_weight_g"),
        "roasted_weight_g": idx.get("roasted_weight_g"),
        "drop_bt_c": idx.get("drop_bt_c"),
        "times_s": profile.times_s,
        "bt_c": profile.bt_c,
        "et_c": profile.et_c,
        "ror_c_per_min": ror_json,
        "markers": markers,
        "events": events,
        "phases": phases,
        "sensory": sensory,
        "background": background,
        "meta": {
            "artisan_version": profile.meta.artisan_version,
            "roastertype": profile.meta.roastertype,
            "ambient_temp_c": profile.meta.ambient_temp_c,
            "sampling_interval_s": profile.meta.sampling_interval_s,
        },
    }
    return json.dumps(response)
