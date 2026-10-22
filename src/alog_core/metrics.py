"""Derived curve metrics. Pure functions, stdlib only."""

from __future__ import annotations

from bisect import bisect_right
from typing import Optional, Sequence


def ror(
    bt: Sequence[Optional[float]],
    times: Sequence[float],
    window_s: float = 15.0,
) -> list[Optional[float]]:
    """Rate of rise of the bean-temperature curve, in °C/min per sample.

    Each point's RoR is the secant slope between the current sample and a
    trailing reference sample: the last sample whose timestamp is at or
    before ``times[i] - window_s``. This mirrors Artisan's 15 s smoothing
    window while tolerating the non-uniform sample spacing of real logs
    (Phidget readings jitter around the nominal ``samplinginterval``):
    the slope is a true ``(ΔBT, Δt)`` quotient, never a fixed-sample-count
    difference. Points whose window does not reach back to the first sample,
    points with a non-positive time span to the reference, and ``None``
    entries in ``bt`` yield ``None``. ``bt`` and ``times`` are truncated to
    the shorter of the two; ``times`` is assumed non-decreasing, as in all
    Artisan logs. Empty input yields an empty list.
    """
    n = min(len(bt), len(times))
    out: list[Optional[float]] = [None] * n
    if window_s <= 0:
        return out
    for i in range(n):
        b_i = bt[i]
        if b_i is None:
            continue
        t_i = times[i]
        j = bisect_right(times, t_i - window_s) - 1
        if j < 0 or j >= n:
            continue
        b_j = bt[j]
        if b_j is None:
            continue
        dt = t_i - times[j]
        if dt <= 0:
            continue
        out[i] = (b_i - b_j) / dt * 60.0
    return out
