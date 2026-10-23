"""FastAPI backend for the sensory editor web app (M2b).

Endpoints:
- GET  /api/roasts              - list roasts from .alog logs dir
- GET  /api/roasts/{uuid}       - get sensory record for a roast
- POST /api/roasts/{uuid}       - create sensory record for a roast
- PUT  /api/roasts/{uuid}       - update sensory record top-level sections
- DELETE /api/roasts/{uuid}    - delete sensory record
- POST /api/roasts/{uuid}/cupping - add cupping session
- PUT  /api/roasts/{uuid}/cupping/{index} - edit cupping session
- DELETE /api/roasts/{uuid}/cupping/{index} - remove cupping session
- PUT  /api/roasts/{uuid}/radar - update radar values

All persistence goes through SensoryStore. The app reads .alog files
read-only and never writes to them (per guardrails).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

# Import from parent package
from alog_core import build_index, list_roasts as alog_list_roasts
from store import (
    DEFAULT_RADAR_LABELS,
    DEFECT_KEYS,
    SCORE_KEYS,
    SensoryStore,
    SensoryStoreError,
)

# Global state (initialized by startup event)
_LOGS_DIR: Path | None = None
_SENSORY_DIR: Path | None = None
_ROAST_INDEX: dict[str, dict[str, Any]] = {}
_SENSORY_STORE: SensoryStore | None = None

app = FastAPI(title="Artisan Companion - Sensory Editor")


# -----------------------------------------------------------
# Startup / shutdown
# -----------------------------------------------------------

@app.on_event("startup")
async def startup() -> None:
    """Build roast index from logs_dir and open the sensory store."""
    global _LOGS_DIR, _SENSORY_DIR, _ROAST_INDEX, _SENSORY_STORE

    # Parse command line args from sys.argv
    logs_dir: Path | None = None
    sensory_dir: Path | None = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--logs-dir" and i + 1 < len(sys.argv):
            logs_dir = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--sensory-dir" and i + 1 < len(sys.argv):
            sensory_dir = Path(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    # Defaults
    if logs_dir is None:
        default_logs = Path.cwd() / "logs"
        if default_logs.exists():
            logs_dir = default_logs
        else:
            logs_dir = Path.cwd()

    if sensory_dir is None:
        sensory_dir = logs_dir.parent / "sensory"

    _LOGS_DIR = logs_dir
    _SENSORY_DIR = sensory_dir

    # Ensure sensory dir exists
    sensory_dir.mkdir(parents=True, exist_ok=True)

    # Build roast index
    index_db = sensory_dir / "roast_index.sqlite"
    build_index(logs_dir, index_db)
    _ROAST_INDEX = {r["roast_id"]: r for r in alog_list_roasts(index_db)}

    # Register all known roasts with the sensory store
    _SENSORY_STORE = SensoryStore(sensory_dir)
    for roast_id, roast_data in _ROAST_INDEX.items():
        try:
            _SENSORY_STORE.register_roast(
                roast_id,
                source_file=roast_data.get("source_file"),
                roast_date=roast_data.get("roast_isodate"),
            )
        except SensoryStoreError:
            # Skip roasts that can't be registered
            pass


@app.on_event("shutdown")
async def shutdown() -> None:
    """Close the sensory store."""
    global _SENSORY_STORE
    if _SENSORY_STORE is not None:
        _SENSORY_STORE.close()
        _SENSORY_STORE = None


# -----------------------------------------------------------
# Helper functions
# -----------------------------------------------------------

def _get_store() -> SensoryStore:
    if _SENSORY_STORE is None:
        raise HTTPException(status_code=500, detail="Store not initialized")
    return _SENSORY_STORE


def _get_roasts_from_index() -> list[dict[str, Any]]:
    """Get all roasts from the alog index with annotation status."""
    store = _get_store()
    # List all known roasts with annotation status
    annotated_roasts = store.list_roasts()

    # Build a dict of annotated roasts for quick lookup
    annotated_map = {r["roast_uuid"]: r for r in annotated_roasts}

    # Result: merge index data with annotation status
    result = []
    for roast_id, index_data in _ROAST_INDEX.items():
        ann = annotated_map.get(roast_id)
        result.append({
            "roast_uuid": roast_id,
            "source_file": index_data.get("source_file"),
            "title": index_data.get("title"),
            "beans": index_data.get("beans"),
            "roast_date": index_data.get("roast_isodate"),
            "green_weight_g": index_data.get("green_weight_g"),
            "roasted_weight_g": index_data.get("roasted_weight_g"),
            "drop_bt_c": index_data.get("drop_bt_c"),
            "fcs_time_s": index_data.get("fcs_time_s"),
            "total_time_s": index_data.get("total_time_s"),
            "parse_ok": bool(index_data.get("parse_ok")),
            "error_msg": index_data.get("error_msg"),
            "annotated": ann is not None,
            "n_cuppings": ann.get("n_cuppings") if ann else 0,
            "best_total": ann.get("best_total") if ann else None,
            "last_cupping_date": ann.get("last_cupping_date") if ann else None,
        })

    # Sort by date (newest first), then by filename
    result.sort(
        key=lambda r: (
            r.get("roast_date") or "",
            r.get("source_file") or "",
        ),
        reverse=True,
    )
    return result


# -----------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------

@app.get("/api/roasts")
async def list_roasts() -> JSONResponse:
    """List all roasts from .alog logs with annotation status."""
    try:
        roasts = _get_roasts_from_index()
        return JSONResponse(content={"roasts": roasts})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/roasts/{roast_uuid}")
async def get_roast_record(roast_uuid: str) -> JSONResponse:
    """Get the sensory record for a specific roast."""
    try:
        store = _get_store()
        record = store.get(roast_uuid)
        if record is None:
            raise HTTPException(status_code=404, detail="Roast not found")
        return JSONResponse(content=record)
    except SensoryStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/roasts/{roast_uuid}")
async def create_roast_record(roast_uuid: str) -> JSONResponse:
    """Create an empty sensory record for a roast."""
    try:
        store = _get_store()
        # Check if roast exists in index
        if roast_uuid not in _ROAST_INDEX:
            raise HTTPException(status_code=404, detail="Roast not found in logs")

        index_data = _ROAST_INDEX[roast_uuid]
        roast_ref = {
            "file": index_data.get("source_file"),
            "date": index_data.get("roast_isodate"),
        }

        # Check if already exists
        if store.get(roast_uuid) is not None:
            raise HTTPException(
                status_code=409,
                detail="Sensory record already exists"
            )

        record = store.create(roast_uuid, roast_ref)
        return JSONResponse(content=record, status_code=201)
    except SensoryStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/roasts/{roast_uuid}")
async def update_roast_record(
    roast_uuid: str,
    request: Request,
) -> JSONResponse:
    """Update top-level sections of a sensory record."""
    try:
        store = _get_store()
        body = await request.json()

        # Validate that the roast exists in our universe
        if roast_uuid not in _ROAST_INDEX:
            raise HTTPException(status_code=404, detail="Roast not found in logs")

        record = store.get(roast_uuid)
        if record is None:
            raise HTTPException(status_code=404, detail="Sensory record not found")

        # Update with provided fields
        updated_record = store.update(
            roast_uuid,
            roast_ref=body.get("roast_ref"),
            radar=body.get("radar"),
            defects_observed=body.get("defects_observed"),
            media=body.get("media"),
        )
        return JSONResponse(content=updated_record)
    except SensoryStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/roasts/{roast_uuid}")
async def delete_roast_record(roast_uuid: str) -> JSONResponse:
    """Delete a sensory record."""
    try:
        store = _get_store()
        existed = store.delete(roast_uuid)
        if not existed:
            raise HTTPException(status_code=404, detail="Sensory record not found")
        return JSONResponse(content={"deleted": True, "roast_uuid": roast_uuid})
    except SensoryStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/roasts/{roast_uuid}/cupping")
async def add_cupping(roast_uuid: str, request: Request) -> JSONResponse:
    """Add a cupping session to a roast."""
    try:
        store = _get_store()
        cupping = await request.json()

        # Validate required field
        if "date" not in cupping:
            raise HTTPException(
                status_code=400,
                detail="Cupping date is required"
            )

        # Check if roast exists
        if roast_uuid not in _ROAST_INDEX:
            raise HTTPException(status_code=404, detail="Roast not found in logs")

        record = store.get(roast_uuid)
        if record is None:
            # Auto-create the record if it doesn't exist
            index_data = _ROAST_INDEX[roast_uuid]
            roast_ref = {
                "file": index_data.get("source_file"),
                "date": index_data.get("roast_isodate"),
            }
            store.create(roast_uuid, roast_ref)

        updated_record = store.add_cupping(roast_uuid, cupping)
        return JSONResponse(content=updated_record, status_code=201)
    except SensoryStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/roasts/{roast_uuid}/cupping/{cupping_index}")
async def edit_cupping(
    roast_uuid: str,
    cupping_index: int,
    request: Request,
) -> JSONResponse:
    """Edit a cupping session."""
    try:
        store = _get_store()
        changes = await request.json()

        # Check if roast exists
        if roast_uuid not in _ROAST_INDEX:
            raise HTTPException(status_code=404, detail="Roast not found in logs")

        updated_record = store.edit_cupping(roast_uuid, cupping_index, changes)
        return JSONResponse(content=updated_record)
    except SensoryStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/roasts/{roast_uuid}/cupping/{cupping_index}")
async def remove_cupping(roast_uuid: str, cupping_index: int) -> JSONResponse:
    """Remove a cupping session."""
    try:
        store = _get_store()

        # Check if roast exists
        if roast_uuid not in _ROAST_INDEX:
            raise HTTPException(status_code=404, detail="Roast not found in logs")

        updated_record = store.remove_cupping(roast_uuid, cupping_index)
        return JSONResponse(content=updated_record)
    except SensoryStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/roasts/{roast_uuid}/radar")
async def update_radar(
    roast_uuid: str,
    request: Request,
) -> JSONResponse:
    """Update the flavor radar for a roast."""
    try:
        store = _get_store()
        body = await request.json()
        values = body.get("values")
        labels = body.get("labels")

        # Check if roast exists
        if roast_uuid not in _ROAST_INDEX:
            raise HTTPException(status_code=404, detail="Roast not found in logs")

        # Ensure we have a record
        record = store.get(roast_uuid)
        if record is None:
            index_data = _ROAST_INDEX[roast_uuid]
            roast_ref = {
                "file": index_data.get("source_file"),
                "date": index_data.get("roast_isodate"),
            }
            store.create(roast_uuid, roast_ref)

        updated_record = store.update_radar(roast_uuid, values, labels)
        return JSONResponse(content=updated_record)
    except SensoryStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/radar_labels")
async def get_radar_labels() -> JSONResponse:
    """Get the default radar labels."""
    return JSONResponse(content={"labels": list(DEFAULT_RADAR_LABELS)})


@app.get("/api/score_keys")
async def get_score_keys() -> JSONResponse:
    """Get the SCA score keys."""
    return JSONResponse(content={"keys": list(SCORE_KEYS)})


@app.get("/api/defect_keys")
async def get_defect_keys() -> JSONResponse:
    """Get the defect keys."""
    return JSONResponse(content={"keys": list(DEFECT_KEYS)})


# -----------------------------------------------------------
# Frontend - Single page app
# -----------------------------------------------------------

@app.get("/")
async def read_root() -> HTMLResponse:
    """Serve the single-page application."""
    frontend_path = Path(__file__).parent / "frontend.html"
    if frontend_path.exists():
        content = frontend_path.read_text(encoding="utf-8")
    else:
        content = "<html><body><h1>Frontend not found</h1></body></html>"
    return HTMLResponse(content=content)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> JSONResponse:
    """Return a simple favicon."""
    return JSONResponse(content={"error": "No favicon"}, status_code=404)


# -----------------------------------------------------------
# Entry point
# -----------------------------------------------------------

def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
