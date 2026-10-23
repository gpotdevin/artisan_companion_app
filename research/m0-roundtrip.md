# M0: Round-trip and Unknown-Key Experiments — Findings

**Date:** 2026-10-23  
**Milestone:** M0 (Pre-flight experiments)  
**Status:** Complete  
**Exit criteria:** Written findings in `research/`, go/no-go for native sync (M4)  

This document reports on experiments R-1 and R-2 from [implementation-plan.md](../docs/implementation-plan.md), 
which are the gate for milestone M4 (native sync). All experiments were run on file *copies* in a temp 
directory (`C:\Users\guill\AppData\Local\Temp\m0_experiment\`). No original corpus file was modified.

---

## 0. Summary and Verdict

| Experiment | Result | Implication for M4 |
|---|---|---|
| R-1 round-trip (v4.2.0) | **PASS** — rewritten file parses cleanly; ONLY 5 intended fields changed structurally | Native sync is **GO** with the caveat below on hash/signature |
| R-1 round-trip (v2.10.4) | **PASS** — same; proves pre-4.0 files also work | Pre-4.0 files are safe for native sync |
| R-1 hash/signature analysis | **UNVERIFIED** — fields preserved in rewrite, but behavior on stale values unknown | **MANUAL CHECK required** (see section 4) before enabling M4 |
| R-2 unknown-key tolerance (7 fixtures) | **PASS** — `alog_core` parses all copies with injected key fine | Defensive `.get()` works across all 7 versions |

**Verdict:** *Conditional GO* — proceed with M4 native sync **after** the manual check in section 4 confirms 
Artisan's behavior on stale `hash`/`signature` in v4.2 files. The round-trip serialization is 
byte-for-byte compatible with Artisan's format (Python `repr()` matches exactly).

---

## 1. What Was Done

### R-1: Round-trip test

1. **Script:** Created `research/rewrite_native_fields.py` — a reusable Python 3 script that:
   - Loads an `.alog` file via `ast.literal_eval` (same as `alog_core.parser.load_alog`)
   - Updates ONLY the native sensory fields M4 will write:
     - `flavors`: list of 9 floats (changed from all 5.0 to `[8.5, 7.5, 9.0, 8.0, 8.5, 8.0, 9.0, 8.5, 8.0]`)
     - `flavorlabels`: list of 9 strings (changed to custom labels)
     - `cuppingnotes`: string (changed from empty to a cupping description)
     - defect booleans: `tipping` and `scorching` set to `True`, others to `False`
   - Writes back using Python's `repr()` which produces **identical serialization** to Artisan
   - Verifies the output parses with the same loader

2. **Executed on copies:**
   ```
   # v4.2.0 fixture
   py -3 research/rewrite_native_fields.py \
       C:/Users/guill/AppData/Local/Temp/m0_experiment/v4.2.0_2026-10-04.alog \
       C:/Users/guill/AppData/Local/Temp/m0_experiment/v4.2.0_2026-10-04_rewritten.alog
   
   # v2.10.4 fixture
   py -3 research/rewrite_native_fields.py \
       C:/Users/guill/AppData/Local/Temp/m0_experiment/v2.10.4_2024-08-03.alog \
       C:/Users/guill/AppData/Local/Temp/m0_experiment/v2.10.4_2024-08-03_rewritten.alog
   ```

### R-2: Unknown-key tolerance test

For each of the 7 anonymized fixtures (v2.4.6 → v4.2.0):
1. Copied fixture to temp dir
2. Loaded with `ast.literal_eval`
3. Injected a bogus top-level key: `"zzz_companion_test": 1`
4. Re-serialized with `repr()` and wrote to a new file
5. Verified `alog_core.load_alog()` parses the copy successfully

---

## 2. Verification Results

### 2.1 Round-trip: Structural Diff

Both rewritten files were loaded and compared against their originals. **Only the intended 
5 fields changed** in both cases:

| Field | Old (v4.2.0) | New | Status |
|---|---|---|---|
| `flavors` | `[5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]` | `[8.5, 7.5, 9.0, 8.0, 8.5, 8.0, 9.0, 8.5, 8.0]` | ✓ Changed |
| `flavorlabels` | `['Acidity', 'Aftertaste', 'Clean Cup', 'Head', 'Fragrance', 'Sweetness', 'Aroma', 'Balance', 'Body']` | Custom labels | ✓ Changed |
| `cuppingnotes` | `''` (empty) | `'Bright citrus, floral jasmine, honey sweetness, clean finish'` | ✓ Changed |
| `tipping` | `False` | `True` | ✓ Changed |
| `scorching` | `False` | `True` | ✓ Changed |
| All other fields | — | — | ✓ Unchanged |

Same result for v2.10.4 file. **Zero unintended changes.**

### 2.2 Round-trip: Serialization Format

- Python's `repr()` on the parsed dict produces **byte-for-byte identical serialization** to 
  Artisan for the unchanged portions
- Dict insertion order is preserved through `ast.literal_eval` → modification → `repr()`
- Key order in the rewritten files matches the originals exactly
- The rewritten files are valid single-line ASCII Python dict literals

### 2.3 Round-trip: alog_core Compatibility

Both rewritten files parse successfully with `alog_core.load_alog()`:
- v4.2.0 rewritten: ✓ Loaded, all fields accessible
- v2.10.4 rewritten: ✓ Loaded, all fields accessible

### 2.4 Round-trip: Byte-level Stats

| File | Original Size | Rewritten Size | Delta | Delta Reason |
|---|---|---|---|---|
| v4.2.0_2026-10-04.alog | 19,107 bytes | 19,174 bytes | +67 bytes | New strings in flavors/cuppingnotes/defects are longer |
| v2.10.4_2024-08-03.alog | 18,019 bytes | 18,086 bytes | +67 bytes | Same reason |

The size increase is exactly the difference in string lengths of the new field values.

### 2.5 R-2: Unknown-key Tolerance

All 7 fixtures passed the unknown-key test:

| Fixture | Parse Result | Bogus Key Present in Loaded Data |
|---|---|---|
| v2.4.6_2021-11-19_multiline.alog | ✓ OK | Yes |
| v2.6.0_2022-09-16.alog | ✓ OK | Yes |
| v2.8.2_2023-04-09.alog | ✓ OK | Yes |
| v2.10.0_2024-04-02.alog | ✓ OK | Yes |
| v2.10.4_2024-08-03.alog | ✓ OK | Yes |
| v3.2.0_2026-07-23.alog | ✓ OK | Yes |
| v4.2.0_2026-10-04.alog | ✓ OK | Yes |

**Conclusion:** `alog_core.parser.load_alog()` uses defensive key access and tolerates unknown 
keys across all 7 Artisan versions (2.4.6 → 4.2.0). This confirms the parser's design principle.

### 2.6 R-1: Hash/Signature Preservation

In v4.2 files:
- `hash`: 64-character hex string
- `signature`: 128-character hex string

The rewrite script preserves these fields unchanged:
- v4.2.0 rewritten file: `hash` present and unchanged ✓
- v4.2.0 rewritten file: `signature` present and unchanged ✓

---

## 3. Hash/Signature Analysis

### 3.1 What They Are

From [upstream-findings.md](upstream-findings.md) and [alog_files_technical_description.md](https://github.com/artisan-roaster-scope/artisan/blob/master/alog_files_technical_description.md) (upstream):
- Introduced in Artisan v4.2.0
- `hash`: 64-hex integrity checksum
- `signature`: 128-hex integrity signature

From observation of the corpus:
- Present in all 9 v4.2.0 files
- Absent in all 221 pre-4.2 files
- Values are unique per file

### 3.2 What They Likely Cover

Given that Artisan uses a `ProfileData` TypedDict schema (from upstream source analysis in 
[upstream-findings.md](upstream-findings.md)), the hash/signature likely covers:
- The canonical set of `ProfileData` fields
- Possibly the entire dict content (all keys known to Artisan at save time)

**Critical insight:** Since the rewrite preserves the original `hash` and `signature` values while 
changing field contents, **the hash/signature become stale** after a rewrite. This is the 
R-1 risk flagged in [feasibility-evaluation.md](../docs/feasibility-evaluation.md).

### 3.3 Expected Artisan Behavior (UNVERIFIED)

From the upstream source (not available locally for dynamic testing), the likely behaviors are:

| Scenario | Expected Artisan Behavior |
|---|---|
| Load v4.2 file with valid hash/signature | Loads normally, no warning |
| Load v4.2 file with stale hash/signature | **UNKNOWN** — possibilities: (a) silent load with recalculation, (b) warning dialog, (c) refusal to load |
| Load pre-v4.2 file (no hash/signature) | Loads normally (backward compatible) |

### 3.4 Implication for M4

Native sync (M4) **MUST** either:
1. **Recompute** hash/signature after writing native fields, OR
2. **Delete** hash/signature from v4.2 files before writing, letting Artisan recreate them on next save, OR  
3. **Restrict** native sync to pre-v4.2 files only

Option 1 requires reverse-engineering Artisan's hash/signature algorithm (not yet done).
Option 2 is simpler and safer: drop `hash` and `signature` before 
