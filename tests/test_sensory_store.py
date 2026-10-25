"""Tests for the sensory store (M2a): CRUD, schema, atomicity, index."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from store import (
    DEFAULT_RADAR_LABELS,
    DEFECT_KEYS,
    SCORE_KEYS,
    SCHEMA_VERSION,
    SensoryStore,
    SensoryStoreError,
)

UUID_A = "41bc74340a464d98a8156045b5bfc495"
UUID_B = "0123456789abcdef0123456789abcdef"
UUID_C = "fedcba9876543210fedcba9876543210"

FULL_SCORES = {
    "fragrance_aroma": 8.0, "flavor": 8.5, "aftertaste": 7.5,
    "acidity": 8.5, "body": 7.0, "balance": 8.0,
    "uniformity": 10.0, "clean_cup": 10.0, "sweetness": 8.0,
    "overall": 8.5, "defects": 0,
}
# sum of the ten attributes minus the penalty
EXPECTED_TOTAL = 84.0

ROAST_REF = {"file": "Abricot 5_24-08-03_2018.alog", "date": "2024-08-03"}


@pytest.fixture
def store(tmp_path: Path) -> SensoryStore:
    s = SensoryStore(tmp_path / "sensory")
    yield s
    s.close()


def make_cupping(date: str = "2024-08-05", **overrides) -> dict:
    cupping = {
        "date": date,
        "scores": dict(FULL_SCORES),
        "descriptors": ["apricot", "stone fruit", "black tea", "floral"],
        "notes": "Very vibrant, expected acidity came through.",
    }
    cupping.update(overrides)
    return cupping


def annotate(store: SensoryStore, uuid: str, ref: dict | None = None) -> dict:
    """Create a record and add one full cupping to it."""
    record = store.create(uuid, ref)
    return store.add_cupping(uuid, make_cupping())


# ---------------------------------------------------------------------------
# Record-level CRUD
# ---------------------------------------------------------------------------

def test_get_missing_returns_none(store: SensoryStore):
    assert store.get(UUID_A) is None


def test_create_writes_sidecar_and_get_round_trips(store: SensoryStore, tmp_path: Path):
    record = store.create(UUID_A, ROAST_REF)
    assert record["schema_version"] == SCHEMA_VERSION
    assert record["roast_uuid"] == UUID_A
    assert record["roast_ref"] == ROAST_REF
    assert record["cuppings"] == []
    assert record["media"] == []

    sidecar = tmp_path / "sensory" / f"{UUID_A}.json"
    assert sidecar.is_file()
    on_disk = json.loads(sidecar.read_text(encoding="utf-8"))
    assert on_disk == record
    assert store.get(UUID_A) == record


def test_create_existing_raises(store: SensoryStore):
    store.create(UUID_A)
    with pytest.raises(SensoryStoreError, match="already exists"):
        store.create(UUID_A)


def test_get_or_create_creates_then_returns(store: SensoryStore):
    assert store.get_or_create(UUID_A, ROAST_REF)["roast_uuid"] == UUID_A
    again = store.get_or_create(UUID_A)
    assert again["roast_ref"] == ROAST_REF


def test_delete_removes_record_and_index_rows(store: SensoryStore, tmp_path: Path):
    annotate(store, UUID_A, ROAST_REF)
    assert store.delete(UUID_A) is True
    assert not (tmp_path / "sensory" / f"{UUID_A}.json").exists()
    assert store.get(UUID_A) is None
    assert store.search() == []
    assert store.delete(UUID_A) is False


def test_invalid_uuids_rejected(store: SensoryStore):
    for bad in ("", "../escape", "a/b", "sub dir", 123, None, "x" * 65):
        with pytest.raises(SensoryStoreError):
            store.create(bad)


def test_update_replaces_and_merges_sections(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)
    record = store.update(
        UUID_A,
        roast_ref={"date": "2024-08-10"},  # file must survive the merge
        defects_observed={"tipping": True},
        media=[{"kind": "photo", "path": "../photos/bag.jpg"}],
    )
    assert record["roast_ref"] == {
        "file": ROAST_REF["file"], "date": "2024-08-10",
    }
    assert record["defects_observed"]["tipping"] is True
    assert record["defects_observed"]["scorching"] is False
    assert record["media"] == [{"kind": "photo", "path": "../photos/bag.jpg"}]


def test_update_missing_record_raises(store: SensoryStore):
    with pytest.raises(SensoryStoreError, match="no sensory record"):
        store.update(UUID_A, media=[])


# ---------------------------------------------------------------------------
# Schema v1
# ---------------------------------------------------------------------------

def test_new_record_matches_schema(store: SensoryStore):
    record = store.create(UUID_A, ROAST_REF)
    assert set(record) == {
        "schema_version", "roast_uuid", "roast_ref", "cuppings",
        "radar", "defects_observed", "native_sync", "media",
    }
    assert record["radar"]["labels"] == list(DEFAULT_RADAR_LABELS)
    assert record["radar"]["values"] == []
    assert record["defects_observed"] == {key: False for key in DEFECT_KEYS}
    assert record["native_sync"] == {"last_synced": None, "fields": []}


def test_record_json_matches_plan_example_shape(store: SensoryStore, tmp_path: Path):
    record = annotate(store, UUID_A, ROAST_REF)
    store.update_radar(
        UUID_A,
        values=[8.5, 7.5, 10.0, 7.0, 8.0, 8.0, 8.5, 8.0, 7.0],
    )
    store.update(UUID_A, defects_observed={"tipping": False, "scorching": False})
    store.set_native_sync(UUID_A, ["radar", "cuppingnotes"])
    store.update(UUID_A, media=[{"kind": "photo", "path": "../photos/abricot5_bag.jpg"}])

    on_disk = json.loads(
        (tmp_path / "sensory" / f"{UUID_A}.json").read_text(encoding="utf-8")
    )
    assert on_disk["schema_version"] == 1
    assert on_disk["roast_uuid"] == UUID_A
    assert on_disk["roast_ref"]["file"] == ROAST_REF["file"]
    cupping = on_disk["cuppings"][0]
    assert set(cupping) == {
        "date", "days_after_roast", "scores", "descriptors", "notes",
    }
    assert set(cupping["scores"]) == set(SCORE_KEYS) | {"defects", "total"}
    assert cupping["descriptors"] == [
        "apricot", "stone fruit", "black tea", "floral",
    ]
    assert on_disk["radar"]["values"] == [8.5, 7.5, 10.0, 7.0, 8.0, 8.0, 8.5, 8.0, 7.0]
    assert on_disk["defects_observed"]["tipping"] is False
    assert on_disk["native_sync"]["fields"] == ["radar", "cuppingnotes"]
    assert on_disk["media"] == [
        {"kind": "photo", "path": "../photos/abricot5_bag.jpg"},
    ]


def test_unknown_keys_and_sections_normalized_on_load(store: SensoryStore, tmp_path: Path):
    store.create(UUID_A, ROAST_REF)
    sidecar = tmp_path / "sensory" / f"{UUID_A}.json"
    raw = json.loads(sidecar.read_text(encoding="utf-8"))
    raw["future_field"] = {"x": 1}
    raw["cuppings"] = [{"date": "2024-08-05", "mystery": True, "scores": {"flavor": 9.0}}]
    raw["defects_observed"]["unknown_defect"] = True
    sidecar.write_text(json.dumps(raw), encoding="utf-8")

    record = store.get(UUID_A)
    assert "future_field" not in record
    assert "mystery" not in record["cuppings"][0]
    assert "unknown_defect" not in record["defects_observed"]
    assert record["cuppings"][0]["scores"]["flavor"] == 9.0


def test_wrong_schema_version_rejected(store: SensoryStore, tmp_path: Path):
    store.create(UUID_A)
    sidecar = tmp_path / "sensory" / f"{UUID_A}.json"
    raw = json.loads(sidecar.read_text(encoding="utf-8"))
    raw["schema_version"] = 2
    sidecar.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(SensoryStoreError, match="schema_version"):
        store.get(UUID_A)


def test_uuid_mismatch_rejected(store: SensoryStore, tmp_path: Path):
    sidecar = tmp_path / "sensory" / f"{UUID_A}.json"
    sidecar.write_text(json.dumps({"schema_version": 1, "roast_uuid": UUID_B}),
                       encoding="utf-8")
    with pytest.raises(SensoryStoreError, match="roast_uuid"):
        store.get(UUID_A)


def test_corrupt_sidecar_raises_on_get(store: SensoryStore, tmp_path: Path):
    (tmp_path / "sensory" / f"{UUID_A}.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(SensoryStoreError, match="cannot read sidecar"):
        store.get(UUID_A)


# ---------------------------------------------------------------------------
# Cupping sessions and derived fields
# ---------------------------------------------------------------------------

def test_add_cupping_computes_days_after_roast_and_total(store: SensoryStore):
    record = annotate(store, UUID_A, ROAST_REF)
    cupping = record["cuppings"][0]
    assert cupping["date"] == "2024-08-05"
    assert cupping["days_after_roast"] == 2
    assert cupping["scores"]["total"] == EXPECTED_TOTAL


def test_days_after_roast_is_none_without_roast_date(store: SensoryStore):
    record = store.create(UUID_A)  # no roast date known
    record = store.add_cupping(UUID_A, make_cupping())
    assert record["cuppings"][0]["days_after_roast"] is None


def test_days_after_roast_recomputed_when_roast_date_changes(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)
    record = store.update(UUID_A, roast_ref={"date": "2024-08-04"})
    assert record["cuppings"][0]["days_after_roast"] == 1


def test_days_after_roast_never_stored_inconsistently(store: SensoryStore, tmp_path: Path):
    annotate(store, UUID_A, ROAST_REF)
    sidecar = tmp_path / "sensory" / f"{UUID_A}.json"
    raw = json.loads(sidecar.read_text(encoding="utf-8"))
    raw["cuppings"][0]["days_after_roast"] = 999  # hand-edit lies
    raw["cuppings"][0]["scores"]["total"] = -1.0
    sidecar.write_text(json.dumps(raw), encoding="utf-8")

    record = store.get(UUID_A)
    assert record["cuppings"][0]["days_after_roast"] == 2
    assert record["cuppings"][0]["scores"]["total"] == EXPECTED_TOTAL


def test_register_roast_backfills_ref_and_days(store: SensoryStore):
    record = store.create(UUID_A)
    record = store.add_cupping(UUID_A, make_cupping())
    assert record["cuppings"][0]["days_after_roast"] is None

    store.register_roast(UUID_A, source_file=ROAST_REF["file"], roast_date=ROAST_REF["date"])
    record = store.get(UUID_A)
    assert record["roast_ref"] == ROAST_REF
    assert record["cuppings"][0]["days_after_roast"] == 2


def test_cupping_date_required_and_validated(store: SensoryStore):
    store.create(UUID_A, ROAST_REF)
    for bad_date in ("05-08-2024", "2024-13-01", None):
        with pytest.raises(SensoryStoreError, match="cupping.date"):
            store.add_cupping(UUID_A, make_cupping(date=bad_date))
    missing = make_cupping()
    del missing["date"]
    with pytest.raises(SensoryStoreError, match="cupping.date"):
        store.add_cupping(UUID_A, missing)


def test_scores_validated(store: SensoryStore):
    store.create(UUID_A, ROAST_REF)
    with pytest.raises(SensoryStoreError, match="scores.flavor"):
        store.add_cupping(UUID_A, make_cupping(scores={**FULL_SCORES, "flavor": 11.0}))
    with pytest.raises(SensoryStoreError, match="scores.acidity"):
        store.add_cupping(UUID_A, make_cupping(scores={**FULL_SCORES, "acidity": "high"}))
    with pytest.raises(SensoryStoreError, match="scores.defects"):
        store.add_cupping(UUID_A, make_cupping(scores={**FULL_SCORES, "defects": -2}))


def test_total_is_derived_not_user_writable(store: SensoryStore):
    store.create(UUID_A, ROAST_REF)
    record = store.add_cupping(
        UUID_A, make_cupping(scores={**FULL_SCORES, "total": 100.0})
    )
    assert record["cuppings"][0]["scores"]["total"] == EXPECTED_TOTAL


def test_partial_scores_kept_with_partial_total(store: SensoryStore):
    store.create(UUID_A, ROAST_REF)
    record = store.add_cupping(
        UUID_A, make_cupping(scores={"flavor": 8.5, "acidity": 8.0})
    )
    scores = record["cuppings"][0]["scores"]
    assert scores == {"flavor": 8.5, "acidity": 8.0, "total": 16.5}


def test_edit_cupping_merges_and_recomputes(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)
    record = store.edit_cupping(
        UUID_A, 0,
        {"date": "2024-08-09", "scores": {"flavor": 9.0}, "notes": "Settled."},
    )
    cupping = record["cuppings"][0]
    assert cupping["date"] == "2024-08-09"
    assert cupping["days_after_roast"] == 6
    assert cupping["scores"]["flavor"] == 9.0
    assert cupping["scores"]["acidity"] == 8.5  # untouched by the merge
    assert cupping["notes"] == "Settled."
    assert cupping["scores"]["total"] == pytest.approx(EXPECTED_TOTAL + 0.5)


def test_remove_cupping(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)
    record = store.add_cupping(UUID_A, make_cupping(date="2024-08-20"))
    assert len(record["cuppings"]) == 2
    record = store.remove_cupping(UUID_A, 0)
    assert [c["date"] for c in record["cuppings"]] == ["2024-08-20"]


def test_remove_cupping_bad_index_raises(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)
    with pytest.raises(SensoryStoreError, match="no cupping"):
        store.remove_cupping(UUID_A, 3)
    with pytest.raises(SensoryStoreError, match="no cupping"):
        store.remove_cupping(UUID_A, -1)
    with pytest.raises(SensoryStoreError, match="no cupping"):
        store.edit_cupping(UUID_A, 3, {"notes": "x"})


def test_cupping_on_missing_record_raises(store: SensoryStore):
    with pytest.raises(SensoryStoreError, match="no sensory record"):
        store.add_cupping(UUID_A, make_cupping())


# ---------------------------------------------------------------------------
# Radar and native sync
# ---------------------------------------------------------------------------

def test_update_radar_values_keeps_default_labels(store: SensoryStore):
    store.create(UUID_A)
    record = store.update_radar(UUID_A, [8.5, 7.5, 10.0, 7.0, 8.0, 8.0, 8.5, 8.0, 7.0])
    assert record["radar"]["labels"] == list(DEFAULT_RADAR_LABELS)
    assert record["radar"]["values"] == [8.5, 7.5, 10.0, 7.0, 8.0, 8.0, 8.5, 8.0, 7.0]


def test_update_radar_custom_labels(store: SensoryStore):
    store.create(UUID_A)
    record = store.update_radar(UUID_A, [1.0, 2.0], labels=["A", "B"])
    assert record["radar"]["labels"] == ["A", "B"]
    assert record["radar"]["values"] == [1.0, 2.0]
    assert record["radar"]["manual"] is True


def test_set_native_sync_stamps_utc_iso8601(store: SensoryStore):
    store.create(UUID_A)
    record = store.set_native_sync(UUID_A, ["radar", "cuppingnotes"])
    stamp = datetime.fromisoformat(record["native_sync"]["last_synced"])
    assert stamp.tzinfo is not None
    assert record["native_sync"]["fields"] == ["radar", "cuppingnotes"]


# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------

def test_no_temp_files_left_behind(store: SensoryStore, tmp_path: Path):
    annotate(store, UUID_A, ROAST_REF)
    store.update_radar(UUID_A, [1.0, 2.0])
    store.edit_cupping(UUID_A, 0, {"notes": "x"})
    store.delete(UUID_A)
    files = sorted(p.name for p in (tmp_path / "sensory").iterdir())
    assert files == ["sensory_index.sqlite"]


def test_failed_replace_preserves_original(store: SensoryStore, tmp_path: Path, monkeypatch):
    annotate(store, UUID_A, ROAST_REF)
    sidecar = tmp_path / "sensory" / f"{UUID_A}.json"
    before = sidecar.read_bytes()

    monkeypatch.setattr(
        "store.sidecars.os.replace", lambda *a: (_ for _ in ()).throw(OSError("boom"))
    )
    with pytest.raises(SensoryStoreError, match="atomic write failed"):
        store.update_radar(UUID_A, [1.0, 2.0])

    assert sidecar.read_bytes() == before
    leftovers = [p for p in (tmp_path / "sensory").iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_index_not_updated_when_write_fails(store: SensoryStore, monkeypatch):
    annotate(store, UUID_A, ROAST_REF)
    monkeypatch.setattr(
        "store.sidecars.os.replace", lambda *a: (_ for _ in ()).throw(OSError("boom"))
    )
    with pytest.raises(SensoryStoreError):
        store.update_radar(UUID_A, [1.0, 2.0])
    rows = store.search(descriptor="apricot")
    assert [r["roast_uuid"] for r in rows] == [UUID_A]


# ---------------------------------------------------------------------------
# Persistence across restarts
# ---------------------------------------------------------------------------

def test_store_survives_close_and_reopen(tmp_path: Path):
    with SensoryStore(tmp_path / "sensory") as store:
        annotate(store, UUID_A, ROAST_REF)
        store.set_native_sync(UUID_A, ["radar"])

    with SensoryStore(tmp_path / "sensory") as store:
        record = store.get(UUID_A)
        assert record is not None
        assert record["cuppings"][0]["days_after_roast"] == 2
        assert record["native_sync"]["fields"] == ["radar"]
        assert [r["roast_uuid"] for r in store.search(descriptor="apricot")] == [UUID_A]


def test_reopen_rebuilds_index_from_sidecars(tmp_path: Path):
    with SensoryStore(tmp_path / "sensory") as store:
        annotate(store, UUID_A, ROAST_REF)
    # wipe the index entirely: it must rebuild from the sidecars alone
    (tmp_path / "sensory" / "sensory_index.sqlite").unlink()

    with SensoryStore(tmp_path / "sensory") as store:
        rows = store.search(descriptor="stone fruit")
        assert [r["roast_uuid"] for r in rows] == [UUID_A]
        assert rows[0]["n_cuppings"] == 1


def test_corrupt_sidecar_skipped_by_index_but_raises_on_get(tmp_path: Path):
    with SensoryStore(tmp_path / "sensory") as store:
        annotate(store, UUID_A, ROAST_REF)
        annotate(store, UUID_B, ROAST_REF)
    (tmp_path / "sensory" / f"{UUID_B}.json").write_text("garbage", encoding="utf-8")

    with SensoryStore(tmp_path / "sensory") as store:
        assert [r["roast_uuid"] for r in store.search()] == [UUID_A]
        with pytest.raises(SensoryStoreError):
            store.get(UUID_B)


# ---------------------------------------------------------------------------
# Index queries
# ---------------------------------------------------------------------------

def test_index_file_inside_sensory_folder(tmp_path: Path):
    store = SensoryStore(tmp_path / "sensory")
    store.close()
    assert (tmp_path / "sensory" / "sensory_index.sqlite").is_file()


def test_list_roasts_annotated_and_unannotated(store: SensoryStore):
    store.register_roast(UUID_A, "a.alog", "2024-08-03")
    store.register_roast(UUID_B, "b.alog", "2024-08-04")
    store.register_roast(UUID_C, "c.alog", "2024-08-05")
    annotate(store, UUID_A, ROAST_REF)

    all_rows = store.list_roasts()
    assert [r["roast_uuid"] for r in all_rows] == [UUID_A, UUID_B, UUID_C]
    assert [r["annotated"] for r in all_rows] == [True, False, False]

    only_annotated = store.list_roasts(annotated=True)
    assert [r["roast_uuid"] for r in only_annotated] == [UUID_A]
    assert only_annotated[0]["n_cuppings"] == 1
    assert only_annotated[0]["best_total"] == EXPECTED_TOTAL

    unannotated = store.list_roasts(annotated=False)
    assert [r["roast_uuid"] for r in unannotated] == [UUID_B, UUID_C]
    assert all(r["n_cuppings"] is None for r in unannotated)


def test_sidecar_without_registration_still_listed(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)
    rows = store.list_roasts()
    assert [r["roast_uuid"] for r in rows] == [UUID_A]
    assert rows[0]["annotated"] is True


def test_search_by_descriptor_substring_and_case(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)
    store.create(UUID_B, ROAST_REF)
    store.add_cupping(UUID_B, make_cupping(descriptors=["chocolate"]))

    assert [r["roast_uuid"] for r in store.search(descriptor="apricot")] == [UUID_A]
    assert [r["roast_uuid"] for r in store.search(descriptor="STONE")] == [UUID_A]
    assert [r["roast_uuid"] for r in store.search(descriptor="choc")] == [UUID_B]
    assert store.search(descriptor="caramel") == []


def test_search_by_date_range(store: SensoryStore):
    store.create(UUID_A, {"file": "a.alog", "date": "2024-07-01"})
    store.add_cupping(UUID_A, make_cupping())
    store.create(UUID_B, {"file": "b.alog", "date": "2024-09-01"})
    store.add_cupping(UUID_B, make_cupping())
    store.create(UUID_C, {"file": "c.alog"})  # unknown roast date
    store.add_cupping(UUID_C, make_cupping())

    uuids = lambda rows: [r["roast_uuid"] for r in rows]
    assert uuids(store.search(date_from="2024-08-01")) == [UUID_B]
    assert uuids(store.search(date_to="2024-08-01")) == [UUID_A]
    assert uuids(store.search(date_from="2024-01-01", date_to="2024-12-31")) == [
        UUID_A, UUID_B,
    ]
    # records without a roast date are excluded by any date filter
    assert UUID_C not in uuids(store.search(date_from="2020-01-01"))


def test_search_invalid_date_raises(store: SensoryStore):
    with pytest.raises(SensoryStoreError, match="date_from"):
        store.search(date_from="2024-13-40")


def test_search_by_score_range(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)
    store.create(UUID_B, ROAST_REF)
    store.add_cupping(UUID_B, make_cupping(scores={"flavor": 3.0, "overall": 3.0}))

    uuids = lambda rows: [r["roast_uuid"] for r in rows]
    assert uuids(store.search(min_score=50.0)) == [UUID_A]
    assert uuids(store.search(max_score=50.0)) == [UUID_B]
    assert store.search(min_score=90.0) == []
    # best total = max across cuppings; both share the roast date,
    # so the uuid breaks the tie (UUID_B sorts before UUID_A)
    store.add_cupping(UUID_B, make_cupping())
    assert uuids(store.search(min_score=80.0)) == [UUID_B, UUID_A]


def test_search_combined_filters(store: SensoryStore):
    annotate(store, UUID_A, ROAST_REF)  # 2024-08-03, apricot..., total 84
    store.create(UUID_B, {"file": "b.alog", "date": "2024-09-01"})
    store.add_cupping(UUID_B, make_cupping(date="2024-09-10"))

    rows = store.search(
        descriptor="apricot", date_from="2024-08-01", date_to="2024-08-31",
        min_score=80.0, max_score=90.0,
    )
    assert [r["roast_uuid"] for r in rows] == [UUID_A]


def test_index_database_is_valid_sqlite(store: SensoryStore, tmp_path: Path):
    annotate(store, UUID_A, ROAST_REF)
    conn = sqlite3.connect(tmp_path / "sensory" / "sensory_index.sqlite")
    try:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"roasts", "annotations", "descriptors"} <= tables
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Radar auto-update from cupping means (M9 Task 2)
# ---------------------------------------------------------------------------

# Expected radar values after one cupping with FULL_SCORES, mapped through
# DEFAULT_RADAR_LABELS:
#   Acidity→acidity=8.5, Aftertaste→aftertaste=7.5, Clean Cup→clean_cup=10.0,
#   Head→overall=8.5, Fragrance→fragrance_aroma=8.0, Sweetness→sweetness=8.0,
#   Aroma→fragrance_aroma=8.0, Balance→balance=8.0, Body→body=7.0
RADAR_AFTER_ONE = [8.5, 7.5, 10.0, 8.5, 8.0, 8.0, 8.0, 8.0, 7.0]

# Second cupping with different scores for mean tests.
SCORES_2 = {
    "fragrance_aroma": 7.0, "flavor": 7.0, "aftertaste": 9.0,
    "acidity": 6.0, "body": 8.5, "balance": 7.5,
    "uniformity": 10.0, "clean_cup": 8.0, "sweetness": 9.0,
    "overall": 7.0, "defects": 0,
}
# Mean of FULL_SCORES and SCORES_2 per default radar label:
#   Acidity=(8.5+6.0)/2=7.25, Aftertaste=(7.5+9.0)/2=8.25,
#   Clean Cup=(10.0+8.0)/2=9.0, Head=(8.5+7.0)/2=7.75,
#   Fragrance=(8.0+7.0)/2=7.5, Sweetness=(8.0+9.0)/2=8.5,
#   Aroma=(8.0+7.0)/2=7.5, Balance=(8.0+7.5)/2=7.75, Body=(7.0+8.5)/2=7.75
RADAR_AFTER_TWO = [7.25, 8.25, 9.0, 7.75, 7.5, 8.5, 7.5, 7.75, 7.75]


def test_add_cupping_updates_radar_to_mean(store: SensoryStore):
    """Adding a cupping sets radar values to that cupping's scores."""
    store.create(UUID_A, ROAST_REF)
    record = store.add_cupping(UUID_A, make_cupping())
    assert record["radar"]["labels"] == list(DEFAULT_RADAR_LABELS)
    assert record["radar"]["values"] == RADAR_AFTER_ONE


