"""alog_core: stdlib-only reader and indexer for Artisan .alog roast logs.

Public API:
    load_alog       -- parse an .alog pydump into a raw dict
    parse_profile   -- parse an .alog file into a typed RoastProfile
    build_index     -- (re)build a SQLite index over a folder of .alog files
    list_roasts     -- list the rows of a built index
    AlogParseError  -- raised on read/parse failures
"""

from .index import build_index, list_roasts
from .metrics import ror
from .model import (
    Marker,
    RoastEvent,
    RoastMeta,
    RoastProfile,
    parse_profile,
)
from .parser import AlogParseError, load_alog, unescape

__version__ = "0.1.0"

__all__ = [
    "AlogParseError",
    "Marker",
    "RoastEvent",
    "RoastMeta",
    "RoastProfile",
    "build_index",
    "list_roasts",
    "load_alog",
    "parse_profile",
    "ror",
    "unescape",
]
