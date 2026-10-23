"""Native sync for Artisan .alog files: opt-in backup-then-write of sensory fields.

This package provides the infrastructure for milestone M4: writing sidecar
sensory data back into .alog files with proper integrity handling for
Artisan v4.2+ (hash/signature preservation).

Main entry point: :func:`sync_alog`
"""

from .integrity import (
    PROFILE_DATA_KEYS,
    compute_profile_hash,
    rec_int_to_float,
    verify_profile_hash,
)
from .writer import (
    NATIVE_FIELDS,
    SyncError,
    SyncResult,
    sync_alog,
)

__all__ = [
    "sync_alog",
    "SyncResult",
    "SyncError",
    "compute_profile_hash",
    "verify_profile_hash",
    "rec_int_to_float",
    "PROFILE_DATA_KEYS",
    "NATIVE_FIELDS",
]