def test_add_second_cupping_updates_radar_to_mean_of_both(store: SensoryStore):
    """Adding a second cupping averages both sessions' scores."""
    store.create(UUID_A, ROAST_REF)
    store.add_cupping(UUID_A, make_cupping())
    record = store.add_cupping(UUID_A, make_cupping(date="2024-08-10", scores=dict(SCORES_2)))
    assert record["radar"]["values"] == RADAR_AFTER_TWO


def test_preexisting_radar_counts_as_one_session(store: SensoryStore):
    """A manually-set radar counts as one extra session in the mean."""
    store.create(UUID_A, ROAST_REF)
    # Manually set radar to all 5.0 — counts as one session.
    store.update_radar(UUID_A, [5.0] * 9)
    # Add one cupping with FULL_SCORES.
    record = store.add_cupping(UUID_A, make_cupping())
    # Mean of [5.0]*9 and FULL_SCORES per label:
    #   Acidity=(5+8.5)/2=6.75, Aftertaste=(5+7.5)/2=6.25,
    #   Clean Cup=(5+10)/2=7.5, Head=(5+8.5)/2=6.75,
    #   Fragrance=(5+8)/2=6.5, Sweetness=(5+8)/2=6.5,
    #   Aroma=(5+8)/2=6.5, Balance=(5+8)/2=6.5, Body=(5+7)/2=6.0
    expected = [6.75, 6.25, 7.5, 6.75, 6.5, 6.5, 6.5, 6.5, 6.0]
    assert record["radar"]["values"] == expected


