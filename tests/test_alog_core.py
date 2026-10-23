"""Tests for alog_core (M1): parser, unescape, model, metrics, index.

Golden coverage runs over the anonymized corpus fixtures in
tests/fixtures/alogs (one file per Artisan version, 2.4.6 - 4.2.0);
behavioral coverage uses synthetic .alog files written on the fly.
"""

from __future__ import annotations

import hashlib
from bisect import bisect_right
from pathlib import Path

import pytest

from alog_core import (
    AlogParseError,
    RoastProfile,
    build_index,
    list_roasts,
    load_alog,
    parse_profile,
    ror,
    unescape,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "alogs"

# fixture filename -> Artisan version stored in its 'version' key
EXPECTED_VERSIONS = {
    "v2.4.6_2021-11-19_multiline.alog": "2.4.6",
    "v2.6.0_2022-09-16.alog": "2.6.0",
    "v2.8.2_2023-04-09.alog": "2.8.2",
    "v2.10.0_2024-04-02.alog": "2.10.0",
    "v2.10.4_2024-08-03.alog": "2.10.4",
    "v3.2.0_2026-07-23.alog": "3.2.0",
    "v4.2.0_2026-10-04.alog": "4.2.0",
}

# timeindex slot per marker name (see alog_files_technical_description.md)
SLOT_BY_NAME = {"CHARGE": 0, "DRY": 1, "FCs": 2, "DROP": 6, "COOL": 7}
KNOWN_MARKERS = set(SLOT_BY_NAME) | {"TP"}


def fixture_path(name: str) -> Path:
    return FIXTURES_DIR / name


def write_alog(tmp_path: Path, data: dict, name: str = "synthetic.alog") -> Path:
    """Write a dict as an Artisan-style single-line pydump."""
    p = tmp_path / name
    p.write_text(repr(data), encoding="ascii")
    return p


def synthetic_profile(
    n: int = 15,
    timeindex: list | None = None,
    **extra: object,
) -> dict:
    """Minimal well-formed pydump: linear rising BT/ET over n samples."""
    timex = [float(i) for i in range(n)]
    temp1 = [100.0 + 2.0 * i for i in range(n)]
    temp2 = [25.0 + 3.0 * i for i in range(n)]
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
# Fixture corpus integrity
# ---------------------------------------------------------------------------

def test_fixture_corpus_contents() -> None:
    """The fixture dir holds exactly the expected files, all ASCII pydumps."""
    names = sorted(p.name for p in FIXTURES_DIR.glob("*.alog"))
    assert names == sorted(EXPECTED_VERSIONS)
    for name in names:
        raw = fixture_path(name).read_bytes()
        assert raw[:1] == b"{"
        assert all(b < 128 for b in raw), f"{name} is not pure ASCII"


# ---------------------------------------------------------------------------
# parser: unescape
# ---------------------------------------------------------------------------

def test_unescape_recovers_double_escaped_accents() -> None:
    assert unescape("torr\\xe9faction") == "torréfaction"
    assert unescape("Br\\xfbleur") == "Brûleur"


def test_unescape_interprets_backslash_sequences() -> None:
    assert unescape("Schneid\\n\\n") == "Schneid\n\n"


def test_unescape_plain_ascii_unchanged() -> None:
    assert unescape("Abricot 1") == "Abricot 1"
    assert unescape("30mBar") == "30mBar"
    assert unescape("") == ""


def test_unescape_non_latin1_text_returned_unchanged() -> None:
    # not latin-1 encodable -> the escape pass is skipped entirely
    assert unescape("€ 400") == "€ 400"


# ---------------------------------------------------------------------------
# parser: load_alog
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(EXPECTED_VERSIONS))
def test_load_alog_returns_expected_raw_dict(name: str) -> None:
    d = load_alog(fixture_path(name))
    assert isinstance(d, dict)
    assert d["version"] == EXPECTED_VERSIONS[name]
    for key in ("timex", "temp1", "temp2", "timeindex"):
        assert isinstance(d.get(key), list), f"missing/invalid key: {key}"
    assert len(d["timex"]) == len(d["temp1"]) == len(d["temp2"]) > 0
    assert all(isinstance(v, (int, float)) for v in d["timex"])
    assert len(d["timeindex"]) == 8


