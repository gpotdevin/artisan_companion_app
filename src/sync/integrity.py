"""Artisan 4.2 profile integrity: int-to-float conversion and SHA256 hashing.

Artisan v4.2+ files include a 'hash' field that must be computed as:
    sha256(json.dumps(rec_int_to_float(profile_minus_hash), 
                      sort_keys=True, ensure_ascii=True, separators=(',', ':')))
                  .hexdigest()

The signature field (Ed25519 over version+revision+artisan_os) is kept
untouched during native sync, as it is content-independent.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def rec_int_to_float(data: Any) -> Any:
    """Recursively convert every int (including bool) to float in a data structure.
    
    Artisan's hash computation uses this transformation on the profile dict
    before JSON serialization. This is applied recursively to dicts and lists.
    
    Examples:
        >>> rec_int_to_float({"a": 1, "b": True, "c": [1, 2.5]})
        {'a': 1.0, 'b': 1.0, 'c': [1.0, 2.5]}
        >>> rec_int_to_float("hello")
        'hello'
    """
    if isinstance(data, bool):
        # bool is a subclass of int, must come first
        return float(data)
    if isinstance(data, int):
        return float(data)
    if isinstance(data, dict):
        return {k: rec_int_to_float(v) for k, v in data.items()}
    if isinstance(data, list):
        return [rec_int_to_float(item) for item in data]
    # float, str, and other types pass through unchanged
    return data


def compute_profile_hash(profile: dict[str, Any]) -> str:
    """Compute the SHA256 profile hash as Artisan 4.2+ expects.
    
    The hash is computed over the profile dict with 'hash' removed,
    after converting all ints (including bools) to floats via rec_int_to_float,
    then JSON-serialized with sorted keys, ASCII-only, compact separators.
    
    This is the value that must be written to profile['hash'] after
    modifying the profile, to avoid Artisan's "Modified Artisan profile"
    warning on load.
    """
    profile_no_hash = {k: v for k, v in profile.items() if k != "hash"}
    normalized = rec_int_to_float(profile_no_hash)
    json_bytes = json.dumps(
        normalized, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(json_bytes).hexdigest()


def verify_profile_hash(profile: dict[str, Any]) -> bool:
    """Verify that profile['hash'] matches the computed hash.
    
    Returns True if the stored hash (if present) matches the computed
    hash over the profile minus the 'hash' key itself.
    Returns False if 'hash' is missing or does not match.
    """
    stored_hash = profile.get("hash")
    if stored_hash is None:
        return False
    computed = compute_profile_hash(profile)
    return stored_hash == computed


# 210 keys of Artisan 4.2.0 `ProfileData` (disassembled from the bundled `atypes.pyc`
# of the user's official artisan.exe build, revision 9334ed7), plus `oversampling`
# (not in the 4.2.0 schema but present in real v2.4.6 files; kept so pre-4.2 syncs
# are not falsely refused). The set is used only to refuse files with unknown keys.
PROFILE_DATA_KEYS: frozenset[str] = frozenset([
    "BlendList",
    "alarmaction",
    "alarmbeep",
    "alarmcond",
    "alarmflag",
    "alarmguard",
    "alarmnegguard",
    "alarmoffset",
    "alarmsetlabel",
    "alarmsource",
    "alarmstrings",
    "alarmtemperature",
    "alarmtime",
    "ambientTemp",
    "ambient_humidity",
    "ambient_pressure",
    "anno_positions",
    "artisan_os",
    "artisan_os_arch",
    "artisan_os_version",
    "backgroundUUID",
    "backgroundpath",
    "bbp_begin",
    "bbp_drop_to_end",
    "bbp_dropbt",
    "bbp_dropet",
    "bbp_dropevents",
    "bbp_endevents",
    "bbp_endroast_epoch_msec",
    "bbp_time_added_from_prev",
    "beans",
    "beansize",
    "beansize_max",
    "beansize_min",
    "betweenbatchDuration",
    "betweenbatch_after_preheat",
    "betweenbatchenergies",
    "biogas_co2_reduction",
    "build",
    "co2kg_per_btu",
    "color_system",
    "computed",
    "coolingDuration",
    "coolingenergies",
    "cuppingnotes",
    "darkCut",
    "default_etypes",
    "default_etypes_set",
    "defects_weight",
    "density",
    "density_roasted",
    "devices",
    "divots",
    "drops",
    "drumspeed",
    "electricEnergyMix",
    "elevation",
    "end_weight_est",
    "etypes",
    "externaloutprogram",
    "externalprogram",
    "extraCurveVisibility1",
    "extraCurveVisibility2",
    "extraDelta1",
    "extraDelta2",
    "extraFill1",
    "extraFill2",
    "extraLCDvisibility1",
    "extraLCDvisibility2",
    "extraNoneTempHint1",
    "extraNoneTempHint2",
    "extradevicecolor1",
    "extradevicecolor2",
    "extradevices",
    "extradrawstyles1",
    "extradrawstyles2",
    "extralinestyles1",
    "extralinestyles2",
    "extralinewidths1",
    "extralinewidths2",
    "extramarkers1",
    "extramarkers2",
    "extramarkersizes1",
    "extramarkersizes2",
    "extramathexpression1",
    "extramathexpression2",
    "extraname1",
    "extraname2",
    "extratemp1",
    "extratemp2",
    "extratimex",
    "flag_positions",
    "flavoraspect",
    "flavorlabels",
    "flavors",
    "flavors_total_correction",
    "flavorstartangle",
    "gain_scheduling",
    "gain_scheduling_on_SV",
    "gain_scheduling_quadratic",
    "gasMix",
    "greens_temp",
    "ground_color",
    "hash",
    "heavyFC",
    "legendloc_pos",
    "lightCut",
    "load_etypes",
    "loadevent_hundpcts",
    "loadevent_zeropcts",
    "loadlabels",
    "loadratings",
    "locale",
    "lowFC",
    "machinesetup",
    "meterfuels",
    "meterlabels",
    "meterreads",
    "metersources",
    "meterunits",
    "mode",
    "moisture_greens",
    "moisture_roasted",
    "oily",
    "operator",
    "organization",
    "oversampling",
    "phases",
    "pidDsetpointWeight",
    "pidKd",
    "pidKd1",
    "pidKd2",
    "pidKi",
    "pidKi1",
    "pidKi2",
    "pidKp",
    "pidKp1",
    "pidKp2",
    "pidPsetpointWeight",
    "pidSchedule0",
    "pidSchedule1",
    "pidSchedule2",
    "pidSource",
    "plus_blend_label",
    "plus_blend_spec",
    "plus_blend_spec_labels",
    "plus_coffee",
    "plus_coffee_label",
    "plus_store",
    "plus_store_label",
    "plus_sync_record_hash",
    "preheatDuration",
    "preheatenergies",
    "presssure_percents",
    "ramp_lookahead",
    "ratingunits",
    "recording_build",
    "recording_revision",
    "recording_version",
    "revision",
    "roastUUID",
    "roastbatchnr",
    "roastbatchpos",
    "roastbatchprefix",
    "roastdate",
    "roastepoch",
    "roasterheating",
    "roastersize",
    "roastertype",
    "roastingnotes",
    "roastisodate",
    "roasttime",
    "roasttzoffset",
    "samplinginterval",
    "scheduleDate",
    "scheduleID",
    "scorching",
    "signature",
    "sourcetypes",
    "specialevents",
    "specialeventsStrings",
    "specialeventstype",
    "specialeventsvalue",
    "svActions",
    "svBeeps",
    "svDescriptions",
    "svLabel",
    "svLookahead",
    "svRamps",
    "svSoaks",
    "svValues",
    "temp1",
    "temp2",
    "timeindex",
    "timex",
    "tipping",
    "title",
    "uneven",
    "version",
    "viewerMode",
    "volume",
    "volumeCalcWeightIn",
    "volumeCalcWeightOut",
    "weight",
    "whole_color",
    "xmax",
    "xmin",
    "ymax",
    "ymin",
    "zmax",
    "zmin",
])