def test_remove_cupping_updates_radar(store: SensoryStore):
    """Removing a cupping recomputes the radar from the remaining sessions."""
    store.create(UUID_A, ROAST_REF)
    store.add_cupping(UUID_A, make_cupping())
    store.add_cupping(UUID_A, make_cupping(date="2024-08-10", scores=dict(SCORES_2)))
    # Radar is the mean of both.
    record = store.get(UUID_A)
    assert record["radar"]["values"] == RADAR_AFTER_TWO
    # Remove the first cupping — radar should reflect only the second.
    record = store.remove_cupping(UUID_A, 0)
    # SCORES_2 mapped through default labels:
    #   Acidity=6.0, Aftertaste=9.0, Clean Cup=8.0, Head=7.0,
    #   Fragrance=7.0, Sweetness=9.0, Aroma=7.0, Balance=7.5, Body=8.5
    expected = [6.0, 9.0, 8.0, 7.0, 7.0, 9.0, 7.0, 7.5, 8.5]
    assert record["radar"]["values"] == expected


def test_edit_cupping_updates_radar(store: SensoryStore):
    """Editing a cupping's scores recomputes the radar."""
    store.create(UUID_A, ROAST_REF)
    store.add_cupping(UUID_A, make_cupping())
    record = store.get(UUID_A)
    assert record["radar"]["values"] == RADAR_AFTER_ONE
    # Edit acidity from 8.5 to 10.0.
    record = store.edit_cupping(UUID_A, 0, {"scores": {"acidity": 10.0}})
    # Only Acidity (index 0) changes; the rest stay the same.
    expected = list(RADAR_AFTER_ONE)
    expected[0] = 10.0
    assert record["radar"]["values"] == expected


