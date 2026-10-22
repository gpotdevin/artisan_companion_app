# Evidence Notes — Evaluation Session 2026-10-21

Supports [feasibility-evaluation.md](../docs/feasibility-evaluation.md). Two
evidence sources were used: the local log corpus and the upstream Artisan
source on GitHub (master branch, checked 2026-10-21).

## 1. Local corpus (`../Artisan/logs`, 230 `.alog` files)

Verified programmatically (existing scan plus spot checks):

- All 230 files are pure-ASCII, single-line Python dict literals; all parse
  with `ast.literal_eval` (230/230, zero failures).
- Version histogram: 2.4.6 = 56, 2.6.0 = 14, 2.8.2 = 42, 2.10.0 = 21,
  2.10.4 = 40, 3.2.0 = 48, 4.2.0 = 9.
- Key counts grow monotonically with version: 151 (v2.4.6) → 196 (v4.2.0);
  grammar unchanged; keys only added (only `beansize`, `oversampling` dropped
  after v2.x).
- Sensory fields present in sampled v2.10.4 file: `flavors` (9 floats, all
  default 5.0), `flavorlabels` (Acidity, Aftertaste, Clean Cup, Head, Fragrance,
  Sweetness, Aroma, Balance, Body), `flavorstartangle`, `flavoraspect`,
  `cuppingnotes` (empty), `roastingnotes` (empty), defect booleans (`heavyFC`,
  `lowFC`, `lightCut`, `darkCut`, `drops`, `oily`, `uneven`, `tipping`,
  `scorching`, `divots`), `whole_color`/`ground_color` (0, unset),
  `moisture_greens`/`moisture_roasted` (unset).
- Curve data present in all files: `timex`, `temp1` (ET), `temp2` (BT),
  `timeindex` markers, `specialevents*` + `etypes`, `phases`, `computed` stats.
- `roastUUID` (32-hex) present in modern files — stable identity for linking.
- v4.2.0 files add `hash` and `signature` (integrity strings of unknown
  enforcement behavior — see R-1).
- String values are double-escaped ASCII (`\xe9` style); a
  `latin-1` → `unicode_escape` pass recovers accents (78 files affected).

Pre-existing local assets (produced in earlier sessions, reused here):

- `../Artisan/alog_files_technical_description.md` — byte-level format
  description, event/marker semantics, unit handling, parser guidance.
- `../Artisan/data_logs_technical_specification.md` — schema of the tidy
  `roasts`/`curves`/`events` tables derived from the corpus.
- `../Artisan/extract_alog.py` + `extracted_logs/` — working extraction
  pipeline (230 roasts, 106,992 curve rows, 2,701 event rows, 0 errors).

## 2. Upstream Artisan source (github.com/artisan-roaster-scope/artisan)

Repository layout (master, checked 2026-10-21): core Python package under
`src/` (main application window ~1.7 MB `main.py`, plus modules: `atypes.py`,
`util.py`, `cup_profile.py`, `comparator.py`, `roast_properties.py`, ...).

Key findings:

- `src/<core>/atypes.py` defines the in-memory profile as
  `class ProfileData(TypedDict, total=False)` — a **fixed, closed key set**
  covering all fields written to `.alog` (flavors, flavorlabels, cuppingnotes,
  svRamps, ambient_*, etc. all appear there as typed members).
  `ComputedProfileInformation` holds the `computed` sub-dict.
- `cup_profile.py` implements the flavor radar dialog: `flavorlabels` is a
  user-configurable list (defaults incl. an SCAA default set), `flavors` the
  matching value list; the cupping notes dialog edits `cuppingnotes`.
- Loading is driven by that schema: the parsed dict is reduced to the known
  `ProfileData` fields; saving serializes those fields. Therefore:
  - unknown keys are ignored on load (tolerant),
  - unknown keys are not re-written on save (dropped).
- Profile save/load machinery lives in the large `main.py` (not indexed by
  GitHub code search; content examined only partially — the closed-key-set
  conclusion rests on the `ProfileData` schema plus the observed corpus
  behavior that files only ever contain known keys).
- License: Artisan is AGPL-3.0. Reading and writing its file format does not
  link its code; an independent implementation is not AGPL-contaminated.

Confidence notes:

- "Custom keys dropped on Artisan re-save" is high-confidence (schema-driven
  load + save) but was not executed against a live Artisan instance in this
  session. Milestone M0 mandates the empirical round-trip test before any
  inline write feature ships.
- `hash`/`signature` enforcement (v4.2) is unverified — flagged as risk R-1
  and experiment in M0.

## 3. Known upstream references

- Artisan project: https://artisan-scope.org/ ; source:
  https://github.com/artisan-roaster-scope/artisan
- `.alog` extension registered by Artisan (`src/artisan-alog.xml`).