def test_load_alog_rejects_non_pydump_first_byte(tmp_path: Path) -> None:
    p = tmp_path / "not_pydump.alog"
    p.write_text("[1, 2, 3]", encoding="ascii")
    with pytest.raises(AlogParseError, match="not an Artisan pydump"):
        load_alog(p)


def test_load_alog_rejects_pickle_variant(tmp_path: Path) -> None:
    p = tmp_path / "old_pickle.alog"
    p.write_bytes(b"\x80\x04\x95\x0f\x00\x00\x00\x00\x00\x00\x00}")
    with pytest.raises(AlogParseError):
        load_alog(p)


def test_load_alog_rejects_truncated_literal(tmp_path: Path) -> None:
    p = tmp_path / "truncated.alog"
    p.write_text("{'version': '2.4.6', 'timex': [1, 2", encoding="ascii")
    with pytest.raises(AlogParseError, match="parse failed"):
        load_alog(p)


def test_load_alog_rejects_non_dict_top_level(tmp_path: Path) -> None:
    p = tmp_path / "set.alog"
    p.write_text("{1, 2, 3}", encoding="ascii")
    with pytest.raises(AlogParseError, match="not a dict"):
        load_alog(p)


def test_load_alog_rejects_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.alog"
    with pytest.raises(AlogParseError, match="cannot read file"):
        load_alog(missing)


# ---------------------------------------------------------------------------
# model: golden-file parse of every fixture
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(EXPECTED_VERSIONS))
def test_golden_parse_types_and_meta(name: str) -> None:
    profile = parse_profile(fixture_path(name))
    raw = load_alog(fixture_path(name))
    assert isinstance(profile, RoastProfile)
    n = len(raw["timex"])
    # every fixture sample is valid -> no rows dropped
    assert len(profile.times_s) == len(profile.bt_c) == len(profile.et_c) == n
    for series in (profile.times_s, profile.bt_c, profile.et_c):
        assert all(isinstance(v, float) for v in series)
    assert profile.times_s == sorted(profile.times_s)
    assert len(profile.ror_c_per_min) == n
    assert all(v is None or isinstance(v, float) for v in profile.ror_c_per_min)
    # metadata
    assert profile.meta.artisan_version == EXPECTED_VERSIONS[name]
    assert profile.meta.roast_isodate == unescape(raw["roastisodate"])
    assert profile.meta.mode == "C"
    assert profile.meta.roastertype == unescape(raw["roastertype"])
    assert profile.meta.machinesetup == unescape(raw["machinesetup"])
    assert profile.meta.sampling_interval_s == 2.0
    assert isinstance(profile.meta.roast_epoch, int)
    assert set(profile.markers) <= KNOWN_MARKERS


@pytest.mark.parametrize("name", sorted(EXPECTED_VERSIONS))
def test_golden_times_relative_to_charge(name: str) -> None:
    profile = parse_profile(fixture_path(name))
    raw = load_alog(fixture_path(name))
    charge_i = raw["timeindex"][0]
    assert charge_i > 0
    assert profile.times_s == [t - raw["timex"][charge_i] for t in raw["timex"]]
    assert profile.times_s[charge_i] == 0.0


@pytest.mark.parametrize("name", sorted(EXPECTED_VERSIONS))
def test_golden_markers_match_timeindex(name: str) -> None:
    profile = parse_profile(fixture_path(name))
    raw = load_alog(fixture_path(name))
    n = len(raw["timex"])
    expected = {
        m for m, slot in SLOT_BY_NAME.items()
        if 0 < raw["timeindex"][slot] < n
    }
    expected.add("TP")
    assert set(profile.markers) == expected
    for m, slot in SLOT_BY_NAME.items():
        if m not in profile.markers:
            continue
        i = raw["timeindex"][slot]
        marker = profile.markers[m]
        assert marker.name == m
        assert marker.time_s == pytest.approx(raw["timex"][i] - raw["timex"][raw["timeindex"][0]])
        assert marker.temp_bt_c == pytest.approx(raw["temp2"][i])
        assert marker.temp_et_c == pytest.approx(raw["temp1"][i])