def test_radar_unchanged_with_no_cuppings(store: SensoryStore):
    """With no cuppings and no pre-existing radar, radar stays empty."""
    record = store.create(UUID_A, ROAST_REF)
    assert record["radar"]["values"] == []
    # Labels are still the defaults.
    assert record["radar"]["labels"] == list(DEFAULT_RADAR_LABELS)


def test_radar_custom_labels(store: SensoryStore):
    """Custom radar labels are mapped correctly when computing means."""
    store.create(UUID_A, ROAST_REF)
    # Set custom labels: only Acidity and Body.
    store.update_radar(UUID_A, [0.0, 0.0], labels=["Acidity", "Body"])
    record = store.add_cupping(UUID_A, make_cupping())
    assert record["radar"]["labels"] == ["Acidity", "Body"]
    # Acidity→acidity=8.5, Body→body=7.0
    assert record["radar"]["values"] == [8.5, 7.0]


def test_radar_custom_labels_unmapped_kept(store: SensoryStore):
    """Labels with no SCA equivalent keep their value when computing means."""
    store.create(UUID_A, ROAST_REF)
    # "Flavor Notes" has no SCA equivalent; "Acidity" does.
    # Manual radar [3.0, 5.0] counts as one session.
    store.update_radar(UUID_A, [3.0, 5.0], labels=["Flavor Notes", "Acidity"])
    record = store.add_cupping(UUID_A, make_cupping())
    # "Flavor Notes" keeps its manual value (3.0); no SCA key to average.
    # "Acidity" = mean(8.5 from cupping, 5.0 from manual radar) = 6.75
    assert record["radar"]["labels"] == ["Flavor Notes", "Acidity"]
    assert record["radar"]["values"] == [3.0, 6.75]


