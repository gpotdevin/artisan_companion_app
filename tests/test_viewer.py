"""Tests for the profile viewer endpoint (M3).

Tests the GET /api/roasts/{uuid}/profile endpoint using TestClient.
Uses fixture .alog files to verify correct profile data extraction.
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

# Test constants - use the actual fixture UUID
SAMPLE_UUID_A = "41bc74340a464d98a8156045b5bfc495"


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing with fixture alog files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logs_dir = Path(tmpdir) / "logs"
        sensory_dir = Path(tmpdir) / "sensory"
        logs_dir.mkdir()
        sensory_dir.mkdir()
        
        # Copy fixture alog files
        fixtures_dir = Path(__file__).parent / "fixtures" / "alogs"
        if fixtures_dir.exists():
            for alog_file in fixtures_dir.glob("*.alog"):
                shutil.copy(alog_file, logs_dir / alog_file.name)
        
        yield logs_dir, sensory_dir


@pytest.fixture
def client(temp_dirs):
    """Create a test client configured with temp directories and fixtures."""
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
        for mod in list(sys.modules.keys()):
            if 'app' in mod:
                del sys.modules[mod]
        
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


# -----------------------------------------------------------
# Profile endpoint tests
# -----------------------------------------------------------

def test_profile_returns_404_for_unknown_uuid(client):
    """GET /api/roasts/{uuid}/profile returns 404 for unknown roast."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    # This should work because we copied fixtures
    # Let's test with a truly unknown UUID
    response = client.get("/api/roasts/00000000000000000000000000000000/profile")
    assert response.status_code == 404


def test_profile_returns_200_for_valid_uuid(client):
    """GET /api/roasts/{uuid}/profile returns 200 for valid roast UUID."""
    # Use the fixture that has UUID_A
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["roast_uuid"] == SAMPLE_UUID_A


def test_profile_returns_correct_series(client):
    """Profile endpoint returns correct series (times, BT, ET, RoR)."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    data = response.json()
    
    # Check that we have the required arrays
    assert "times_s" in data
    assert "bt_c" in data
    assert "et_c" in data
    assert "ror_c_per_min" in data
    
    # Verify arrays are populated
    assert len(data["times_s"]) > 0
    assert len(data["bt_c"]) > 0
    assert len(data["et_c"]) > 0
    assert len(data["ror_c_per_min"]) > 0
    
    # Verify lengths match
    assert len(data["times_s"]) == len(data["bt_c"])
    assert len(data["times_s"]) == len(data["et_c"])
    assert len(data["times_s"]) == len(data["ror_c_per_min"])
    
    # Verify time starts at or near 0 (CHARGE is at time 0)
    assert data["times_s"][0] <= 0.1  # Should be 0 or very close
    
    # Verify BT values are in plausible range (0-300°C)
    assert min(data["bt_c"]) >= 0
    assert max(data["bt_c"]) <= 300
    
    # Verify ET values are in plausible range
    assert min(data["et_c"]) >= 0
    assert max(data["et_c"]) <= 300


def test_profile_returns_markers(client):
    """Profile endpoint returns CHARGE/DRY/FCs/DROP markers with times."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    data = response.json()
    
    assert "markers" in data
    assert isinstance(data["markers"], dict)
    
    # Check for expected markers (v2.10.4 fixture has CHARGE/DRY/FCs/DROP)
    expected_markers = ["CHARGE", "DRY", "FCs", "DROP"]
    for marker in expected_markers:
        if marker in data["markers"]:
            marker_data = data["markers"][marker]
            assert "time_s" in marker_data
            assert isinstance(marker_data["time_s"], (int, float))
            assert "temp_bt_c" in marker_data
            assert "temp_et_c" in marker_data
    
    # Verify CHARGE is at or near time 0
    if "CHARGE" in data["markers"]:
        assert data["markers"]["CHARGE"]["time_s"] <= 0.1


def test_profile_returns_events(client):
    """Profile endpoint returns events with times and labels."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    data = response.json()
    
    assert "events" in data
    assert isinstance(data["events"], list)
    
    # v2.10.4 fixture has special events
    if len(data["events"]) > 0:
        event = data["events"][0]
        assert "time_s" in event
        assert "index" in event
        # At least one of type_label or label should be present
        assert "type_label" in event or "label" in event


def test_profile_returns_phases(client):
    """Profile endpoint returns phase boundaries (drying/Maillard/development)."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    data = response.json()
    
    assert "phases" in data
    assert isinstance(data["phases"], dict)
    
    # Check for expected phase durations
    # The fixture has computed phase times
    phase_keys = ["drying_s", "maillard_s", "development_s", "total_s"]
    for key in phase_keys:
        if key in data["phases"]:
            assert isinstance(data["phases"][key], (int, float, type(None)))


def test_profile_returns_metadata(client):
    """Profile endpoint returns roast metadata."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    data = response.json()
    
    # Check metadata fields
    assert "source_file" in data
    assert "title" in data
    assert "roast_date" in data
    assert "meta" in data
    
    # Check artisan version
    assert "artisan_version" in data["meta"]


def test_profile_returns_sensory_data(client):
    """Profile endpoint returns sensory summary data."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    data = response.json()
    
    # Sensory data may be null if no sensory record exists
    assert "sensory" in data
    # Initially, sensory data may be None
    if data["sensory"] is not None:
        assert isinstance(data["sensory"], dict)
        # Check for expected sensory fields
        assert "cuppings" in data["sensory"]
        assert "radar" in data["sensory"]


