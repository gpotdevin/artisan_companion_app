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
Option 2 is simpler and safer: drop `hash` and `signature` before writing, letting Artisan recreate them on next save. A no-hash copy has now been prepared for the manual check in section 4.

**Update (2026-10-23):** Option 1 (**recompute hash**) is **CHOSSEN** — see section 7. Option 2 (delete hash/signature) is **REJECTED (inferior)** — triggers "Not a genuine Artisan profile" warning on every load.

---

## 4. Manual Check (GUI) — required before M4

Perform the following steps in Artisan to verify behavior with hash/signature fields:

1. **Version check:** Note the installed Artisan version (must be v4.2+ to test the hash/signature path; the corpus contains v4.2.0 files).

2. **Baseline (original file):** Open `C:\Users\guill\AppData\Local\Temp\m0_experiment\v4.2.0_2026-10-04.alog` in Artisan — confirm it loads with no warning. Open the cupping/flavors dialog and note what the radar, labels, notes, and defect flags show (this is the baseline).

3. **Stale hash/signature test:** Open `v4.2.0_2026-10-04_rewritten.alog` (sensory fields changed, STALE hash/signature) — record:
   - Does it load?
   - Any integrity/hash/signature warning or refusal?
   - In the cupping dialog, are the new radar values `[8.5, 7.5, 9.0, 8.0, 8.5, 8.0, 9.0, 8.5, 8.0]`, the custom flavor labels, the note `"Bright citrus, floral jasmine, honey sweetness, clean finish"`, and the tipping/scorching defect flags visible?

4. **Re-save stale hash file:** Re-save the rewritten file from Artisan and re-open it — do the fields survive? Compare the file's hash/signature values before and after the Artisan save (they should be recomputed by Artisan if it maintains them).

5. **No-hash test:** Open `v4.2.0_2026-10-04_nohash.alog` (hash/signature DELETED — the design M4 will use) — does Artisan load it without complaint? Do the sensory fields show? Re-save and confirm Artisan recreates hash/signature.

6. **Pre-4.2 test:** Open `v2.10.4_2024-08-03_rewritten.alog` (pre-4.2, no hash/signature concept) — loads cleanly? fields visible? survive re-save?

7. **Go/No-Go criteria:**
   - **GO** for M4 if all files load without blocking warnings, fields are visible, and fields survive an Artisan re-save.
   - If the stale-hash file triggers a blocking warning but the no-hash file is clean, M4 uses the delete-hash/signature design.
   - If the no-hash file is also blocked, M4 is **NO-GO** for v4.2 files (restrict native sync to pre-4.2, or reverse-engineer the hash algorithm).

---

## 5. Manual check outcomes (Artisan 4.2.0 GUI, 2026-10-23)

Manual GUI verification was performed on Artisan 4.2.0 (official build, revision 9334ed7) against the user's real corpus.

| Test | File | Result |
|---|---|---|
| Baseline | Original anonymized v4.2.0 fixture | Loads cleanly, no warning |
| Stale hash/signature | Rewritten v4.2.0 (sensory fields changed, stale hash) | "Modified Artisan profile. Load it anyway?" warning; loads on Yes; radar values, custom labels, tipping+scorching visible in cupping dialog; cupping note visible under Roast → Properties → Cupping Notes |
| No-hash copy | v4.2.0 copy with hash+signature deleted | "Not a genuine Artisan profile. Load it anyway?" warning; loads on Yes; user re-saved it in Artisan; the re-saved file now has fresh `hash` `7857c22798b0025d817ef06ce1b2914535907aa7aa9fe2ad63ce42531f540108` and `signature` `c9cc0985...`; **the fresh hash verifies against the algorithm → heal-on-resave proven** |
| Pre-4.2 rewritten | Rewritten v2.10.4 copy | Opens **without warning**, notes visible. (An earlier report of "same warning" for this file was a misattribution; the disassembly and the re-test agree: pre-4.2 files skip both checks.) |

**Conclusion:** The stale-hash warning is non-blocking (Yes loads anyway), but the no-hash copy triggers a different warning. The heal-on-resave behavior confirms Artisan can regenerate valid hash/signature.

---

## 6. Artisan 4.2 profile integrity (reverse-engineered)

Integrity machinery in Artisan 4.2.0 official builds (`artisanlib/main.py` `ApplicationWindow.validateProfileDict`, disassembled from the bundled pyc; `artisanlib/util.py` `rec_int_to_float`, `signature_message`):