def test_radar_partial_scores_skipped(store: SensoryStore):
    """Cuppings missing a score key are skipped for that axis."""
    store.create(UUID_A, ROAST_REF)
    # First cupping: only acidity and body.
    store.add_cupping(UUID_A, make_cupping(scores={"acidity": 8.0, "body": 6.0}))
    # Second cupping: only acidity (different value) and body.
    store.add_cupping(UUID_A, make_cupping(
        date="2024-08-10",
        scores={"acidity": 6.0, "body": 8.0},
    ))
    record = store.get(UUID_A)
    labels = record["radar"]["labels"]
    values = record["radar"]["values"]
    # Acidity (index 0): mean of 8.0 and 6.0 = 7.0
    assert values[labels.index("Acidity")] == 7.0
    # Body (last index): mean of 6.0 and 8.0 = 7.0
    assert values[labels.index("Body")] == 7.0
    # Aftertaste (index 1): no cupping has it, no pre-existing radar → 0.0
    assert values[labels.index("Aftertaste")] == 0.0


def test_radar_case_insensitive_labels(store: SensoryStore):
    """Radar label matching is case-insensitive."""
    store.create(UUID_A, ROAST_REF)
    store.update_radar(UUID_A, [0.0, 0.0], labels=["ACIDITY", "body"])
    record = store.add_cupping(UUID_A, make_cupping())
    assert record["radar"]["values"] == [8.5, 7.0]


