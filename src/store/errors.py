"""Exceptions for the sensory store."""

from __future__ import annotations


class SensoryStoreError(Exception):
    """Raised on sensory store failures (validation, sidecar I/O, index)."""