1. On load, the profile dict is first reduced by pydantic `TypeAdapter(ProfileData).validate_python(...)` (schema = `ProfileData` TypedDict in `artisanlib/atypes.py`, 210 keys). Unknown keys are dropped, values coerced. **On genuine Artisan-written files this reduction is the identity** (verified: 0 keys dropped, 0 values changed on 10 genuine v4.2 files).
2. Signature check (only if official build AND `validate_signature` AND `version >= 4.2`): loads bundled `artisan_public_key.pem` (Ed25519) and verifies `profile['signature']` (hex) over `signature_message(version, revision, artisan_os)` = `bytes(f"{version}{revision}{artisan_os}", "ascii")`. **The signature covers only version+revision+artisan_os — NOT the profile content.** Verified 10/10 against the user's corpus with the bundled public key. Any failure (incl. missing `signature` key) → dialog "Not a genuine Artisan profile. Load it anyway?".
3. Hash check (only if `'hash'` in profile): `computed = sha256(json.dumps(rec_int_to_float(profile_minus_hash), sort_keys=True, ensure_ascii=True, separators=(',',':')).encode()).hexdigest()`; mismatch → dialog "Modified Artisan profile. Load it anyway?" (Yes loads anyway, Cancel aborts the load). `rec_int_to_float` converts **every int to float, including bools** (`True` → `1.0`), recursing into dicts (copied) and lists; all other types unchanged. (A bool-excluding reimplementation produces wrong hashes — this was verified the hard way.)
4. On save (`getProfile`, main.py ~line 17310), Artisan builds the profile from `ProfileData()`, assigns `signature` (line 17039) **before** computing `hash` (line 17310) — so the stored hash covers the signature value.
5. Pre-4.2 profiles have no `hash`/`signature` keys; version < 4.2 skips the signature check and the absent `hash` skips the hash check → **no warnings on load**.

Verification evidence:
- The stdlib reimplementation `sha256(json.dumps(rec_int_to_float(profile_minus_hash), sort_keys=True, ensure_ascii=True, separators=(',',':')).encode()).hexdigest()` reproduces the stored hash **10/10**: all 9 v4.2.0 files in the user's corpus (`C:\Users\guill\ai\coffee\Artisan\logs`, read-only) plus the user's re-saved test file.
- The same computation ground-truthed against the **real** pydantic 2.13.4 `TypeAdapter(ProfileData)` loaded from the extracted bundled pyc (`atypes.pyc`, `plus/stock.pyc`): 10/10 match, validation identity on genuine files.
- Ed25519 signature verification with the bundled `C:\Program Files\Artisan\artisan_public_key.pem`: 10/10 valid; message is version+revision+artisan_os only (content-independent; identical signature `c9cc0985...` observed across different re-saves).

---

## 7. M4 design decision

**Status: GO**

For profiles with version >= 4.2 (practically: those carrying `hash`/`signature`): write the sensory fields, **keep the original `signature` untouched** (it stays valid — it is content-independent), and **recompute `hash`** with the exact algorithm above over the final written dict minus `hash`. Result: Artisan loads the file with **zero warnings**.

For pre-4.2 profiles: write the sensory fields only; never add `hash`/`signature`.

Deleting `hash`/`signature` (previous option in section 3.4) is **REJECTED (inferior)**: it triggers "Not a genuine Artisan profile" on every load.

Caveat: the hash covers the pydantic-reduced profile. Genuine files are schema-conformant (verified). The writer must therefore write sensory values in canonical types (`flavors`: list of floats, `flavorlabels`: list of strings, `cuppingnotes`: string, defect flags: bools) and must refuse to sync a file that contains keys outside the bundled 4.2.0 `ProfileData` schema (Artisan would drop them at load before hashing, invalidating a whole-dict hash).

---

## 8. Outcome

M0 experiments complete. Manual check confirms:
- Stale hash triggers non-blocking "Modified Artisan profile" warning
- No-hash triggers non-blocking "Not a genuine Artisan profile" warning
- Heal-on-resave proven: Artisan regenerates valid hash/signature
- Pre-4.2 files load without warnings

**M4 native sync is GO** with the recompute-hash design.

**Note:** All test files live in `C:\Users\guill\AppData\Local\Temp\m0_experiment\` and can be regenerated with `research/rewrite_native_fields.py` and `research/prepare_nohash_copy.py`.