def test_radar_head_maps_to_overall(store: SensoryStore):
    """The 'Head' label maps to the 'overall' SCA score key."""
    store.create(UUID_A, ROAST_REF)
    record = store.add_cupping(UUID_A, make_cupping())
    labels = record["radar"]["labels"]
    values = record["radar"]["values"]
    # Head is at index 3 in DEFAULT_RADAR_LABELS; overall = 8.5
    assert labels[3] == "Head"
    assert values[3] == 8.5  # FULL_SCORES["overall"]


def test_manual_radar_after_cuppings_counts_as_session(store: SensoryStore):
    """Manual radar set after cuppings still counts when another cupping is added."""
    store.create(UUID_A, ROAST_REF)
    # Add first cupping — radar auto-computed.
    store.add_cupping(UUID_A, make_cupping())
    # User manually overrides the radar.
    store.update_radar(UUID_A, [5.0] * 9)
    # Add second cupping — manual radar should count as one session.
    record = store.add_cupping(
        UUID_A, make_cupping(date="2024-08-10", scores=dict(SCORES_2))
    )
    # Mean of: cupping1 (FULL_SCORES), cupping2 (SCORES_2), manual [5.0]*9
    # Acidity: (8.5 + 6.0 + 5.0) / 3 = 6.5
    # Aftertaste: (7.5 + 9.0 + 5.0) / 3 = 7.17
    # Clean Cup: (10.0 + 8.0 + 5.0) / 3 = 7.67
    # Head(overall): (8.5 + 7.0 + 5.0) / 3 = 6.83
    # Fragrance: (8.0 + 7.0 + 5.0) / 3 = 6.67
    # Sweetness: (8.0 + 9.0 + 5.0) / 3 = 7.33
    # Aroma: (8.0 + 7.0 + 5.0) / 3 = 6.67
    # Balance: (8.0 + 7.5 + 5.0) / 3 = 6.83
    # Body: (7.0 + 8.5 + 5.0) / 3 = 6.83
    expected = [6.5, 7.17, 7.67, 6.83, 6.67, 7.33, 6.67, 6.83, 6.83]
    assert record["radar"]["values"] == expected


def test_radar_manual_flag_cleared_after_auto_compute(store: SensoryStore):
    """After auto-computation, the manual flag is cleared (idempotent)."""
    store.create(UUID_A, ROAST_REF)
    store.update_radar(UUID_A, [5.0] * 9)
    record = store.add_cupping(UUID_A, make_cupping())
    assert record["radar"]["manual"] is False
    # Adding a second cupping should NOT count the previous radar as a session.
    record = store.add_cupping(
        UUID_A, make_cupping(date="2024-08-10", scores=dict(SCORES_2))
    )
    assert record["radar"]["values"] == RADAR_AFTER_TWO
    assert record["radar"]["manual"] is False