@pytest.mark.parametrize("name", sorted(EXPECTED_VERSIONS))
def test_golden_tp_is_bt_minimum_between_charge_and_drop(name: str) -> None:
    profile = parse_profile(fixture_path(name))
    raw = load_alog(fixture_path(name))
    ti = raw["timeindex"]
    lo, hi = ti[0], ti[SLOT_BY_NAME["DROP"]]
    tp_i = min(range(lo, hi + 1), key=lambda i: raw["temp2"][i])
    tp = profile.markers["TP"]
    assert tp.temp_bt_c == pytest.approx(raw["temp2"][tp_i])
    assert tp.time_s == pytest.approx(raw["timex"][tp_i] - raw["timex"][lo])


@pytest.mark.parametrize("name", sorted(EXPECTED_VERSIONS))
def test_golden_events_match_specialevents(name: str) -> None:
    profile = parse_profile(fixture_path(name))
    raw = load_alog(fixture_path(name))
    n = len(raw["timex"])
    charge_i = raw["timeindex"][0]
    etypes = [unescape(s) for s in raw.get("etypes", [])]
    expected = []
    for i, code, slider, label in zip(
        raw["specialevents"],
        raw["specialeventstype"],
        raw["specialeventsvalue"],
        raw["specialeventsStrings"],
    ):
        if not 0 <= i < n:
            continue
        expected.append((
            i,
            raw["timex"][i] - raw["timex"][charge_i],
            etypes[code] if 0 <= code < len(etypes) else None,
            float(slider),
            unescape(label),
        ))
    assert len(profile.events) == len(expected)
    got = [
        (e.index, e.time_s, e.type_label, e.slider_value, e.label)
        for e in profile.events
    ]
    assert got == expected


@pytest.mark.parametrize("name", sorted(EXPECTED_VERSIONS))
def test_golden_phases_from_computed(name: str) -> None:
    profile = parse_profile(fixture_path(name))
    raw = load_alog(fixture_path(name))
    computed = raw.get("computed")
    if not isinstance(computed, dict):
        assert profile.phases is None
        assert profile.computed is None
        return
    assert profile.computed == computed
    assert profile.phases == {
        "dry_s": computed.get("dryphasetime"),
        "mid_s": computed.get("midphasetime"),
        "finish_s": computed.get("finishphasetime"),
        "total_s": computed.get("totaltime"),
    }


