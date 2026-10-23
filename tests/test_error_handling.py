"""Error handling tests for sidecars and alog_core index."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from alog_core import AlogParseError, build_index
from store.sidecars import delete_record, SensoryStoreError


class TestBuildIndexErrors:
    """Tests for build_index error handling (FIX 2)."""

    def test_build_index_missing_dir_raises_alog_parse_error(self, tmp_path: Path):
        """build_index on a missing dir raises AlogParseError."""
        missing_dir = tmp_path / "nonexistent"
        db_path = tmp_path / "test.db"
        with pytest.raises(AlogParseError) as exc_info:
            build_index(missing_dir, db_path)
        assert "logs directory does not exist" in str(exc_info.value)

    def test_build_index_not_a_dir_raises_alog_parse_error(self, tmp_path: Path):
        """build_index on a file (not a dir) raises AlogParseError."""
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("not a directory")
        db_path = tmp_path / "test.db"
        with pytest.raises(AlogParseError) as exc_info:
            build_index(file_path, db_path)
        assert "not a directory" in str(exc_info.value)


class TestDeleteRecordErrors:
    """Tests for delete_record error handling (FIX 1)."""

    def test_delete_record_file_not_found_returns_false(self, tmp_path: Path):
        """delete_record returns False when sidecar does not exist."""
        sensory_dir = tmp_path / "sensory"
        sensory_dir.mkdir()
        result = delete_record(sensory_dir, "nonexistent_uuid")
        assert result is False

    def test_delete_record_happy_path_returns_true(self, tmp_path: Path):
        """delete_record returns True on successful deletion."""
        sensory_dir = tmp_path / "sensory"
        sensory_dir.mkdir()
        # Create a sidecar file
        sidecar_path = sensory_dir / "test_uuid.json"
        sidecar_path.write_text('{"roast_uuid": "test_uuid"}')
        result = delete_record(sensory_dir, "test_uuid")
        assert result is True
        assert not sidecar_path.exists()

    def test_delete_record_permission_error_raises_sensory_store_error(self, tmp_path: Path):
        """delete_record on read-only dir raises SensoryStoreError."""
        # Check if platform enforces permissions
        sensory_dir = tmp_path / "sensory_readonly"
        sensory_dir.mkdir()
        
        # Create a sidecar file
        sidecar_path = sensory_dir / "test_uuid.json"
        sidecar_path.write_text('{"roast_uuid": "test_uuid"}')
        
        # Try to make directory read-only
        try:
            # Remove write permission from the directory
            os.chmod(sensory_dir, stat.S_IRUSR | stat.S_IXUSR)
            
            # Verify the directory is actually read-only
            # Try to create a test file to confirm
            try:
                test_file = sensory_dir / ".test_write"
                test_file.write_text("test")
                test_file.unlink()
                # If we can write, skip this test
                pytest.skip("Platform does not enforce read-only directories")
            except (OSError, PermissionError):
                # Good, permissions are enforced
                pass
            
            # Now try to delete - should raise SensoryStoreError
            with pytest.raises(SensoryStoreError) as exc_info:
                delete_record(sensory_dir, "test_uuid")
            assert "cannot delete sidecar" in str(exc_info.value)
            
        except (OSError, PermissionError, NotImplementedError):
            # Clean up and skip if we can't set permissions
            os.chmod(sensory_dir, stat.S_IRWXU)
            pytest.skip("Platform does not enforce read-only directories")
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(sensory_dir, stat.S_IRWXU)
            except (OSError, PermissionError):
                pass
