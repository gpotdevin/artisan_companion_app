"""Tests for the sensory editor web app (M2b).

Tests the FastAPI backend endpoints using TestClient.
Uses tmp dirs and synthetic roastUUIDs; does not depend on the real corpus.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

# Test constants
SAMPLE_UUID_A = "41bc74340a464d98a8156045b5bfc495"
SAMPLE_UUID_B = "0123456789abcdef0123456789abcdef"

FULL_SCORES = {
    "fragrance_aroma": 8.0, "flavor": 8.5, "aftertaste": 7.5,
    "acidity": 8.5, "body": 7.0, "balance": 8.0,
    "uniformity": 10.0, "clean_cup": 10.0, "sweetness": 8.0,
    "overall": 8.5, "defects": 0,
}
# sum of the ten attributes minus the penalty
EXPECTED_TOTAL = 84.0


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logs_dir = Path(tmpdir) / "logs"
        sensory_dir = Path(tmpdir) / "sensory"
        logs_dir.mkdir()
        sensory_dir.mkdir()
        
        # Create a minimal .alog file
        alog_path = logs_dir / "test.alog"
        alog_data = {
            "version": "2.10.4",
            "roastUUID": SAMPLE_UUID_A,
            "title": "Test Roast A",
            "beans": "Test Beans",
            "roastdate": "2024-01-01",
            "roast_isodate": "2024-01-01",
            "timex": [0, 10, 20, 30],
            "temp2": [20, 100, 180, 200],
            "timeindex": [0, 0, 0, 0, 0, 0, 0, 0],
        }
        alog_path.write_text(repr(alog_data))
        
        yield logs_dir, sensory_dir


@pytest.fixture
def client(temp_dirs):
    """Create a test client configured with temp directories."""
    logs_dir, sensory_dir = temp_dirs
    
    # Save original state
    orig_argv = sys.argv[:]
    orig_modules = sys.modules.copy()
    
    try:
        # Configure sys.argv
        sys.argv = [
            "test",
            "--logs-dir", str(logs_dir),
            "--sensory-dir", str(sensory_dir)
        ]
        
        # Reload the app module to pick up new config
        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "app" in sys.modules:
            del sys.modules["app"]
        
        # Import fresh
        from app.main import app
        
        # Create test client
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
            
            # Clean up store
            from app.main import _SENSORY_STORE
            if _SENSORY_STORE is not None:
                try:
                    _SENSORY_STORE.close()
                except:
                    pass
    
    finally:
        # Restore sys.argv
        sys.argv = orig_argv


# ---------------------------------------------------------------------------
# Roast listing
# ---------------------------------------------------------------------------

def test_list_roasts(client):
    """GET /api/roasts returns the roast list."""
    response = client.get("/api/roasts")
    assert response.status_code == 200
    data = response.json()
    assert "roasts" in data
    assert isinstance(data["roasts"], list)
    # Should have at least our test roast
    uuid_set = {r["roast_uuid"] for r in data["roasts"]}
    assert SAMPLE_UUID_A in uuid_set


def test_list_roasts_annotated_status(client):
    """Roasts in the list show annotation status."""
    # Create a new roast that won't be in the list initially
    # First, check the roast exists in the list
    response = client.get("/api/roasts")
    assert response.status_code == 200
    data = response.json()
    roast_data = next((r for r in data["roasts"] if r["roast_uuid"] == SAMPLE_UUID_A), None)
    assert roast_data is not None
    assert "annotated" in roast_data
    # Just check that annotated field exists and is boolean
    assert isinstance(roast_data["annotated"], bool)


# ---------------------------------------------------------------------------
# Record CRUD
# ---------------------------------------------------------------------------

def test_get_nonexistent_record_returns_404(client):
    """GET /api/roasts/{uuid} returns 404 for unknown roast."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_B}")
    assert response.status_code == 404