@pytest.mark.parametrize("name", sorted(EXPECTED_VERSIONS))
def test_golden_ror_matches_reference_definition(name: str) -> None:
    profile = parse_profile(fixture_path(name))
    raw = load_alog(fixture_path(name))
    timex, bt = raw["timex"], raw["temp2"]
    # reference implementation of the documented 15 s trailing-window RoR
    def expected_ror(i: int) -> float | None:
        j = bisect_right(timex, timex[i] - 15.0) - 1
        if j < 0:
            return None
        dt = timex[i] - timex[j]
        if dt <= 0:
            return None
        return (bt[i] - bt[j]) / dt * 60.0

    n = len(timex)
    first_ok = next(i for i in range(n) if expected_ror(i) is not None)
    for i in (first_ok, n // 2, n - 1):
        want = expected_ror(i)
        got = profile.ror_c_per_min[i]
        if want is None:
            assert got is None
        else:
            assert got == pytest.approx(want)


# ---------------------------------------------------------------------------
# model: synthetic profiles
# ---------------------------------------------------------------------------

def test_markers_charge_dry_fcs_drop(tmp_path: Path) -> None:
    ti = [2, 5, 9, 0, 0, 0, 12, 0]
    p = write_alog(tmp_path, synthetic_profile(timeindex=ti))
    markers = parse_profile(p).markers
    assert set(markers) == {"CHARGE", "DRY", "FCs", "DROP", "TP"}
    for name in ("CHARGE", "DRY", "FCs", "DROP"):
        slot = SLOT_BY_NAME[name]
        i = ti[slot]
        assert markers[name].time_s == i - 2.0
        assert markers[name].temp_bt_c == 25.0 + 3.0 * i
        assert markers[name].temp_et_c == 100.0 + 2.0 * i


def test_no_markers_marks_tp_only(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(timeindex=[0] * 8))
    profile = parse_profile(p)
    # no CHARGE -> time base is recording start, only TP is derived
    assert set(profile.markers) == {"TP"}
    assert profile.times_s == [float(i) for i in range(15)]
    assert profile.markers["TP"].time_s == 0.0
    assert profile.markers["TP"].temp_bt_c == 25.0


def test_tp_search_limited_to_charge_drop_range(tmp_path: Path) -> None:
    timex = [float(i * 10) for i in range(10)]
    # global BT minimum at sample 1 (before CHARGE at 3), in-range minimum at 5
    bt = [100.0, 50.0, 100.0, 90.0, 100.0, 80.0, 100.0, 100.0, 110.0, 120.0]
    p = write_alog(tmp_path, {
        "version": "2.4.6",
        "timex": timex,
        "temp1": [200.0] * 10,
        "temp2": bt,
        "timeindex": [3, 0, 7, 0, 0, 0, 8, 0],
    })
    tp = parse_profile(p).markers["TP"]
    assert tp.time_s == 50.0 - 30.0
    assert tp.temp_bt_c == 80.0


def test_events_extraction_and_invalid_indices_dropped(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(
        n=10,
        specialevents=[3, 999, -1, 5, 9],
        specialeventstype=[0, 1, 2, 3, 99],
        specialeventsvalue=[7.0, 8.0, 1.0, 16.0, 2.0],
        specialeventsStrings=["7", "8", "1", "30mBar", "x"],
    ))
    events = parse_profile(p).events
    # index 999 and -1 are invalid; type 99 has no etype label
    assert [e.index for e in events] == [3, 5, 9]
    by_index = {e.index: e for e in events}
    assert by_index[3].type_label == "Air"
    assert by_index[3].slider_value == 7.0
    assert by_index[3].label == "7"
    assert by_index[5].type_label == "Burner"
    assert by_index[5].label == "30mBar"
    assert by_index[9].type_label is None
    for e in events:
        assert e.time_s == float(e.index)


def test_events_with_shared_index_and_escaped_labels(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(
        n=10,
        etypes=["Air", "Tambour", "Vanne", "Br\\xfbleur", "--"],
        specialevents=[4, 4],
        specialeventstype=[0, 3],
        specialeventsvalue=[8.0, 21.0],
        specialeventsStrings=["7", "40mBar"],
    ))
    events = parse_profile(p).events
    assert [e.index for e in events] == [4, 4]
    assert [e.type_label for e in events] == ["Air", "Brûleur"]
    assert [e.time_s for e in events] == [4.0, 4.0]


def test_empty_events(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(
        specialevents=[],
        specialeventstype=[],
        specialeventsvalue=[],
        specialeventsStrings=[],
    ))
    assert parse_profile(p).events == []


def test_unknown_keys_tolerated(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(
        someFutureKey={"nested": [1, 2, {"deep": True}]},
        hash="0" * 64,
        signature="f" * 96,
        bbp_pidKp1=20.0,
        pidScheduleSetpoints=[],
    ))
    profile = parse_profile(p)
    assert len(profile.times_s) == 15
    assert profile.meta.artisan_version == "4.2.0"


def test_bad_samples_dropped(tmp_path: Path) -> None:
    p = write_alog(tmp_path, {
        "version": "2.4.6",
        "timex": [0, 2, 4],
        "temp1": [20.0, "broken", 30.0],
        "temp2": [25.0, 26.0, "broken"],
        "timeindex": [0] * 8,
    })
    profile = parse_profile(p)
    # rows 1 (bad ET) and 2 (bad BT) are dropped entirely
    assert profile.times_s == [0.0]
    assert profile.et_c == [20.0]
    assert profile.bt_c == [25.0]


def test_meta_weights(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(
        weight=[400.0, 354.0, "g"],
        computed={"weight_loss": 11.5},
    ))
    meta = parse_profile(p).meta
    assert meta.green_weight_g == 400.0
    assert meta.roasted_weight_g == 354.0
    assert meta.weight_loss_pct == 11.5


def test_meta_zero_weights_and_weight_loss_100_mean_missing(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(
        weight=[0.0, 0.0, "g"],
        computed={"weight_loss": 100.0},
    ))
    meta = parse_profile(p).meta
    assert meta.green_weight_g is None
    assert meta.roasted_weight_g is None
    assert meta.weight_loss_pct is None


def test_meta_defect_flags_coercion(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(
        heavyFC=True, lowFC=0, oily="not a bool",
    ))
    flags = parse_profile(p).meta.defect_flags
    assert flags is not None
    assert flags["heavyFC"] is True
    assert flags["lowFC"] is False
    assert flags["oily"] is None
    assert flags["tipping"] is None


def test_meta_flavors(tmp_path: Path) -> None:
    p = write_alog(tmp_path, synthetic_profile(
        flavorlabels=["apricot", "floral"],
        flavors=[8.0, 7.5, "bad"],
    ))
    meta = parse_profile(p).meta
    assert meta.flavorlabels == ["apricot", "floral"]
    assert meta.flavors == [8.0, 7.5]


def test_empty_dict_parses_to_empty_profile(tmp_path: Path) -> None:
    p = write_alog(tmp_path, {})
    profile = parse_profile(p)
    assert profile.times_s == []
    assert profile.bt_c == []
    assert profile.et_c == []
    assert profile.ror_c_per_min == []
    assert profile.markers == {}
    assert profile.events == []
    assert profile.phases is None
    assert profile.meta.title is None


def test_parse_profile_raises_on_malformed_file(tmp_path: Path) -> None:
    p = tmp_path / "bad.alog"
    p.write_text("{'version': '2.4.6', 'timex': [1, 2", encoding="ascii")
    with pytest.raises(AlogParseError):
        parse_profile(p)


# ---------------------------------------------------------------------------
# metrics: RoR
# ---------------------------------------------------------------------------

def test_ror_empty_input() -> None:
    assert ror([], []) == []


def test_ror_constant_curve_zero_after_first_window() -> None:
    times = [float(2 * i) for i in range(10)]
    bt = [150.0] * 10
    out = ror(bt, times)
    # 15 s window never reaches back for the first 8 samples
    assert out[:8] == [None] * 8
    assert out[8:] == [0.0, 0.0]


def test_ror_linear_ramp() -> None:
    times = [float(2 * i) for i in range(31)]
    bt = [20.0 + 0.1 * t for t in times]
    out = ror(bt, times)
    assert out[:8] == [None] * 8
    assert all(v == pytest.approx(0.1 * 60.0) for v in out[8:])


def test_ror_non_uniform_spacing() -> None:
    # hand-computed: only i=3 has a sample at least 15 s behind it
    out = ror([100.0, 101.0, 102.0, 108.0], [0.0, 5.0, 10.0, 40.0])
    assert out == [None, None, None, pytest.approx(12.0)]


def test_ror_negative_for_cooling_curve() -> None:
    out = ror([200.0, 190.0], [0.0, 60.0], window_s=30.0)
    assert out == [None, pytest.approx(-10.0)]


def test_ror_none_bt_propagates() -> None:
    out = ror([100.0, None, 110.0, 120.0], [0.0, 10.0, 20.0, 30.0], window_s=5.0)
    # i=1: bt None; i=2 references sample 1 (None bt); i=3 references sample 2
    assert out == [None, None, None, pytest.approx(60.0)]
    out2 = ror([100.0, 105.0, None, 120.0], [0.0, 10.0, 20.0, 30.0], window_s=5.0)
    assert out2[1] == pytest.approx(30.0)
    assert out2[2] is None
    assert out2[3] is None


def test_ror_non_positive_window_all_none() -> None:
    assert ror([1.0, 2.0], [0.0, 1.0], window_s=0.0) == [None, None]
    assert ror([1.0, 2.0], [0.0, 1.0], window_s=-1.0) == [None, None]


def test_ror_length_mismatch_truncated_to_shorter() -> None:
    out = ror([1.0, 2.0, 3.0], [0.0, 2.0, 4.0, 6.0, 8.0], window_s=2.0)
    assert len(out) == 3
    assert out == [None, pytest.approx(30.0), pytest.approx(30.0)]


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

def test_build_index_over_fixture_dir(tmp_path: Path) -> None:
    db = tmp_path / "index.sqlite"
    n = build_index(FIXTURES_DIR, db)
    assert n == len(EXPECTED_VERSIONS)
    rows = list_roasts(db)
    assert len(rows) == n
    assert all(r["parse_ok"] == 1 for r in rows)
    assert all(r["error_msg"] is None for r in rows)
    for row in rows:
        raw = load_alog(fixture_path(row["source_file"]))
        assert row["roast_id"] == raw["roastUUID"]
        assert row["roast_isodate"] == unescape(raw["roastisodate"])
        assert row["title"] == unescape(raw["title"])
        # every fixture has CHARGE/FCs/DROP marked
        assert row["drop_bt_c"] is not None
        assert row["fcs_time_s"] is not None
        assert row["total_time_s"] is not None


def test_build_index_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "index.sqlite"
    assert build_index(FIXTURES_DIR, db) == len(EXPECTED_VERSIONS)
    first = list_roasts(db)
    assert build_index(FIXTURES_DIR, db) == len(EXPECTED_VERSIONS)
    second = list_roasts(db)
    assert first == second
    assert len({r["roast_id"] for r in second}) == len(second)


def test_build_index_malformed_file_does_not_abort_scan(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "bad.alog").write_text("{'version': '2.4.6'", encoding="ascii")
    good_bytes = fixture_path("v2.10.4_2024-08-03.alog").read_bytes()
    (logs / "good.alog").write_bytes(good_bytes)
    db = tmp_path / "index.sqlite"
    assert build_index(logs, db) == 2
    rows = {r["source_file"]: r for r in list_roasts(db)}
    assert rows["bad.alog"]["parse_ok"] == 0
    assert rows["bad.alog"]["error_msg"] is not None
    assert rows["good.alog"]["parse_ok"] == 1
    assert rows["good.alog"]["drop_bt_c"] is not None


def test_build_index_creates_missing_parent_dirs(tmp_path: Path) -> None:
    db = tmp_path / "deep" / "nested" / "index.sqlite"
    assert build_index(FIXTURES_DIR, db) == len(EXPECTED_VERSIONS)
    assert db.exists()


def test_build_index_roast_id_falls_back_to_filename_hash(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    p = logs / "no_uuid.alog"
    p.write_text(repr(synthetic_profile(n=5)), encoding="ascii")
    db = tmp_path / "index.sqlite"
    build_index(logs, db)
    (row,) = list_roasts(db)
    expected_id = hashlib.sha256(p.name.encode("utf-8")).hexdigest()[:16]
    assert row["roast_id"] == expected_id


def test_list_roasts_ordered_by_date_then_file(tmp_path: Path) -> None:
    db = tmp_path / "index.sqlite"
    build_index(FIXTURES_DIR, db)
    rows = list_roasts(db)
    dates = [r["roast_isodate"] for r in rows]
    assert dates == sorted(dates)
    assert [r["source_file"] for r in rows] == sorted(
        EXPECTED_VERSIONS,
        key=lambda name: (load_alog(fixture_path(name))["roastisodate"], name),
    )
