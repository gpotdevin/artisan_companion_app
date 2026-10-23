"""Native sync writer: opt-in backup-then-write of sensory fields into .alog files.

Writes the following native Artisan fields from a sensory record into the
corresponding .alog profile:
  - flavors <- record["radar"]["values"]
  - flavorlabels <- record["radar"]["labels"]
  - cuppingnotes <- record["cuppings"][0]["notes"] (first cupping, or "" if none)
  - defect booleans <- record["defects_observed"]

For v4.2+ profiles, keeps the original signature untouched and recomputes
the hash field so Artisan loads the file without integrity warnings.
Pre-v4.2 profiles have no hash/signature, so fields are written directly.

A .bak backup is created (once) before the first modification.
"""

from __future__ import annotations

import ast
import reprlib
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from .integrity import (
    PROFILE_DATA_KEYS,
    compute_profile_hash,
    rec_int_to_float,
)

PathLike = Union[str, Path]

# Mapping from sidecar record paths to native profile keys.
NATIVE_FIELDS: dict[str, str] = {
    "radar.values": "flavors",
    "radar.labels": "flavorlabels",
    "cuppings.0.notes": "cuppingnotes",
    **{f"defects_observed.{key}": key for key in (
        "heavyFC", "lowFC", "lightCut", "darkCut", "drops",
        "oily", "uneven", "tipping", "scorching", "divots",
    )},
}


class SyncError(Exception):
    """Raised when a sync operation cannot proceed due to validation failure."""

    def __init__(self, message: str, invalid_keys: Optional[list[str]] = None) -> None:
        super().__init__(message)
        self.invalid_keys = invalid_keys or []


