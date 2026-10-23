"""Tests for src/sync/integrity.py: hash computation and int-to-float conversion."""

import json

import pytest

from src.sync.integrity import (
    PROFILE_DATA_KEYS,
    compute_profile_hash,
    rec_int_to_float,
    verify_profile_hash,
)


class TestRecIntToFloat:
    """Test rec_int_to_float conversion."""

    def test_bool_to_float(self):
        assert rec_int_to_float(True) == 1.0
        assert rec_int_to_float(False) == 0.0

    def test_int_to_float(self):
        assert rec_int_to_float(1) == 1.0
        assert rec_int_to_float(0) == 0.0
        assert rec_int_to_float(-5) == -5.0

    def test_float_passthrough(self):
        assert rec_int_to_float(1.5) == 1.5
        assert rec_int_to_float(0.0) == 0.0

    def test_str_passthrough(self):
        assert rec_int_to_float("hello") == "hello"

    def test_list_recursive(self):
        assert rec_int_to_float([1, 2, 3]) == [1.0, 2.0, 3.0]
        assert rec_int_to_float([1, True, 2.5]) == [1.0, 1.0, 2.5]

    def test_dict_recursive(self):
        assert rec_int_to_float({"a": 1, "b": True}) == {"a": 1.0, "b": 1.0}
        assert rec_int_to_float({"a": 1, "b": [2, 3]}) == {"a": 1.0, "b": [2.0, 3.0]}

    def test_nested(self):
        data = {"a": 1, "b": True, "c": [1, 2.5], "d": {"e": 0}}
        expected = {"a": 1.0, "b": 1.0, "c": [1.0, 2.5], "d": {"e": 0.0}}
        assert rec_int_to_float(data) == expected


class TestComputeProfileHash:
    """Test hash computation."""

    def test_known_synthetic_hash(self):
        # Known-answer test: hash of {"a":1.0,"b":1.0,"c":[1.0,2.5],"d":{"e":0.0}}
        data = {"a": 1, "b": True, "c": [1, 2.5], "d": {"e": 0}}
        expected = "977bc4b7cac3f9e4d296c114cec1191b2b89c466799e496c39cc7b6a21aba55e"
        assert compute_profile_hash(data) == expected

    def test_v42_fixture_hash(self):
        """Compute hash over the v4.2.0 fixture minus its stale hash."""
        import ast
        from pathlib import Path

        fixture_path = Path("tests/fixtures/alogs/v4.2.0_2026-10-04.alog")
        raw = fixture_path.read_bytes()
        data = ast.literal_eval(raw.decode("utf-8"))
        
        # The fixture has a stale hash; compute what it should be
        expected = "37b8fc8260d50b0fa11025f72f069c7c12fe6e434db456100a5a1574212024b8"
        
        # Remove hash and compute
        data_no_hash = {k: v for k, v in data.items() if k != "hash"}
        computed = compute_profile_hash(data_no_hash)
        
        assert computed == expected

    def test_hash_excludes_hash_key(self):
        """Verify that the hash field itself is excluded from computation."""
        data1 = {"a": 1, "b": 2, "hash": "fake1"}
        data2 = {"a": 1, "b": 2, "hash": "fake2"}
        # Both should have the same hash since hash key is excluded
        assert compute_profile_hash(data1) == compute_profile_hash(data2)


class TestVerifyProfileHash:
    """Test hash verification."""

    def test_valid_hash_returns_true(self):
        data = {"a": 1, "b": True}
        computed = compute_profile_hash(data)
        data["hash"] = computed
        assert verify_profile_hash(data) is True

    def test_missing_hash_returns_false(self):
        data = {"a": 1, "b": 2}
        assert verify_profile_hash(data) is False

    def test_invalid_hash_returns_false(self):
        data = {"a": 1, "b": 2, "hash": "wrong"}
        assert verify_profile_hash(data) is False

    def test_v42_fixture_has_stale_hash(self):
        """The v4.2.0 fixture has a stale hash (anonymization changed values)."""
        import ast
        from pathlib import Path

        fixture_path = Path("tests/fixtures/alogs/v4.2.0_2026-10-04.alog")
        raw = fixture_path.read_bytes()
        data = ast.literal_eval(raw.decode("utf-8"))
        
        # Should return False because hash is stale
        assert verify_profile_hash(data) is False

    def test_v42_fixture_with_recomputed_hash(self):
        """After recomputing hash, verification should pass."""
        import ast
        from pathlib import Path

        fixture_path = Path("tests/fixtures/alogs/v4.2.0_2026-10-04.alog")
        raw = fixture_path.read_bytes()
        data = ast.literal_eval(raw.decode("utf-8"))
        
        # Recompute the hash
        data["hash"] = compute_profile_hash(data)
        
        # Now verification should pass
        assert verify_profile_hash(data) is True


class TestProfileDataKeys:
    """Test PROFILE_DATA_KEYS set."""

    def test_has_211_keys(self):
        assert len(PROFILE_DATA_KEYS) == 211

    def test_contains_v42_fixture_keys(self):
        """All keys in the v4.2.0 fixture must be in PROFILE_DATA_KEYS."""
        import ast
        from pathlib import Path

        fixture_path = Path("tests/fixtures/alogs/v4.2.0_2026-10-04.alog")
        raw = fixture_path.read_bytes()
        data = ast.literal_eval(raw.decode("utf-8"))
        
        fixture_keys = set(data.keys())
        assert fixture_keys.issubset(PROFILE_DATA_KEYS)

    def test_contains_known_schema_keys(self):
        """Verify new schema keys from 4.2.0 and corpus are present."""
        expected_keys = {
            "legendloc_pos", "plus_blend_label", "plus_coffee",
            "plus_coffee_label", "plus_store", "plus_store_label", "oversampling",
        }
        assert expected_keys.issubset(PROFILE_DATA_KEYS)

    def test_excludes_non_schema_keys(self):
        """Verify non-schema keys are excluded."""
        non_schema_keys = {
            "bbp_begin_to_bottom_ror", "bbp_begin_to_bottom_time",
            "bbp_bottom_temp", "bbp_bottom_to_charge_ror",
            "bbp_bottom_to_charge_time",
        }
        assert PROFILE_DATA_KEYS.isdisjoint(non_schema_keys)

    def test_contains_common_keys(self):
        """Verify some well-known keys are present."""
        expected_keys = {
            "version", "revision", "hash", "signature",
            "flavors", "flavorlabels", "cuppingnotes",
            "heavyFC", "lowFC", "lightCut", "darkCut", "drops",
            "oily", "uneven", "tipping", "scorching", "divots",
            "roastUUID", "roastisodate", "title", "beans",
        }
        assert expected_keys.issubset(PROFILE_DATA_KEYS)
