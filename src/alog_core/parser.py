"""Low-level loading of Artisan .alog files.

An .alog file is Artisan's "pydump": a single-line, pure-ASCII Python dict
literal. It is parsed with ``ast.literal_eval`` only -- log content is never
executed, and the pickle variant used by Artisan < 2.0 is not supported.

String values are stored double-escaped (e.g. ``torr\\xe9`` for ``torré``);
:meth:`unescape` recovers the real text.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Union

PathLike = Union[str, Path]


class AlogParseError(Exception):
    """Raised when an .alog file cannot be read or parsed as an Artisan pydump."""


def unescape(s: str) -> str:
    """Recover text stored as double-escaped ASCII (``torr\\xe9`` -> ``torré``).

    Artisan writes non-ASCII characters as literal backslash escape sequences.
    A latin-1 encode followed by a unicode_escape decode recovers them;
    strings that cannot be latin-1 encoded (already clean text) or whose
    escape sequences are invalid (e.g. literal Windows paths) are returned
    unchanged.
    """
    try:
        return s.encode("latin-1").decode("unicode_escape")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def load_alog(path: PathLike) -> dict[str, Any]:
    """Load an .alog pydump file into a plain dict.

    The file must start with the byte ``{`` (binary pickle logs from
    Artisan < 2.0 are rejected). Raises :class:`AlogParseError` with the
    filename in the message on any read or parse failure. The returned dict
    is a freshly parsed object; it is never mutated by callers of this API.
    """
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as exc:
        raise AlogParseError(f"{p}: cannot read file ({exc})") from exc
    if raw[:1] != b"{":
        raise AlogParseError(
            f"{p}: not an Artisan pydump (first byte is not '{{')")
    try:
        data = ast.literal_eval(raw.decode("utf-8"))
    except (SyntaxError, ValueError, TypeError, UnicodeDecodeError,
            RecursionError) as exc:
        raise AlogParseError(f"{p}: pydump parse failed ({exc})") from exc
    if not isinstance(data, dict):
        raise AlogParseError(f"{p}: top-level object is not a dict")
    return data
