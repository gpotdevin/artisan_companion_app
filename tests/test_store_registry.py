"""Tests for roast registry and search validation (M2b review findings M-2, L-5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from store import SensoryStore, SensoryStoreError

UUID_A = "41bc74340a464d98a8156045b5bfc495"
UUID_B = "0123456789abcdef0123456789abcdef"

# Full scores that sum to 84.0 (10 attribute scores minus defects)
FULL_SCORES = {
    "fragrance_aroma": 8.0, "flavor": 8.5, "aftertaste": 7.5,
    "acidity": 8.5, "body": 7.0, "balance": 8.0,
    "uniformity": 10.0, "clean_cup": 10.0, "sweetness": 8.0,
    "overall": 8.5, "defects": 0,
}


@pytest.fixture
def store(tmp_path: Path) -> SensoryStore:
    s = SensoryStore(tmp_path / "sensory")
    yield s
    s.close()


# ---------------------------------------------------------------------------
# FIX 1: register_roast with values then bare register_roast preserves values
# ---------------------------------------------------------------------------

def test_register_roast_preserves_values_on_bare_reregister(store: SensoryStore):
    """A bare register_roast(uuid) for an already-registered roast must be a no-op."""
    # Register with file and date
    store.register_roast(UUID_A, source_file="test.alog", roast_date="2024-01-01")
    
    # Verify the registration
    roasts = store.list_roasts()
    assert len(roasts) == 1
    assert roasts[0]["roast_uuid"] == UUID_A
    assert roasts[0]["source_file"] == "test.alog"
    assert roasts[0]["roast_date"] == "2024-01-01"
    
    # Bare register_roast should preserve existing values
    store.register_roast(UUID_A)
    
    # Verify values are still there
    roasts = store.list_roasts()
    assert len(roasts) == 1
    assert roasts[0]["roast_uuid"] == UUID_A
    assert roasts[0]["source_file"] == "test.alog"
    assert roasts[0]["roast_date"] == "2024-01-01"


def test_register_roast_updates_with_new_values(store: SensoryStore):
    """register_roast with new values should update the existing registration."""
    # Register with initial values
    store.register_roast(UUID_A, source_file="test.alog", roast_date="2024-01-01")
    
    # Update with new values
    store.register_roast(UUID_A, source_file="updated.alog", roast_date="2024-02-01")
    
    # Verify updated values
    roasts = store.list_roasts()
    assert len(roasts) == 1
    assert roasts[0]["source_file"] == "updated.alog"
    assert roasts[0]["roast_date"] == "2024-02-01"


def test_register_roast_partial_update_preserves_other_fields(store: SensoryStore):
    """register_roast with only one field should preserve the other."""
    # Register with both values
    store.register_roast(UUID_A, source_file="test.alog", roast_date="2024-01-01")
    
    # Update only the file
    store.register_roast(UUID_A, source_file="new.alog")
    
    # Verify date is preserved
    roasts = store.list_roasts()
    assert len(roasts) == 1
    assert roasts[0]["source_file"] == "new.alog"
    assert roasts[0]["roast_date"] == "2024-01-01"
    
    # Update only the date
    store.register_roast(UUID_A, roast_date="2024-02-01")
    
    # Verify file is preserved
    roasts = store.list_roasts()
    assert len(roasts) == 1
    assert roasts[0]["source_file"] == "new.alog"
    assert roasts[0]["roast_date"] == "2024-02-01"


# ---------------------------------------------------------------------------
# FIX 2: search min_score/max_score type validation
# ---------------------------------------------------------------------------

def test_search_invalid_min_score_raises(store: SensoryStore):
    """search with min_score as a string should raise SensoryStoreError."""
    with pytest.raises(SensoryStoreError, match="min_score: expected a number"):
        store.search(min_score="abc")


def test_search_invalid_max_score_raises(store: SensoryStore):
    """search with max_score as a string should raise SensoryStoreError."""
    with pytest.raises(SensoryStoreError, match="max_score: expected a number"):
        store.search(max_score="xyz")


def test_search_invalid_min_score_type_raises(store: SensoryStore):
    """search with min_score as a non-numeric type should raise SensoryStoreError."""
    with pytest.raises(SensoryStoreError, match="min_score: expected a number"):
        store.search(min_score=[1, 2, 3])


def test_search_invalid_max_score_type_raises(store: SensoryStore):
    """search with max_score as a non-numeric type should raise SensoryStoreError."""
    with pytest.raises(SensoryStoreError, match="max_score: expected a number"):
        store.search(max_score={"value": 5})


def test_search_valid_min_score_filters_correctly(store: SensoryStore):
    """search with valid min_score should filter correctly."""
    # Create record A with a cupping that has total = 84.0
    store.create(UUID_A)
    store.add_cupping(UUID_A, {
        "date": "2024-01-01",
        "scores": FULL_SCORES,
        "descriptors": ["test"],
    })
    
    # Search with min_score should return records with best_total >= min_score
    results = store.search(min_score=80.0)
    assert len(results) == 1
    assert results[0]["roast_uuid"] == UUID_A
    
    # Search with higher min_score should return no results
    results = store.search(min_score=90.0)
    assert len(results) == 0


def test_search_valid_max_score_filters_correctly(store: SensoryStore):
    """search with valid max_score should filter correctly."""
    # Create record A with a cupping that has total = 84.0
    store.create(UUID_A)
    store.add_cupping(UUID_A, {
        "date": "2024-01-01",
        "scores": FULL_SCORES,
        "descriptors": ["test"],
    })
    
    # Search with max_score should return records with best_total <= max_score
    results = store.search(max_score=90.0)
    assert len(results) == 1
    assert results[0]["roast_uuid"] == UUID_A
    
    # Search with lower max_score should return no results
    results = store.search(max_score=80.0)
    assert len(results) == 0


def test_search_valid_min_max_score_filters_correctly(store: SensoryStore):
    """search with both min_score and max_score should filter correctly."""
    # Create record A with a cupping that has total = 84.0
    store.create(UUID_A)
    store.add_cupping(UUID_A, {
        "date": "2024-01-01",
        "scores": FULL_SCORES,
        "descriptors": ["test"],
    })
    
    # Search with both bounds should return records in range
    results = store.search(min_score=80.0, max_score=90.0)
    assert len(results) == 1
    assert results[0]["roast_uuid"] == UUID_A
    
    # Search with bounds that exclude the record
    results = store.search(min_score=85.0, max_score=90.0)
    assert len(results) == 0


def test_search_integer_scores_work(store: SensoryStore):
    """search with integer min_score/max_score should work (converted to float)."""
    # Create record A with a cupping that has total = 84.0
    store.create(UUID_A)
    store.add_cupping(UUID_A, {
        "date": "2024-01-01",
        "scores": FULL_SCORES,
        "descriptors": ["test"],
    })
    
    # Search with integer min_score should work
    results = store.search(min_score=80)
    assert len(results) == 1
    assert results[0]["roast_uuid"] == UUID_A
