# Review: M1 (alog_core) + M2a (store)

- **Scope**: Read-only code review of M1 (`src/alog_core`) and M2a (`src/store`).
- **Method**: Static analysis and manual inspection.
- **Date**: 2026-10-23
- **Reviewer model**: Mistral Large 4

## Findings and Resolutions

All fixes are committed on `dev`. Verified commit hashes via `git log --oneline`.

| ID | Severity | Location | Description | Suggested Fix | Resolution Status |
|---|---|---|---|---|---|
| M-1 | Medium | `src/alog_core/model.py` | Marker/event index-shift when samples are dropped | Raw->coerced index map; regression tests | FIXED by `08d4da1` |
| M-2 | Medium | `src/store/index.py` `upsert_roast` | `register_roast(uuid)` with no file/date wipes an existing registration | COALESCE merge | FIXED by `d20c1f3` |
| M-3 | Medium | CI | `pytest` would fail collecting `tests/test_app.py` (fastapi/httpx missing) | Install app test deps | FIXED by `40a025d` |
| L-1 | Low | Store schema | `schema_version: true` accepted as `1` | Strict int, reject bool | FIXED by `8446d4e` |
| L-2 | Low | Store schema | String exploded into per-character lists (radar labels/values, native_sync fields, descriptors) | `_as_list` helper | FIXED by `8446d4e` |
| L-3 | Low | Store schema | Radar values not range-validated | Validate 0-10 | FIXED by `8446d4e` |
| L-4 | Low | `SensoryStore` | `delete_record` leaks raw `OSError` | Wrap in `SensoryStoreError` | FIXED by `322a6f9` |
| L-5 | Low | Store index | `search(min_score=...)` with non-number silently returns nothing | Raise `SensoryStoreError` on garbage | FIXED by `d20c1f3` |
| L-6 | Low | Store schema | Cupping with only defects penalty gets negative total | Floor total at 0 | FIXED by `8446d4e` |
| L-7 | Low | Store index | `build_index` on missing logs dir silently builds empty index | Raise `AlogParseError` | FIXED by `322a6f9` |
| L-8 | Low | README | Stale status/license | Update to MIT per `pyproject.toml` | FIXED by `40a025d` |
| L-9 | Low | Project layout | `pyproject` renamed to `artisan-companion` with app extra | Accept coherent single-distribution layout | NOTED, accepted |
| L-10 | Low | UI spec vs store | S1 promises notes search; store index has none | Add notes column/FTS when viewer search ships | DEFERRED to M3 |
| L-11 | Low | Store index | Descriptor search ASCII-case-insensitive only | Optional Python-side case folding later | ACCEPTED for now |
| L-12 | Low | Store | Atomic write lacks directory fsync after rename | Local companion app; power-loss durability out of scope | ACCEPTED |
| L-13 | Low | Repo root | `smoke_test.py` scratch file | File no longer present | RESOLVED |

## Areas Verified Clean

- No `eval`/`exec` on log content
- No `.alog` writes
- ISO 8601 timestamps
- Stdlib-only core+store
- Fixture anonymization sufficient
- Parser edge cases
- RoR metrics
- Store atomicity/index rebuild
- Corpus re-verification 230/230
- End-to-end composition
- Git hygiene for fixtures

## Review Verdict

Ready to build M2b/M3 on top after M-1/M-2/M-3 fixes — all three are now fixed.

## Remaining Test-Coverage Gaps

- Out-of-range marker indices test
- Timeindex shorter than 8 / non-monotonic timex assumption
- `alog_core`<->`store` integration test
- `.alog` byte-identical guardrail test
