# Feasibility Evaluation — Sensory Companion App for Artisan `.alog` Logs

Evaluation date: 2026-10-21.
Evidence base: 230 `.alog` files (2021–2026, Artisan 2.4.6 → 4.2.0) and the
upstream Artisan source code (GitHub `artisan-roaster-scope/artisan`, master).
Details: [research/upstream-findings.md](../research/upstream-findings.md).

---

## 1. Question

Can a standalone companion app — operating purely offline on existing `.alog`
files, with no interaction with a running Artisan instance:

1. attach sensory information (cupping scores, flavor descriptors, defects) to
   existing `.alog` roast logs, using the file format itself — information that
   by nature only becomes available days after the roast, once beans are
   rested and cupped, and therefore can never be entered in Artisan during or
   right after roasting;
2. display a roast profile (curves, events, phases) similar to Artisan's graph?

## 2. Short answer

**Both are feasible.** The `.alog` format is a plain-text Python dictionary
literal that tolerates additional keys, and it already ships a set of *native
sensory fields* (flavor radar, cupping notes, defect flags, color readings) that
round-trip through Artisan untouched. The full curve data needed to redraw the
profile is present in every file of the corpus.

One material constraint shapes the design: **custom (non-native) keys do not
survive an Artisan re-save**. Artisan loads the dict, keeps only the keys it
knows (its `ProfileData` schema), and writes exactly those keys back. So rich
sensory data must live in fields Artisan preserves, and/or in a sidecar store.
This drives the recommended **hybrid storage model** (section 6).

## 3. The `.alog` format in brief

| Property | Finding |
|---|---|
| Serialization | Single-line, pure-ASCII Python dict literal ("pydump"), no pickle in the corpus |
| Safe parsing | `ast.literal_eval` (stdlib, no execution) — 230/230 corpus files parse |
| Size | ~19–30 KB per roast, one physical line (two early files pretty-printed, same grammar) |
| Compatibility | Only additive change observed across versions 2.4.6 → 4.2.0 (151 → 196 keys); one parser handles the whole corpus; read optional keys with `.get()` |
| Text quirk | Non-ASCII in string values stored double-escaped; recover via `latin-1` → `unicode_escape` pass |
| Identity | `roastUUID` (32-hex) present in all modern files; stable key for linking data |
| Introspection | `version` / `recording_version` identify the writing Artisan; `mode` ('C') fixes units |

Core content per roast:

- `timex` / `temp1` (ET) / `temp2` (BT): parallel time series (~2 s sampling).
- `timeindex`: indices of CHARGE / DRY / FCs / DROP / COOL markers.
- `specialevents*` + `etypes`: manual events (air, burner changes...).
- `computed`: derived statistics (TP, MET, phase times, weight loss, RoR stats).
- Metadata: title, beans, weights, date/time, ambient conditions, machine info.

## 4. Sensory capability of the format today

Native fields already present in the format (all observed in the corpus):

| Field | Purpose | Notes |
|---|---|---|
| `flavors` | Radar scores, list of floats (0–10 scale) | Corpus files hold the untouched default (all 5.0) — free capacity |
| `flavorlabels` | Axis labels for the radar (fully customizable list) | Default: Acidity, Aftertaste, Clean Cup, Head, Fragrance, Sweetness, Aroma, Balance, Body |
| `cuppingnotes` | Free-text cupping notes | Empty in corpus |
| `roastingnotes` | Free-text roasting notes | Sparsely used |
| Defect flags | `tipping`, `scorching`, `divots`, `uneven`, `oily`, `drops`, `heavyFC`, `lowFC`, `lightCut`, `darkCut` | Boolean roast-quality observations, first-class in Artisan's UI |
| `whole_color`, `ground_color`, `color_system` | Roast color readings (e.g. Colorette/Tonino) | Unset in corpus |
| `moisture_greens`, `moisture_roasted` | Moisture measurements | Unset in corpus |
| `weight` [green, roasted, unit], `density*` | Yield metrics | Green weight used consistently |

**Conclusion:** the format was designed with sensory data in mind. A companion
app can populate `flavors`/`flavorlabels`/`cuppingnotes`/defect flags and the
data will be readable — and editable — inside Artisan itself, on any version.