@dataclass(frozen=True)
class SyncResult:
    """Result of a sync operation on a single .alog file."""

    path: Path
    backup_path: Optional[Path] = None
    fields_written: list[str] = field(default_factory=list)
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    changed: bool = False
    dry_run: bool = False


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string like '4.2.0' or '4.2' into a tuple of ints."""
    parts = []
    for part in version_str.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)


def _version_ge(a: str, b: str) -> bool:
    """Return True if version a >= version b (string comparison)."""
    return _parse_version(a) >= _parse_version(b)


def _validate_types(profile: dict[str, Any]) -> None:
    """Validate that native sensory fields have correct types.
    
    Raises SyncError if any field has an incompatible type.
    """
    errors = []
    
    # flavors: list of numbers (will be written as floats)
    flavors = profile.get("flavors")
    if flavors is not None:
        if not isinstance(flavors, list):
            errors.append("flavors must be a list")
        else:
            for i, v in enumerate(flavors):
                if not isinstance(v, (int, float)):
                    errors.append(f"flavors[{i}] must be a number, got {type(v).__name__}")
    
    # flavorlabels: list of strings
    flavorlabels = profile.get("flavorlabels")
    if flavorlabels is not None:
        if not isinstance(flavorlabels, list):
            errors.append("flavorlabels must be a list")
        else:
            for i, v in enumerate(flavorlabels):
                if not isinstance(v, str):
                    errors.append(f"flavorlabels[{i}] must be a string, got {type(v).__name__}")
    
    # cuppingnotes: string
    cuppingnotes = profile.get("cuppingnotes")
    if cuppingnotes is not None and not isinstance(cuppingnotes, str):
        errors.append(f"cuppingnotes must be a string, got {type(cuppingnotes).__name__}")
    
    # defect booleans
    defect_keys = ("heavyFC", "lowFC", "lightCut", "darkCut", "drops",
                   "oily", "uneven", "tipping", "scorching", "divots")
    for key in defect_keys:
        val = profile.get(key)
        if val is not None and not isinstance(val, (bool, int)):
            errors.append(f"{key} must be a bool, got {type(val).__name__}")
    
    if errors:
        raise SyncError("; ".join(errors))


def _check_unknown_keys(profile: dict[str, Any]) -> None:
    """Refuse files with keys outside PROFILE_DATA_KEYS.
    
    Raises SyncError listing the unknown keys.
    """
    unknown = set(profile.keys()) - PROFILE_DATA_KEYS
    if unknown:
        raise SyncError(
            f"profile contains unknown keys: {', '.join(sorted(unknown))}",
            invalid_keys=list(unknown),
        )


def _apply_native_fields(profile: dict[str, Any], record: dict[str, Any]) -> list[str]:
    """Apply sensory record fields to the profile dict.
    
    Returns the list of native keys that were written.
    """
    written = []
    
    # radar.values -> flavors
    if "radar" in record and "values" in record["radar"]:
        profile["flavors"] = [float(v) for v in record["radar"]["values"]]
        written.append("flavors")
    
    # radar.labels -> flavorlabels
    if "radar" in record and "labels" in record["radar"]:
        profile["flavorlabels"] = list(record["radar"]["labels"])
        written.append("flavorlabels")
    
    # cuppings[0].notes -> cuppingnotes
    if "cuppings" in record and len(record["cuppings"]) > 0:
        notes = record["cuppings"][0].get("notes", "")
        if notes:
            profile["cuppingnotes"] = notes
            written.append("cuppingnotes")
        elif "cuppingnotes" in profile:
            # If there's no note in the record, leave existing value unchanged
            pass
        else:
            profile["cuppingnotes"] = ""
            written.append("cuppingnotes")
    else:
        # No cuppings: set to empty string if not present, leave if present
        if "cuppingnotes" not in profile:
            profile["cuppingnotes"] = ""
            written.append("cuppingnotes")
    
    # defects_observed -> defect booleans
    if "defects_observed" in record:
        for key, value in record["defects_observed"].items():
            profile[key] = bool(value)
            written.append(key)
    
    return written


def _create_backup(alog_path: Path) -> Optional[Path]:
    """Create a .bak backup if one doesn't exist yet.
    
    Returns the backup path if created, None if already exists.
    """
    backup_path = alog_path.with_suffix(".alog.bak")
    if backup_path.exists():
        return None
    shutil.copy2(alog_path, backup_path)
    return backup_path


def _load_alog(path: PathLike) -> dict[str, Any]:
    """Load an .alog file as a Python dict via ast.literal_eval."""
    p = Path(path)
    raw = p.read_bytes()
    if raw[:1] != b"{":
        raise SyncError(f"{p}: not an Artisan pydump (first byte is not '{{')")
    try:
        data = ast.literal_eval(raw.decode("utf-8"))
    except (SyntaxError, ValueError, TypeError, UnicodeDecodeError) as exc:
        raise SyncError(f"{p}: pydump parse failed ({exc})") from exc
    if not isinstance(data, dict):
        raise SyncError(f"{p}: top-level object is not a dict")
    return data


def _write_alog(path: Path, data: dict[str, Any]) -> None:
    """Write a profile dict back to an .alog file using repr().
    
    This produces byte-identical serialization to Artisan's own format.
    """
    serialized = repr(data)
    path.write_text(serialized, encoding="utf-8")


def sync_alog(
    alog_path: PathLike,
    record: dict[str, Any],
    *,
    backup: bool = True,
    dry_run: bool = False,
    store: Optional[Any] = None,
    store_uuid: Optional[str] = None,
) -> SyncResult:
    """Sync sensory fields from a sidecar record into an .alog file.
    
    Args:
        alog_path: Path to the .alog file to modify.
        record: The sensory sidecar record containing the data to write.
        backup: If True (default), create a .bak backup on first modification.
        dry_run: If True, compute and return the result without writing.
        store: Optional SensoryStore instance to update with sync audit.
        store_uuid: Optional roast UUID (if store is provided but record
                   doesn't have roast_uuid).
    
    Returns:
        SyncResult with details of the operation.
    
    Raises:
        SyncError: If the profile contains unknown keys, or if field types
                  are incompatible.
    """
    alog_path = Path(alog_path)
    
    # Load the existing profile
    profile = _load_alog(alog_path)
    
    # Check for unknown keys
    _check_unknown_keys(profile)
    
    # Save the old hash for the result
    old_hash = profile.get("hash")
    
    # Apply the native fields from the record
    fields_written = _apply_native_fields(profile, record)
    
    # Validate types after applying
    _validate_types(profile)
    
    # Determine if we need to recompute hash
    version = profile.get("version", "0")
    is_v42_plus = _version_ge(version, "4.2")
    has_hash = "hash" in profile
    has_signature = "signature" in profile
    
    new_hash = None
    
    if is_v42_plus or has_hash or has_signature:
        # v4.2+: keep signature untouched, recompute hash
        # Also recompute hash if present in pre-4.2 (shouldn't happen but be safe)
        new_hash = compute_profile_hash(profile)
        profile["hash"] = new_hash
    
    # Compute changed: compare serialized content
    original_bytes = alog_path.read_bytes()
    if not dry_run:
        new_serialized = repr(profile).encode("utf-8")
    else:
        # For dry run, we still need to check if it would change
        new_serialized = repr(profile).encode("utf-8")
    
    changed = (new_serialized != original_bytes)
    
    backup_path = None
    
    if not dry_run:
        # Create backup if requested and this is the first modification
        if backup and changed:
            backup_path = _create_backup(alog_path)
        
        # Write the modified profile
        if changed:
            _write_alog(alog_path, profile)
    
    # Update audit trail in store if provided
    if store is not None:
        uuid = store_uuid or record.get("roast_uuid")
        if uuid:
            store.set_native_sync(uuid, fields_written)
    
    return SyncResult(
        path=alog_path,
        backup_path=Path(backup_path) if backup_path else None,
        fields_written=fields_written,
        old_hash=old_hash,
        new_hash=new_hash,
        changed=changed,
        dry_run=dry_run,
    )