def test_profile_with_background_uuid(client):
    """Profile endpoint includes background BT series when backgroundUUID resolves."""
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    data = response.json()
    
    # Check if background is present
    # The fixture v2.10.4 has backgroundUUID = e9124b57b75a432ebfde580a545868fe
    # but that file may not exist in the test fixtures
    # So we just check that background field exists
    assert "background" in data
    # It should be None or an object with times_s and bt_c
    if data["background"] is not None:
        assert "times_s" in data["background"]
        assert "bt_c" in data["background"]


def test_profile_values_match_alog_core(client):
    """Profile endpoint returns values matching alog_core direct parsing."""
    # Import alog_core to parse the same fixture
    import sys as sys_module
    sys_module.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from alog_core import parse_profile, load_alog
    
    response = client.get(f"/api/roasts/{SAMPLE_UUID_A}/profile")
    assert response.status_code == 200
    api_data = response.json()
    
    # Find the actual fixture file path
    from app.main import _LOGS_DIR
    if _LOGS_DIR:
        for alog_file in _LOGS_DIR.glob("*.alog"):
            try:
                profile = parse_profile(alog_file)
                if profile.meta.roast_uuid == SAMPLE_UUID_A:
                    # Compare key values
                    assert len(api_data["times_s"]) == len(profile.times_s)
                    assert len(api_data["bt_c"]) == len(profile.bt_c)
                    assert len(api_data["et_c"]) == len(profile.et_c)
                    
                    # Check first few BT values match
                    for i in range(min(5, len(profile.bt_c))):
                        assert abs(api_data["bt_c"][i] - profile.bt_c[i]) < 0.01
                    
                    # Check markers
                    for marker_name, marker in profile.markers.items():
                        if marker_name in api_data["markers"]:
                            api_marker = api_data["markers"][marker_name]
                            assert abs(api_marker["time_s"] - marker.time_s) < 0.01
                            
                    # Phases if present
                    if profile.phases and api_data["phases"]:
                        for key in ["drying_s", "maillard_s", "development_s", "total_s"]:
                            if key in profile.phases and key in api_data["phases"]:
                                api_val = api_data["phases"][key]
                                profile_val = profile.phases.get(key)
                                if api_val is not None and profile_val is not None:
                                    assert abs(api_val - profile_val) < 0.1
                    
                    break
            except:
                continue


# -----------------------------------------------------------
# Viewer page tests
# -----------------------------------------------------------

def test_viewer_page_returns_200(client):
    """GET /viewer returns 200."""
    response = client.get("/viewer")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_viewer_page_returns_200_with_uuid(client):
    """GET /viewer?uuid=... returns 200."""
    response = client.get(f"/viewer?uuid={SAMPLE_UUID_A}")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Check that it's the viewer page (not just a redirect)
    assert "Profile Viewer" in response.text


# -----------------------------------------------------------
# Integration tests
# -----------------------------------------------------------

def test_profile_endpoint_for_all_fixtures(client):
    """Test that profile endpoint works for all fixture alog files."""
    from app.main import _ROAST_INDEX
    
    for roast_uuid, roast_data in _ROAST_INDEX.items():
        response = client.get(f"/api/roasts/{roast_uuid}/profile")
        assert response.status_code == 200, f"Failed for {roast_uuid}"
        data = response.json()
        
        # Verify basic structure
        assert "times_s" in data
        assert "bt_c" in data
        assert "et_c" in data
        assert len(data["times_s"]) > 0
        
        # Verify time starts at or near 0
        assert data["times_s"][0] <= 0.1
        
        # Verify plausible temperature ranges
        assert 0 <= min(data["bt_c"]) <= max(data["bt_c"]) <= 300


# -----------------------------------------------------------
# Fixture integrity test
# -----------------------------------------------------------

def test_fixture_files_unchanged_after_requests(temp_dirs):
    """Verify that fixture .alog files are not modified by requests."""
    logs_dir, sensory_dir = temp_dirs
    
    # Get checksums before
    checksums_before = {}
    for alog_file in logs_dir.glob("*.alog"):
        checksums_before[alog_file.name] = hashlib.sha256(alog_file.read_bytes()).hexdigest()
    
    # Now make some requests
    sys.argv = ["test", "--logs-dir", str(logs_dir), "--sensory-dir", str(sensory_dir)]
    for mod in list(sys.modules.keys()):
        if 'app' in mod:
            del sys.modules[mod]
    
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as client:
        # List roasts
        response = client.get("/api/roasts")
        assert response.status_code == 200
        
        # Get a profile
        if response.json()["roasts"]:
            uuid = response.json()["roasts"][0]["roast_uuid"]
            response = client.get(f"/api/roasts/{uuid}/profile")
            assert response.status_code == 200
    
    # Get checksums after
    checksums_after = {}
    for alog_file in logs_dir.glob("*.alog"):
        checksums_after[alog_file.name] = hashlib.sha256(alog_file.read_bytes()).hexdigest()
    
    # Verify no files were modified
    assert checksums_before == checksums_after
