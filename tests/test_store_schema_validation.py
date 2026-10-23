"""Tests for schema validation fixes (FIX 1-4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from store import SensoryStore, SensoryStoreError
from store.schema import (
    SCHEMA_VERSION,
    normalize_cupping,
    normalize_native_sync,
    normalize_radar,
    normalize_record,
)

UUID_A = "41bc74340a464d98a8156045b5bfc495"
ROAST_REF = {"file": "test.alog", "date": "2024-08-03"}


# ---------------------------------------------------------------------------
# FIX 1: schema_version validation rejects non-int and bool
# ---------------------------------------------------------------------------

def test_schema_version_true_rejected():
    """FIX 1: schema_version: true should be rejected (True == 1 in Python)."""
    raw = {"schema_version": True, "roast_uuid": UUID_A}
    with pytest.raises(SensoryStoreError, match="schema_version"):
        normalize_record(raw)


def test_schema_version_false_rejected():
    """FIX 1: schema_version: false should be rejected."""
    raw = {"schema_version": False, "roast_uuid": UUID_A}
    with pytest.raises(SensoryStoreError, match="schema_version"):
        normalize_record(raw)


def test_schema_version_string_rejected():
    """FIX 1: schema_version as string should be rejected."""
    raw = {"schema_version": "1", "roast_uuid": UUID_A}
    with pytest.raises(SensoryStoreError, match="schema_version"):
        normalize_record(raw)


def test_schema_version_float_rejected():
    """FIX 1: schema_version as float should be rejected."""
    raw = {"schema_version": 1.0, "roast_uuid": UUID_A}
    with pytest.raises(SensoryStoreError, match="schema_version"):
        normalize_record(raw)


def test_schema_version_valid_int_accepted():
    """FIX 1: schema_version as valid int should be accepted."""
    raw = {"schema_version": SCHEMA_VERSION, "roast_uuid": UUID_A}
    result = normalize_record(raw)
    assert result["schema_version"] == SCHEMA_VERSION


def test_schema_version_missing_defaults_to_current():
    """FIX 1: missing schema_version defaults to current version."""
    raw = {"roast_uuid": UUID_A}
    result = normalize_record(raw)
    assert result["schema_version"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# FIX 2: _as_list helper prevents string explosion
# ---------------------------------------------------------------------------

def test_normalize_radar_labels_string_rejected():
    """FIX 2: radar labels as string should be rejected, not exploded."""
    raw = {"labels": "apricot", "values": []}
    with pytest.raises(SensoryStoreError, match="expected a list"):
        normalize_radar(raw)


def test_normalize_radar_values_string_rejected():
    """FIX 2: radar values as string should be rejected, not exploded."""
    raw = {"labels": [], "values": "apricot"}
    with pytest.raises(SensoryStoreError, match="expected a list"):
        normalize_radar(raw)


def test_normalize_native_sync_fields_string_rejected():
    """FIX 2: native_sync fields as string should be rejected, not exploded."""
    raw = {"fields": "radar", "last_synced": None}
    with pytest.raises(SensoryStoreError, match="expected a list"):
        normalize_native_sync(raw)


def test_normalize_cupping_descriptors_string_rejected():
    """FIX 2: cupping descriptors as string should be rejected, not exploded."""
    raw = {"date": "2024-08-05", "descriptors": "apricot", "scores": {}}
    with pytest.raises(SensoryStoreError, match="expected a list"):
        normalize_cupping(raw)


def test_normalize_radar_labels_list_accepted():
    """FIX 2: radar labels as list should be accepted."""
    raw = {"labels": ["A", "B"], "values": [1.0, 2.0]}
    result = normalize_radar(raw)
    assert result["labels"] == ["A", "B"]


def test_normalize_radar_labels_none_defaults_to_empty():
    """FIX 2: radar labels as None should default to empty list."""
    raw = {"labels": None, "values": None}
    result = normalize_radar(raw)
    assert result["labels"] == []
    assert result["values"] == []


def test_normalize_cupping_descriptors_list_accepted():
    """FIX 2: cupping descriptors as list should be accepted."""
    raw = {"date": "2024-08-05", "descriptors": ["apricot", "floral"], "scores": {}}
    result = normalize_cupping(raw)
    assert result["descriptors"] == ["apricot", "floral"]


def test_normalize_cupping_descriptors_none_defaults_to_empty():
    """FIX 2: cupping descriptors as None should default to empty list."""
    raw = {"date": "2024-08-05", "descriptors": None, "scores": {}}
    result = normalize_cupping(raw)
    assert result["descriptors"] == []


# ---------------------------------------------------------------------------
# FIX 3: radar values validated to 0-10 range
# ---------------------------------------------------------------------------

def test_normalize_radar_values_above_10_rejected():
    """FIX 3: radar values above 10 should be rejected."""
    raw = {"labels": [], "values": [11.0]}
    with pytest.raises(SensoryStoreError, match="radar.values.*expected a number in 0-10"):
        normalize_radar(raw)


def test_normalize_radar_values_below_0_rejected():
    """FIX 3: radar values below 0 should be rejected."""
    raw = {"labels": [], "values": [-5.0]}
    with pytest.raises(SensoryStoreError, match="radar.values.*expected a number in 0-10"):
        normalize_radar(raw)


def test_normalize_radar_values_at_boundaries_accepted():
    """FIX 3: radar values at 0 and 10 should be accepted."""
    raw = {"labels": [], "values": [0.0, 10.0]}
    result = normalize_radar(raw)
    assert result["values"] == [0.0, 10.0]


def test_normalize_radar_values_in_range_accepted():
    """FIX 3: radar values in 0-10 range should be accepted."""
    raw = {"labels": [], "values": [5.5, 8.0, 3.2]}
    result = normalize_radar(raw)
    assert result["values"] == [5.5, 8.0, 3.2]


def test_normalize_radar_non_numeric_dropped():
    """FIX 3: non-numeric radar values should be dropped silently."""
    raw = {"labels": [], "values": [5.0, "not a number", 8.0]}
    result = normalize_radar(raw)
    assert result["values"] == [5.0, 8.0]


# ---------------------------------------------------------------------------
# FIX 4: cupping total floored at 0
# ---------------------------------------------------------------------------

def test_cupping_only_defects_yields_total_zero():
    """FIX 4: cupping with only defects penalty yields total >= 0."""
    raw = {"date": "2024-08-05", "scores": {"defects": 2.0}}
    result = normalize_cupping(raw)
    assert result["scores"]["total"] == 0.0


def test_cupping_defects_exceeding_attrs_yields_total_zero():
    """FIX 4: cupping with defects > attrs yields total >= 0."""
    raw = {
        "date": "2024-08-05",
        "scores": {"flavor": 5.0, "defects": 10.0}
    }
    result = normalize_cupping(raw)
    assert result["scores"]["total"] == 0.0


def test_cupping_normal_total_computed_correctly():
    """FIX 4: cupping with valid scores computes total correctly."""
    raw = {
        "date": "2024-08-05",
        "scores": {"flavor": 8.0, "acidity": 7.0, "defects": 1.0}
    }
    result = normalize_cupping(raw)
    assert result["scores"]["total"] == 14.0


def test_cupping_no_scores_no_total():
    """FIX 4: cupping with no scores has no total."""
    raw = {"date": "2024-08-05", "scores": {}}
    result = normalize_cupping(raw)
    assert "total" not in result["scores"]


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------

def test_full_record_normalization_happy_path():
    """Happy path: valid full record normalizes correctly."""
    raw = {
        "schema_version": SCHEMA_VERSION,
        "roast_uuid": UUID_A,
        "roast_ref": ROAST_REF,
        "radar": {"labels": ["A", "B"], "values": [5.0, 8.0]},
        "cuppings": [
            {
                "date": "2024-08-05",
                "descriptors": ["apricot", "floral"],
                "scores": {
                    "flavor": 8.0,
                    "acidity": 7.0,
                    "defects": 0.5,
                },
                "notes": "Test",
            }
        ],
        "native_sync": {"fields": ["radar"], "last_synced": None},
        "media": [],
    }
    result = normalize_record(raw)
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["roast_uuid"] == UUID_A
    assert result["radar"]["labels"] == ["A", "B"]
    assert result["radar"]["values"] == [5.0, 8.0]
    assert len(result["cuppings"]) == 1
    assert result["cuppings"][0]["descriptors"] == ["apricot", "floral"]
    assert result["cuppings"][0]["scores"]["total"] == pytest.approx(14.5)
    assert result["native_sync"]["fields"] == ["radar"]


def test_store_integration_schema_version_true_rejected(tmp_path: Path):
    """Integration test: schema_version true rejected via store."""
    store = SensoryStore(tmp_path / "sensory")
    sidecar = tmp_path / "sensory" / f"{UUID_A}.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(
        json.dumps({"schema_version": True, "roast_uuid": UUID_A}),
        encoding="utf-8"
    )
    with pytest.raises(SensoryStoreError, match="schema_version"):
        store.get(UUID_A)
    store.close()


def test_store_integration_string_descriptors_rejected(tmp_path: Path):
    """Integration test: string descriptors rejected via store."""
    store = SensoryStore(tmp_path / "sensory")
    store.create(UUID_A, ROAST_REF)
    with pytest.raises(SensoryStoreError, match="expected a list"):
        store.add_cupping(UUID_A, {
            "date": "2024-08-05",
            "descriptors": "apricot",
            "scores": {},
        })
    store.close()


def test_store_integration_radar_out_of_range_rejected(tmp_path: Path):
    """Integration test: radar values out of range rejected via store."""
    store = SensoryStore(tmp_path / "sensory")
    store.create(UUID_A, ROAST_REF)
    with pytest.raises(SensoryStoreError, match="radar.values.*expected a number in 0-10"):
        store.update_radar(UUID_A, [11.0, 5.0])
    store.close()


def test_store_integration_cupping_total_floored(tmp_path: Path):
    """Integration test: cupping total floored at 0 via store."""
    store = SensoryStore(tmp_path / "sensory")
    store.create(UUID_A, ROAST_REF)
    record = store.add_cupping(UUID_A, {
        "date": "2024-08-05",
        "scores": {"defects": 5.0},
    })
    assert record["cuppings"][0]["scores"]["total"] == 0.0
    store.close()