## 5. Round-trip behavior (the decisive constraint)

Verified against the upstream source (see research notes):

- **Load is tolerant.** Artisan parses the whole dict and reads the keys it
  knows. Extra keys injected by a companion app are ignored, not fatal.
- **Save is closed.** The in-memory profile is a `ProfileData` TypedDict — a
  fixed key set. On save, Artisan writes exactly those known fields. Any custom
  key added by an external tool is dropped the next time the user re-saves that
  log from Artisan.
- **Known caveat (v4.2 files):** the newest files carry `hash` and `signature`
  integrity fields. If an external tool rewrites the file, these become stale.
  Expected behavior (warning or silent recalculation) is not yet confirmed from
  source; it must be settled by the round-trip experiment R-1 in the
  implementation plan before any inline writing ships.

Practical consequence per storage strategy:

| Strategy | Survives Artisan load? | Survives Artisan re-save? | Visible in Artisan? | Risk to original file |
|---|---|---|---|---|
| A. Write native fields only (flavors, cuppingnotes, defects...) | Yes | **Yes** | Yes (radar, notes, flags UI) | Low — but file is rewritten; v4.2 `hash`/`signature` stale (R-1) |
| B. Inject custom keys (`sensory: {...}`) | Yes (ignored) | **No — dropped** | No | Same rewrite risk for no persistence gain |
| C. Sidecar file / local store keyed by `roastUUID` | n/a (file untouched) | **Yes** | No (unless synced to A) | **None** |

## 6. Verdict and recommended model

**Feasible — proceed**, with a hybrid of strategies A and C:

1. **Sidecar-first (C):** rich structured sensory data lives in a companion
   store keyed by `roastUUID` — the original `.alog` is never modified. This is
   the system of record for cupping sessions, multi-brew impressions, photos,
   and anything the native format cannot hold.
2. **Native sync (A), opt-in:** the app can also write the native `flavors`,
   `flavorlabels`, `cuppingnotes` and defect-flag fields back into the `.alog`
   (one native field = one capability Artisan itself displays). Because these
   fields round-trip, the sensory summary becomes visible inside Artisan.
   Gated behind the R-1 experiment and a backup-before-write rule.
3. **No custom keys inside `.alog` (B rejected):** they are silently deleted by
   Artisan on re-save; relying on them would corrupt the user's expectations.

**Profile viewing** is unconditionally feasible: `timex/temp1/temp2`,
`timeindex`, `specialevents*`, `phases` and `computed` contain everything needed
to reproduce an Artisan-style graph (curves, RoR derived from BT, event flags,
phase shading, background-profile comparison via `backgroundUUID`).

## 7. Risks and unknowns

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R-1 | Rewriting v4.2 logs invalidates `hash`/`signature`; behavior of Artisan on stale signature unknown | Medium | Round-trip experiment on file copies before enabling native sync; if problematic, restrict inline writes to < v4.2 files or disable inline writes |
| R-2 | Artisan format evolves (new keys, possible future schema change) | Low | Additive-only evolution observed over 5 years; parser reads all keys defensively via `.get()`; corpus regression test across all 7 versions |
| R-3 | Parsing Python literals from untrusted files | Low | `ast.literal_eval` only — never `eval()`/`pickle` |
| R-4 | Filename ↔ UUID drift (renamed/duplicated logs) | Low | Key on `roastUUID`; fall back to filename hash for the two oldest files lacking it; de-duplicate on import |
| R-5 | User opens the app's store on another machine | Medium | Keep the store as plain JSON/SQLite next to the logs folder (portable, sync-friendly); document layout |

## 8. Pre-existing assets that de-risk the project

- A validated parser/extraction pipeline already exists for this corpus
  (`extract_alog.py` producing `roasts`/`curves`/`events` tables, 230/230 files,
  106,992 curve samples, 2,701 events).
- Byte-level format documentation for all corpus versions.
- A real multi-year corpus spanning 7 Artisan versions — an ideal test fixture
  (to be reduced to a small anonymized sample for the public repo).
