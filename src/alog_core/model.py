"""Typed profile model for Artisan .alog roasts.

Composes the raw pydump loader (:mod:`alog_core.parser`), this dataclass
model and the derived metrics (:mod:`alog_core.metrics`) into
:func:`parse_profile`. All optional source keys are read with ``.get()``
and coerced defensively: key sets differ across Artisan 2.4.6 - 4.2.0 and
the parser must tolerate any of them, plus future versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .metrics import ror
from .parser import AlogParseError, PathLike, load_alog, unescape

_MARKER_SLOTS: dict[str, int] = {
    "CHARGE": 0,
    "DRY": 1,
    "FCs": 2,
    "DROP": 6,
    "COOL": 7,
}

_DEFECT_FLAG_KEYS: tuple[str, ...] = (
    "heavyFC", "lowFC", "lightCut", "darkCut", "drops",
    "oily", "uneven", "tipping", "scorching", "divots",
)


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------

def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> Optional[str]:
    return unescape(value) if isinstance(value, str) else None


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoastMeta:
    """Roast metadata from the top-level keys; every field is optional."""

    title: Optional[str] = None
    beans: Optional[str] = None
    roast_uuid: Optional[str] = None
    roast_isodate: Optional[str] = None
    roast_time: Optional[str] = None
    roast_epoch: Optional[int] = None
    roast_tzoffset_s: Optional[int] = None
    green_weight_g: Optional[float] = None
    roasted_weight_g: Optional[float] = None
    weight_loss_pct: Optional[float] = None
    roastertype: Optional[str] = None
    machinesetup: Optional[str] = None
    ambient_temp_c: Optional[float] = None
    artisan_version: Optional[str] = None
    recording_version: Optional[str] = None
    mode: Optional[str] = None
    sampling_interval_s: Optional[float] = None
    cuppingnotes: Optional[str] = None
    roastingnotes: Optional[str] = None
    flavorlabels: Optional[list[str]] = None
    flavors: Optional[list[float]] = None
    defect_flags: Optional[dict[str, Optional[bool]]] = None


@dataclass(frozen=True)
class Marker:
    """A roast marker at a sample index (CHARGE/DRY/FCs/DROP/COOL/TP).

    ``temp_bt_c``/``temp_et_c`` are the probe readings at that sample.
    """

    name: str
    time_s: float
    temp_bt_c: Optional[float] = None
    temp_et_c: Optional[float] = None


@dataclass(frozen=True)
class RoastEvent:
    """One special event (slider/button change) on the curve.

    ``slider_value`` is Artisan's 0-25 slider position, not the physical
    value; the physical value is the user-typed ``label``
    (``specialeventsStrings``, e.g. ``"30mBar"``). ``index`` is the sample
    index into the profile's time series.
    """

    time_s: float
    index: int
    type_label: Optional[str] = None
    slider_value: Optional[float] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class RoastProfile:
    """A parsed roast: metadata, curves, markers, events, derived metrics.

    ``times_s`` are roast-relative seconds (``timex[i] - timex[CHARGE]``);
    samples recorded before CHARGE are negative. ``ror_c_per_min`` is the
    BT rate of rise, same length as ``times_s`` (``None`` where not
    computable). ``markers`` holds only the markers present in the file
    (plus derived ``TP``); ``events`` excludes events with invalid sample
    indices. ``phases`` carries the phase durations from ``computed``
    when that dict is present, else ``None``.
    """

    meta: RoastMeta = field(default_factory=RoastMeta)
    times_s: list[float] = field(default_factory=list)
    bt_c: list[float] = field(default_factory=list)
    et_c: list[float] = field(default_factory=list)
    ror_c_per_min: list[Optional[float]] = field(default_factory=list)
    markers: dict[str, Marker] = field(default_factory=dict)
    events: list[RoastEvent] = field(default_factory=list)
    phases: Optional[dict[str, Optional[float]]] = None
    computed: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Profile construction
# ---------------------------------------------------------------------------

def _coerced_series(d: dict[str, Any]) -> tuple[list[float], list[float], list[float]]:
    """Return parallel (times, ET, BT) float lists, dropping bad samples."""
    times: list[float] = []
    et_c: list[float] = []
    bt_c: list[float] = []
    rows = zip(
        _as_list(d.get("timex")),
        _as_list(d.get("temp1")),
        _as_list(d.get("temp2")),
    )
    for t, et, bt in rows:
        ft = _as_float(t)
        fet = _as_float(et)
        fbt = _as_float(bt)
        if ft is None or fet is None or fbt is None:
            continue
        times.append(ft)
        et_c.append(fet)
        bt_c.append(fbt)
    return times, et_c, bt_c


def _marker_index(
    timeindex: list[Any], slot: int, n_samples: int
) -> Optional[int]:
    """Sample index for a ``timeindex`` slot; 0/-1 mean "not marked"."""
    if slot >= len(timeindex):
        return None
    v = _as_int(timeindex[slot])
    if v is None or v <= 0 or v >= n_samples:
        return None
    return v


def _build_markers(
    timeindex: list[Any],
    times_s: list[float],
    bt_c: list[float],
    et_c: list[float],
) -> dict[str, Marker]:
    n = len(times_s)
    markers: dict[str, Marker] = {}
    for name, slot in _MARKER_SLOTS.items():
        i = _marker_index(timeindex, slot, n)
        if i is None:
            continue
        markers[name] = Marker(
            name=name, time_s=times_s[i], temp_bt_c=bt_c[i], temp_et_c=et_c[i]
        )
    return markers


def _build_events(
    d: dict[str, Any], times_s: list[float]
) -> list[RoastEvent]:
    """Build the event list; events with invalid sample indices are dropped."""
    etypes = _as_list(d.get("etypes"))
    events: list[RoastEvent] = []
    rows = zip(
        _as_list(d.get("specialevents")),
        _as_list(d.get("specialeventstype")),
        _as_list(d.get("specialeventsvalue")),
        _as_list(d.get("specialeventsStrings")),
    )
    for raw_index, type_code, slider, label in rows:
        i = _as_int(raw_index)
        if i is None or i < 0 or i >= len(times_s):
            continue
        type_label = None
        code = _as_int(type_code)
        if code is not None and 0 <= code < len(etypes):
            type_label = _as_str(etypes[code])
        events.append(
            RoastEvent(
                time_s=times_s[i],
                index=i,
                type_label=type_label,
                slider_value=_as_float(slider),
                label=_as_str(label),
            )
        )
    return events


def _build_meta(d: dict[str, Any], computed: Optional[dict[str, Any]]) -> RoastMeta:
    weight = _as_list(d.get("weight"))
    green = _as_float(weight[0]) if len(weight) >= 1 else None
    roasted = _as_float(weight[1]) if len(weight) >= 2 else None
    # Artisan writes 0 for "not entered".
    green = green if green else None
    roasted = roasted if roasted else None

    # computed weight_loss is 100.0 when no roasted weight was entered.
    weight_loss = _as_float(computed.get("weight_loss")) if computed else None
    if weight_loss is not None and weight_loss >= 100.0:
        weight_loss = None

    uuid = d.get("roastUUID")
    ambient = _as_float(d.get("ambientTemp"))

    return RoastMeta(
        title=_as_str(d.get("title")),
        beans=_as_str(d.get("beans")),
        roast_uuid=uuid if isinstance(uuid, str) and uuid else None,
        roast_isodate=_as_str(d.get("roastisodate")),
        roast_time=_as_str(d.get("roasttime")),
        roast_epoch=_as_int(d.get("roastepoch")),
        roast_tzoffset_s=_as_int(d.get("roasttzoffset")),
        green_weight_g=green,
        roasted_weight_g=roasted,
        weight_loss_pct=weight_loss,
        roastertype=_as_str(d.get("roastertype")),
        machinesetup=_as_str(d.get("machinesetup")),
        ambient_temp_c=ambient,
        artisan_version=_as_str(d.get("version")),
        recording_version=_as_str(d.get("recording_version")),
        mode=_as_str(d.get("mode")),
        sampling_interval_s=_as_float(d.get("samplinginterval")),
        cuppingnotes=_as_str(d.get("cuppingnotes")),
        roastingnotes=_as_str(d.get("roastingnotes")),
        flavorlabels=[
            s for s in (_as_str(v) for v in _as_list(d.get("flavorlabels")))
            if s is not None
        ],
        flavors=[
            v for v in (_as_float(x) for x in _as_list(d.get("flavors")))
            if v is not None
        ],
        defect_flags={
            key: (
                bool(d.get(key))
                if isinstance(d.get(key), (bool, int)) else None
            )
            for key in _DEFECT_FLAG_KEYS
        },
    )


def _build_profile(d: dict[str, Any]) -> RoastProfile:
    """Build a RoastProfile from a parsed pydump dict (never mutated)."""
    times, et_c, bt_c = _coerced_series(d)
    n = len(times)

    timeindex = _as_list(d.get("timeindex"))
    charge_i = _marker_index(timeindex, _MARKER_SLOTS["CHARGE"], n)

    # Roast-relative time base: CHARGE sample when marked, else recording
    # start (t_rel == timex); the CHARGE marker is absent in that case.
    t0 = times[charge_i] if charge_i is not None else 0.0
    times_s = [t - t0 for t in times]

    markers = _build_markers(timeindex, times_s, bt_c, et_c)

    # TP: BT minimum between CHARGE and DROP when both are marked,
    # else BT minimum over the whole curve.
    if n:
        drop_i = _marker_index(timeindex, _MARKER_SLOTS["DROP"], n)
        if charge_i is not None and drop_i is not None and charge_i <= drop_i:
            lo, hi = charge_i, drop_i
        else:
            lo, hi = 0, n - 1
        tp_i = min(range(lo, hi + 1), key=lambda i: bt_c[i])
        markers["TP"] = Marker(
            name="TP",
            time_s=times_s[tp_i],
            temp_bt_c=bt_c[tp_i],
            temp_et_c=et_c[tp_i],
        )

    computed = d.get("computed")
    computed = computed if isinstance(computed, dict) else None
    phases = None
    if computed is not None:
        phases = {
            "dry_s": _as_float(computed.get("dryphasetime")),
            "mid_s": _as_float(computed.get("midphasetime")),
            "finish_s": _as_float(computed.get("finishphasetime")),
            "total_s": _as_float(computed.get("totaltime")),
        }

    return RoastProfile(
        meta=_build_meta(d, computed),
        times_s=times_s,
        bt_c=bt_c,
        et_c=et_c,
        ror_c_per_min=ror(bt_c, times_s),
        markers=markers,
        events=_build_events(d, times_s),
        phases=phases,
        computed=computed,
    )


def parse_profile(path: PathLike) -> RoastProfile:
    """Parse an .alog file into a :class:`RoastProfile`.

    Combines the raw loader, the typed model and the derived metrics
    (RoR). Raises :class:`AlogParseError` with the filename in the
    message if the file cannot be read or parsed.
    """
    d = load_alog(path)
    try:
        return _build_profile(d)
    except Exception as exc:
        raise AlogParseError(f"{path}: profile build failed ({exc!r})") from exc
