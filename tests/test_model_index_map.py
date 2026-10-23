"""Regression tests for the index map fix (M-1).

These tests verify that markers and events correctly map to retained samples
when some raw samples are dropped due to non-numeric time/ET/BT values.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alog_core import parse_profile


def write_alog(tmp_path: Path, data: dict, name: str = "synthetic.alog") -> Path:
    """Write a dict as an Artisan-style single-line pydump."""
    p = tmp_path / name
    p.write_text(repr(data), encoding="ascii")
    return p


def synthetic_profile_bad_sample(
    n: int = 15,
    bad_at: int | None = 5,
    timeindex: list | None = None,
    **extra: object,
) -> dict:
    """Profile with a bad sample at position bad_at (None for no bad samples)."""
    timex = [float(i) for i in range(n)]
    temp1 = [100.0 + 2.0 * i for i in range(n)]
    temp2 = [25.0 + 3.0 * i for i in range(n)]
    if bad_at is not None:
        # Make BT non-numeric at bad_at
        temp2[bad_at] = None
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": timex,
        "temp1": temp1,
        "temp2": temp2,
        "timeindex": timeindex if timeindex is not None else [0] * 8,
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
    }
    d.update(extra)
    return d


# ---------------------------------------------------------------------------
# Identity behavior: clean profiles have identity index map
# ---------------------------------------------------------------------------

def test_identity_map_clean_profile(tmp_path: Path) -> None:
    """For a clean profile with no dropped samples, markers/events map to
    the same positions as the raw timeindex."""
    ti = [2, 5, 9, 0, 0, 0, 12, 0]  # CHARGE=2, DRY=5, FCs=9, DROP=12
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(15)],
        "temp1": [100.0 + 2.0 * i for i in range(15)],
        "temp2": [25.0 + 3.0 * i for i in range(15)],
        "timeindex": ti,
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
    }
    p = write_alog(tmp_path, d)
    
    profile = parse_profile(p)
    
    # All markers should be present with times matching raw timex
    assert "CHARGE" in profile.markers
    assert profile.markers["CHARGE"].time_s == pytest.approx(0.0)  # timex[2] - timex[2]
    assert profile.markers["CHARGE"].temp_bt_c == pytest.approx(25.0 + 3.0 * 2)
    
    assert "DRY" in profile.markers
    assert profile.markers["DRY"].time_s == pytest.approx(5.0 - 2.0)
    assert profile.markers["DRY"].temp_bt_c == pytest.approx(25.0 + 3.0 * 5)
    
    assert "FCs" in profile.markers
    assert profile.markers["FCs"].time_s == pytest.approx(9.0 - 2.0)
    
    assert "DROP" in profile.markers
    assert profile.markers["DROP"].time_s == pytest.approx(12.0 - 2.0)


def test_identity_events_clean_profile(tmp_path: Path) -> None:
    """For a clean profile, event times equal raw timex times (relative to CHARGE)."""
    p = write_alog(tmp_path, {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(15)],
        "temp1": [100.0 + 2.0 * i for i in range(15)],
        "temp2": [25.0 + 3.0 * i for i in range(15)],
        "timeindex": [2, 0, 0, 0, 0, 0, 0, 0],  # CHARGE at 2
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
        "specialevents": [3, 7, 10],
        "specialeventstype": [0, 1, 2],
        "specialeventsvalue": [5.0, 10.0, 15.0],
        "specialeventsStrings": ["5", "10", "15"],
    })
    
    profile = parse_profile(p)
    
    # Events should have times matching raw timex relative to CHARGE (at 2)
    assert len(profile.events) == 3
    assert profile.events[0].time_s == pytest.approx(3.0 - 2.0)
    assert profile.events[0].index == 3
    assert profile.events[1].time_s == pytest.approx(7.0 - 2.0)
    assert profile.events[1].index == 7
    assert profile.events[2].time_s == pytest.approx(10.0 - 2.0)
    assert profile.events[2].index == 10


# ---------------------------------------------------------------------------
# Index shift fix: profiles with dropped samples
# ---------------------------------------------------------------------------

def test_markers_map_to_correct_retained_samples_with_bad_bt(tmp_path: Path) -> None:
    """When a sample with bad BT is dropped, markers still point to correct retained samples."""
    # Create profile with bad sample at index 5
    # CHARGE at raw index 2, DROP at raw index 10
    # After dropping index 5, the coerced series has 14 samples
    # CHARGE should be at coerced index 2, DROP at coerced index 9 (since 5 was dropped)
    
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(12)],
        "temp1": [100.0 + 2.0 * i for i in range(12)],
        "temp2": [25.0 + 3.0 * i for i in range(12)],
        "timeindex": [2, 0, 0, 0, 0, 0, 10, 0],  # CHARGE at 2, DROP at 10
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
    }
    # Make sample 5 have bad BT (None)
    d["temp2"][5] = None
    
    p = write_alog(tmp_path, d)
    profile = parse_profile(p)
    
    # 11 valid samples (index 5 dropped)
    assert len(profile.times_s) == 11
    
    # CHARGE at raw index 2 -> coerced index 2 (not dropped)
    assert "CHARGE" in profile.markers
    assert profile.markers["CHARGE"].time_s == pytest.approx(0.0)
    assert profile.markers["CHARGE"].temp_bt_c == pytest.approx(25.0 + 3.0 * 2)
    
    # DROP at raw index 10 -> coerced index 9 (since index 5 was dropped)
    assert "DROP" in profile.markers
    assert profile.markers["DROP"].time_s == pytest.approx(10.0 - 2.0)
    assert profile.markers["DROP"].temp_bt_c == pytest.approx(25.0 + 3.0 * 10)


def test_markers_with_bad_sample_before_charge(tmp_path: Path) -> None:
    """When a bad sample exists before CHARGE, indices still align correctly."""
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(10)],
        "temp1": [100.0 + 2.0 * i for i in range(10)],
        "temp2": [25.0 + 3.0 * i for i in range(10)],
        "timeindex": [3, 0, 0, 0, 0, 0, 7, 0],  # CHARGE at 3, DROP at 7
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
    }
    # Make sample 1 have bad BT
    d["temp2"][1] = None
    
    p = write_alog(tmp_path, d)
    profile = parse_profile(p)
    
    # 9 valid samples (index 1 dropped)
    assert len(profile.times_s) == 9
    
    # CHARGE at raw index 3 -> coerced index 2 (since index 1 was dropped before it)
    assert "CHARGE" in profile.markers
    # timex[3] - timex[3] = 0
    assert profile.markers["CHARGE"].time_s == pytest.approx(0.0)
    
    # DROP at raw index 7 -> coerced index 6 (since index 1 was dropped)
    assert "DROP" in profile.markers
    # timex[7] - timex[3] = 7 - 3 = 4
    assert profile.markers["DROP"].time_s == pytest.approx(4.0)


def test_events_map_to_correct_retained_samples_with_bad_bt(tmp_path: Path) -> None:
    """When samples are dropped, events still map to correct retained samples."""
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(15)],
        "temp1": [100.0 + 2.0 * i for i in range(15)],
        "temp2": [25.0 + 3.0 * i for i in range(15)],
        "timeindex": [2, 0, 0, 0, 0, 0, 0, 0],  # CHARGE at 2
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
        "specialevents": [3, 5, 8, 10],  # Events at raw indices 3, 5, 8, 10
        "specialeventstype": [0, 1, 2, 3],
        "specialeventsvalue": [5.0, 10.0, 15.0, 20.0],
        "specialeventsStrings": ["5", "10", "15", "20"],
    }
    # Make sample 5 have bad BT (None)
    d["temp2"][5] = None
    
    p = write_alog(tmp_path, d)
    profile = parse_profile(p)
    
    # 14 valid samples (index 5 dropped)
    assert len(profile.times_s) == 14
    
    # Event at raw index 3 -> coerced index 3
    # Event at raw index 5 -> dropped (should not appear)
    # Event at raw index 8 -> coerced index 7 (since index 5 was dropped)
    # Event at raw index 10 -> coerced index 9 (since index 5 was dropped)
    
    assert len(profile.events) == 3
    
    # Sort events by time for easier comparison
    events_by_time = sorted(profile.events, key=lambda e: e.time_s)
    
    # Event at coerced index 3 (raw index 3)
    assert events_by_time[0].index == 3
    assert events_by_time[0].time_s == pytest.approx(3.0 - 2.0)
    
    # Event at coerced index 7 (raw index 8)
    assert events_by_time[1].index == 7
    assert events_by_time[1].time_s == pytest.approx(8.0 - 2.0)
    
    # Event at coerced index 9 (raw index 10)
    assert events_by_time[2].index == 9
    assert events_by_time[2].time_s == pytest.approx(10.0 - 2.0)


def test_event_at_dropped_sample_is_absent(tmp_path: Path) -> None:
    """An event whose raw sample was dropped should be absent from the profile."""
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(10)],
        "temp1": [100.0 + 2.0 * i for i in range(10)],
        "temp2": [25.0 + 3.0 * i for i in range(10)],
        "timeindex": [1, 0, 0, 0, 0, 0, 0, 0],  # CHARGE at 1
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
        "specialevents": [3, 5, 7],  # Events at raw indices 3, 5, 7
        "specialeventstype": [0, 1, 2],
        "specialeventsvalue": [5.0, 10.0, 15.0],
        "specialeventsStrings": ["5", "10", "15"],
    }
    # Make sample 5 have bad BT (None) - this is where an event is
    d["temp2"][5] = None
    
    p = write_alog(tmp_path, d)
    profile = parse_profile(p)
    
    # 9 valid samples (index 5 dropped)
    assert len(profile.times_s) == 9
    
    # Only 2 events should be present (raw index 5 was dropped)
    assert len(profile.events) == 2
    
    # The remaining events should be at the correct coerced indices
    # raw 3 -> coerced 3 (no drops before it)
    # raw 7 -> coerced 6 (since index 5 was dropped)
    event_indices = sorted([e.index for e in profile.events])
    assert event_indices == [3, 6]


def test_marker_at_dropped_sample_is_absent(tmp_path: Path) -> None:
    """A marker whose raw sample was dropped should be absent from the profile."""
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(12)],
        "temp1": [100.0 + 2.0 * i for i in range(12)],
        "temp2": [25.0 + 3.0 * i for i in range(12)],
        "timeindex": [2, 5, 0, 0, 0, 0, 10, 0],  # CHARGE at 2, DRY at 5, DROP at 10
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
    }
    # Make sample 5 (DRY marker) have bad BT
    d["temp2"][5] = None
    
    p = write_alog(tmp_path, d)
    profile = parse_profile(p)
    
    # DRY marker at raw index 5 should be absent
    assert "CHARGE" in profile.markers
    assert "DRY" not in profile.markers
    assert "DROP" in profile.markers


def test_marker_at_dropped_sample_bad_et(tmp_path: Path) -> None:
    """Marker dropped when ET is bad (not just BT)."""
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(12)],
        "temp1": [100.0 + 2.0 * i for i in range(12)],
        "temp2": [25.0 + 3.0 * i for i in range(12)],
        "timeindex": [2, 5, 0, 0, 0, 0, 10, 0],  # CHARGE at 2, DRY at 5, DROP at 10
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
    }
    # Make sample 5 (DRY marker) have bad ET
    d["temp1"][5] = "broken"
    
    p = write_alog(tmp_path, d)
    profile = parse_profile(p)
    
    # DRY marker at raw index 5 should be absent
    assert "CHARGE" in profile.markers
    assert "DRY" not in profile.markers
    assert "DROP" in profile.markers


def test_marker_at_dropped_sample_bad_time(tmp_path: Path) -> None:
    """Marker dropped when time is bad."""
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(12)],
        "temp1": [100.0 + 2.0 * i for i in range(12)],
        "temp2": [25.0 + 3.0 * i for i in range(12)],
        "timeindex": [2, 5, 0, 0, 0, 0, 10, 0],  # CHARGE at 2, DRY at 5, DROP at 10
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
    }
    # Make sample 5 (DRY marker) have bad time
    d["timex"][5] = "broken"
    
    p = write_alog(tmp_path, d)
    profile = parse_profile(p)
    
    # DRY marker at raw index 5 should be absent
    assert "CHARGE" in profile.markers
    assert "DRY" not in profile.markers
    assert "DROP" in profile.markers


def test_multiple_bad_samples_with_markers_and_events(tmp_path: Path) -> None:
    """Complex case: multiple bad samples affecting markers and events."""
    d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(20)],
        "temp1": [100.0 + 2.0 * i for i in range(20)],
        "temp2": [25.0 + 3.0 * i for i in range(20)],
        "timeindex": [2, 5, 8, 0, 0, 0, 15, 0],  # CHARGE=2, DRY=5, FCs=8, DROP=15
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
        "specialevents": [4, 7, 10, 15, 18],
        "specialeventstype": [0, 1, 2, 3, 0],
        "specialeventsvalue": [5.0, 10.0, 15.0, 20.0, 25.0],
        "specialeventsStrings": ["5", "10", "15", "20", "25"],
    }
    # Make samples 5 (DRY marker), 10, and 15 (DROP marker) have bad BT
    d["temp2"][5] = None
    d["temp2"][10] = None
    d["temp2"][15] = None
    
    p = write_alog(tmp_path, d)
    profile = parse_profile(p)
    
    # 17 valid samples (indices 5, 10, 15 dropped)
    assert len(profile.times_s) == 17
    
    # DRY and DROP markers should be absent (at dropped samples)
    assert "CHARGE" in profile.markers
    assert "DRY" not in profile.markers
    assert "FCs" in profile.markers
    assert "DROP" not in profile.markers
    
    # FCs at raw index 8 -> coerced index 7 (since 5 was dropped before it)
    assert profile.markers["FCs"].time_s == pytest.approx(8.0 - 2.0)
    
    # Events at raw indices 4, 7, 10, 15, 18
    # raw 4 -> coerced 4 (no drops before it)
    # raw 7 -> coerced 6 (no drops before it, but index 5 is dropped so 7->6)
    # raw 10 -> dropped (should not appear)
    # raw 15 -> dropped (should not appear)
    # raw 18 -> coerced 15 (indices 5, 10, 15 were dropped before it)
    assert len(profile.events) == 3
    event_indices = sorted([e.index for e in profile.events])
    assert event_indices == [4, 6, 15]


def test_bad_samples_comparison_with_clean_profile(tmp_path: Path) -> None:
    """Verify that a profile with a bad sample removed entirely produces
    the same marker/event positions as the same profile with the bad sample
    present but dropped.
    """
    # Base profile with CHARGE and DROP markers and events
    base_d = {
        "version": "4.2.0",
        "mode": "C",
        "timex": [float(i) for i in range(12)],
        "temp1": [100.0 + 2.0 * i for i in range(12)],
        "temp2": [25.0 + 3.0 * i for i in range(12)],
        "timeindex": [2, 0, 0, 0, 0, 0, 10, 0],  # CHARGE at 2, DROP at 10
        "etypes": ["Air", "Drum", "Damper", "Burner", "--"],
        "specialevents": [4, 7],
        "specialeventstype": [0, 1],
        "specialeventsvalue": [5.0, 10.0],
        "specialeventsStrings": ["5", "10"],
    }
    
    # Profile 1: clean (no bad samples), remove index 5 entirely
    d1 = {
        **base_d,
        "timex": [float(i) for i in range(12) if i != 5],
        "temp1": [100.0 + 2.0 * i for i in range(12) if i != 5],
        "temp2": [25.0 + 3.0 * i for i in range(12) if i != 5],
        # Adjust timeindex: CHARGE was at 2, now at 2; DROP was at 10, now at 9
        "timeindex": [2, 0, 0, 0, 0, 0, 9, 0],
        # Adjust event indices: 4 stays 4, 7 becomes 6
        "specialevents": [4, 6],
    }
    
    # Profile 2: has bad sample at index 5 (bad BT)
    d2 = {**base_d}
    d2["temp2"][5] = None
    
    p1 = write_alog(tmp_path, d1, "clean.alog")
    p2 = write_alog(tmp_path, d2, "with_bad.alog")
    
    profile1 = parse_profile(p1)
    profile2 = parse_profile(p2)
    
    # Both should have 11 samples
    assert len(profile1.times_s) == 11
    assert len(profile2.times_s) == 11
    
    # Both should have CHARGE and DROP at the same times
    assert profile1.markers["CHARGE"].time_s == pytest.approx(profile2.markers["CHARGE"].time_s)
    assert profile1.markers["DROP"].time_s == pytest.approx(profile2.markers["DROP"].time_s)
    
    # Both should have events at the same times
    assert len(profile1.events) == 2
    assert len(profile2.events) == 2
    assert profile1.events[0].time_s == pytest.approx(profile2.events[0].time_s)
    assert profile1.events[1].time_s == pytest.approx(profile2.events[1].time_s)
