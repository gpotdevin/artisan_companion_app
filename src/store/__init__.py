"""store: sensory sidecar store for artisan-companion (M2a).

Public API:
    SensoryStore       -- CRUD + search over one sensory folder
    SensoryStoreError  -- raised on store/validation/index failures
    SCHEMA_VERSION     -- sidecar schema version written by this store
    SCORE_KEYS         -- SCA attribute score keys of a cupping
    DEFECT_KEYS        -- native Artisan defect flag keys
    DEFAULT_RADAR_LABELS -- Artisan's default flavor-radar axis labels
"""

from .errors import SensoryStoreError
from .schema import (
    DEFAULT_RADAR_LABELS,
    DEFECT_KEYS,
    SCORE_KEYS,
    SCHEMA_VERSION,
)
from .store import SensoryStore

__all__ = [
    "DEFAULT_RADAR_LABELS",
    "DEFECT_KEYS",
    "SCORE_KEYS",
    "SCHEMA_VERSION",
    "SensoryStore",
    "SensoryStoreError",
]