def test_create_record(client):
    """POST /api/roasts/{uuid} creates a new sensory record."""
    response = client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 201
    record = response.json()
    assert record["roast_uuid"] == SAMPLE_UUID_A
    assert record["schema_version"] == 1
    assert record["cuppings"] == []
    assert "radar" in record
    assert "defects_observed" in record


def test_get_record_after_create(client):
    """GET /api/roasts/{uuid} returns the created record."""
    # Create first
    client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    
    # Then get
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 200
    record = response.json()
    assert record["roast_uuid"] == SAMPLE_UUID_A


def test_create_duplicate_returns_409(client):
    """POST /api/roasts/{uuid} returns 409 if record exists."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    response = client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 409


def test_update_record(client):
    """PUT /api/roasts/{uuid} updates top-level sections."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    
    response = client.put(
        f"/api/roasts/{SAMPLE_UUID_A}",
        json={"defects_observed": {"tipping": True, "scorching": False}}
    )
    assert response.status_code == 200
    record = response.json()
    assert record["defects_observed"]["tipping"] is True
    assert record["defects_observed"]["scorching"] is False


def test_delete_record(client):
    """DELETE /api/roasts/{uuid} removes the record."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    
    response = client.delete(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    
    # Verify it's gone
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 404


def test_delete_nonexistent_returns_404(client):
    """DELETE /api/roasts/{uuid} returns 404 if record doesn't exist."""
    response = client.delete(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Cupping sessions
# ---------------------------------------------------------------------------

def test_add_cupping(client):
    """POST /api/roasts/{uuid}/cupping adds a cupping session."""
    response = client.post(
        f"/api/roasts/{SAMPLE_UUID_A}/cupping",
        json={
            "date": "2024-01-05",
            "scores": FULL_SCORES,
            "descriptors": ["fruity", "floral"],
            "notes": "Test cupping notes",
        }
    )
    assert response.status_code == 201
    record = response.json()
    assert len(record["cuppings"]) == 1
    cupping = record["cuppings"][0]
    assert cupping["date"] == "2024-01-05"
    assert cupping["notes"] == "Test cupping notes"
    assert cupping["descriptors"] == ["fruity", "floral"]


def test_add_cupping_auto_creates_record(client):
    """Adding a cupping to a non-existent record auto-creates it."""
    response = client.post(
        f"/api/roasts/{SAMPLE_UUID_A}/cupping",
        json={
            "date": "2024-01-05",
            "scores": FULL_SCORES,
        }
    )
    assert response.status_code == 201
    record = response.json()
    assert record["roast_uuid"] == SAMPLE_UUID_A
    assert len(record["cuppings"]) == 1


def test_add_cupping_missing_date_returns_400(client):
    """Adding a cupping without a date returns 400."""
    response = client.post(
        f"/api/roasts/{SAMPLE_UUID_A}/cupping",
        json={"scores": FULL_SCORES}
    )
    assert response.status_code == 400


def test_edit_cupping(client):
    """PUT /api/roasts/{uuid}/cupping/{index} edits a cupping session."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}/cupping", json={
        "date": "2024-01-05",
        "scores": FULL_SCORES,
        "notes": "Original notes",
    })
    
    response = client.put(
        f"/api/roasts/{SAMPLE_UUID_A}/cupping/0",
        json={"notes": "Updated notes"}
    )
    assert response.status_code == 200
    record = response.json()
    assert record["cuppings"][0]["notes"] == "Updated notes"


def test_edit_nonexistent_cupping_returns_400(client):
    """PUT /api/roasts/{uuid}/cupping/{index} returns 400 for invalid index."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    response = client.put(
        f"/api/roasts/{SAMPLE_UUID_A}/cupping/99",
        json={"notes": "Updated"}
    )
    assert response.status_code == 400


def test_remove_cupping(client):
    """DELETE /api/roasts/{uuid}/cupping/{index} removes a cupping."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}/cupping", json={
        "date": "2024-01-05",
        "scores": FULL_SCORES,
    })
    client.post(f"/api/roasts/{SAMPLE_UUID_A}/cupping", json={
        "date": "2024-01-10",
        "scores": FULL_SCORES,
    })
    
    response = client.delete(f"/api/roasts/{SAMPLE_UUID_A}/cupping/0")
    assert response.status_code == 200
    record = response.json()
    assert len(record["cuppings"]) == 1


def test_remove_nonexistent_cupping_returns_400(client):
    """DELETE /api/roasts/{uuid}/cupping/{index} returns 400 for invalid index."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    response = client.delete(f"/api/roasts/{SAMPLE_UUID_A}/cupping/0")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Radar
# ---------------------------------------------------------------------------

def test_update_radar(client):
    """PUT /api/roasts/{uuid}/radar updates radar values."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    
    response = client.put(
        f"/api/roasts/{SAMPLE_UUID_A}/radar",
        json={
            "values": [8.0, 7.5, 9.0, 8.5, 7.0, 9.0, 8.0, 8.5, 7.5],
            "labels": ["Acidity", "Aftertaste", "Clean Cup", "Head", "Fragrance",
                       "Sweetness", "Aroma", "Balance", "Body"]
        }
    )
    assert response.status_code == 200
    record = response.json()
    assert len(record["radar"]["values"]) == 9
    assert record["radar"]["values"][0] == 8.0
    assert record["radar"]["values"][2] == 9.0


def test_update_radar_auto_creates_record(client):
    """Updating radar for a non-existent record auto-creates it."""
    response = client.put(
        f"/api/roasts/{SAMPLE_UUID_A}/radar",
        json={"values": [8.0, 7.5, 9.0, 8.5, 7.0, 9.0, 8.0, 8.5, 7.5]}
    )
    assert response.status_code == 200
    record = response.json()
    assert record["roast_uuid"] == SAMPLE_UUID_A


# ---------------------------------------------------------------------------
# Constants endpoints
# ---------------------------------------------------------------------------

def test_get_radar_labels(client):
    """GET /api/radar_labels returns the default radar labels."""
    response = client.get("/api/radar_labels")
    assert response.status_code == 200
    data = response.json()
    assert "labels" in data
    assert len(data["labels"]) == 9
    assert "Acidity" in data["labels"]


def test_get_score_keys(client):
    """GET /api/score_keys returns the SCA score keys."""
    response = client.get("/api/score_keys")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) == 10
    assert "fragrance_aroma" in data["keys"]
    assert "flavor" in data["keys"]


def test_get_defect_keys(client):
    """GET /api/defect_keys returns the defect keys."""
    response = client.get("/api/defect_keys")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) == 10
    assert "tipping" in data["keys"]
    assert "scorching" in data["keys"]


# ---------------------------------------------------------------------------
# Round-trip and integration tests
# ---------------------------------------------------------------------------

def test_cupping_round_trip(client):
    """Test create, read, verify cupping round-trip."""
    # Create record
    client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    
    # Add cupping with all fields
    original_cupping = {
        "date": "2024-10-23",
        "scores": FULL_SCORES,
        "descriptors": ["apricot", "stone fruit", "black tea", "floral"],
        "notes": "Very vibrant, expected acidity came through.",
    }
    response = client.post(
        f"/api/roasts/{SAMPLE_UUID_A}/cupping",
        json=original_cupping
    )
    assert response.status_code == 201
    
    # Get and verify
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 200
    record = response.json()
    
    assert len(record["cuppings"]) == 1
    cupping = record["cuppings"][0]
    assert cupping["date"] == "2024-10-23"
    assert cupping["notes"] == "Very vibrant, expected acidity came through."
    assert set(cupping["descriptors"]) == {"apricot", "stone fruit", "black tea", "floral"}
    
    # Verify all scores
    for key, expected_value in FULL_SCORES.items():
        assert cupping["scores"][key] == expected_value
    
    # Verify total is computed
    assert "total" in cupping["scores"]
    # Total should be sum of 10 attributes minus defects
    attrs_total = sum(FULL_SCORES[k] for k in FULL_SCORES if k != "defects")
    expected_total = round(attrs_total - FULL_SCORES["defects"], 2)
    assert cupping["scores"]["total"] == expected_total


def test_end_to_end_annotation_workflow(client):
    """Test complete annotation workflow: create, add cupping, update radar, verify."""
    # Create record
    response = client.post(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 201
    
    # Add cupping
    response = client.post(
        f"/api/roasts/{SAMPLE_UUID_A}/cupping",
        json={
            "date": "2024-10-23",
            "scores": {
                "fragrance_aroma": 8.5,
                "flavor": 9.0,
                "aftertaste": 8.0,
                "acidity": 8.5,
                "body": 7.5,
                "balance": 8.5,
                "uniformity": 10.0,
                "clean_cup": 10.0,
                "sweetness": 8.5,
                "overall": 9.0,
                "defects": 0,
            },
            "descriptors": ["bright", "juicy"],
            "notes": "Excellent batch",
        }
    )
    assert response.status_code == 201
    
    # Update radar
    response = client.put(
        f"/api/roasts/{SAMPLE_UUID_A}/radar",
        json={
            "values": [8.5, 8.0, 10.0, 7.5, 9.0, 8.5, 9.0, 8.5, 7.5]
        }
    )
    assert response.status_code == 200
    
    # Update defects
    response = client.put(
        f"/api/roasts/{SAMPLE_UUID_A}",
        json={
            "defects_observed": {
                "tipping": False,
                "scorching": False,
                "uneven": True,
            }
        }
    )
    assert response.status_code == 200
    
    # Verify final state
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}")
    assert response.status_code == 200
    record = response.json()
    
    # Verify all data is present
    assert len(record["cuppings"]) == 1
    assert len(record["radar"]["values"]) == 9
    assert record["defects_observed"]["uneven"] is True
    assert record["defects_observed"]["tipping"] is False
    
    # Verify annotation status is updated in list
    response = client.get("/api/roasts")
    data = response.json()
    roast_data = next((r for r in data["roasts"] if r["roast_uuid"] == SAMPLE_UUID_A), None)
    assert roast_data is not None
    assert roast_data["annotated"] is True
    assert roast_data["n_cuppings"] == 1


def test_multiple_cuppings(client):
    """Test adding multiple cupping sessions."""
    # Add multiple cuppings
    for i in range(3):
        response = client.post(
            f"/api/roasts/{SAMPLE_UUID_A}/cupping",
            json={
                "date": f"2024-10-{23 + i}",
                "scores": {**FULL_SCORES, "overall": 8.0 + i},
                "notes": f"Cupping session {i + 1}",
            }
        )
        assert response.status_code == 201
    
    # Verify all are present
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}")
    record = response.json()
    assert len(record["cuppings"]) == 3
    
    # Delete middle one
    response = client.delete(f"/api/roasts/{SAMPLE_UUID_A}/cupping/1")
    assert response.status_code == 200
    
    # Verify only 2 remain
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}")
    record = response.json()
    assert len(record["cuppings"]) == 2
    assert record["cuppings"][0]["notes"] == "Cupping session 1"
    assert record["cuppings"][1]["notes"] == "Cupping session 3"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_partial_score_update(client):
    """Test updating only some scores in a cupping."""
    client.post(f"/api/roasts/{SAMPLE_UUID_A}/cupping", json={
        "date": "2024-01-05",
        "scores": FULL_SCORES,
    })
    
    # Update only one score
    response = client.put(
        f"/api/roasts/{SAMPLE_UUID_A}/cupping/0",
        json={"scores": {"flavor": 9.5}}
    )
    assert response.status_code == 200
    record = response.json()
    assert record["cuppings"][0]["scores"]["flavor"] == 9.5
    # Others should remain unchanged
    assert record["cuppings"][0]["scores"]["fragrance_aroma"] == 8.0
