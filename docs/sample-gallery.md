# Sample Gallery — artisan-companion

This document showcases the 7 anonymized `.alog` test fixtures included in
`tests/fixtures/alogs/`. Each file is a copy of one roast log from a real
Artisan corpus, with identifying information removed. Together they exercise
all Artisan versions from 2.4.6 to 4.2.0.

## The Fixtures

| Fixture | Artisan Version | Roast Date (ISO) | Notable Characteristics |
|---|---|---|---|
| `v2.4.6_2021-11-19_multiline.alog` | 2.4.6 | 2021-11-19 | French locale (`etypes` = Air/Tambour/Vanne/Bruleur); pretty-printed multi-line pydump variant; CHARGE/FCs/DROP markers present, DRY not marked; 151 keys |
| `v2.6.0_2022-09-16.alog` | 2.6.0 | 2022-09-16 | 21 events recorded; standard single-line format; CHARGE/FCs/DROP marked; first Windows-recorded generation in the corpus |
| `v2.8.2_2023-04-09.alog` | 2.8.2 | 2023-04-09 | CHARGE/FCs/DROP markers present, DRY not marked |
| `v2.10.0_2024-04-02.alog` | 2.10.0 | 2024-04-02 | First 2.10.x generation in the corpus; key set drops `beansize` and adds `default_etypes` vs 2.8.2 |
| `v2.10.4_2024-08-03.alog` | 2.10.4 | 2024-08-03 | `roastUUID` matches `UUID_A` used in the M2a store tests |
| `v3.2.0_2026-07-23.alog` | 3.2.0 | 2026-07-23 | Full marker set: CHARGE/DRY/FCs/DROP all marked |
| `v4.2.0_2026-10-04.alog` | 4.2.0 | 2026-10-04 | v4 key set (`hash`, `signature`, `bbp_*`, PID config keys); full marker set: CHARGE/DRY/FCs/DROP all present; 196 keys |

Key-set drift across versions: 151 keys (2.4.6) → 196 keys (4.2.0).

## How to View

1. Install the app (development):
   ```bash
   pip install -e ".[app]"
   ```

2. Run the app:
   ```bash
   artisan-companion --logs-dir tests/fixtures/alogs
   ```

3. Open the viewer in your browser:
   - Navigate to `http://127.0.0.1:8000/` to see the library, then click on a roast
   - Or open directly: `http://127.0.0.1:8000/viewer?uuid=<roast-uuid>`

   To get a fixture's UUID, parse its `roastUUID` field or inspect the library listing.

   Note: the app creates its sensory store next to the logs directory by
   default (`tests/fixtures/sensory/`, gitignored); pass `--sensory-dir PATH`
   to keep it elsewhere.

4. The profile viewer shows:
   - BT/ET temperature curves over time
   - Rate of Rise (RoR) curve
   - Event markers (CHARGE, DRY, FCs, DROP, etc.) as vertical lines
   - Phase shading (Drying, Maillard, Development) derived from marker times
   - Sensory summary panel (radar chart, cupping history)

## Per-Version Notes

### Artisan 2.4.6
- **Locale**: French — `etypes` uses `Air/Tambour/Vanne/Bruleur` (Air/Drum/Van/Burner) instead of English event type labels
- **Format**: Pretty-printed multi-line pydump variant
- **Markers**: CHARGE, FCs, DROP present; DRY not marked
- **Viewer**: Renders correctly; event type labels display as stored (French)
- **Native sync**: Fields only; no `hash`/`signature` added (pre-4.2); loads without warning in Artisan

### Artisan 2.6.0
- **Events**: 21 events recorded — useful for testing event timeline rendering
- **Format**: Standard single-line pydump
- **Markers**: CHARGE, FCs, DROP marked
- **OS**: First Windows-recorded generation in the corpus (all 2.4.6 corpus files are Mac OS X)
- **Viewer**: All 21 events appear as flags on the ET curve
- **Native sync**: Fields only; no `hash`/`signature` added; loads without warning

### Artisan 2.8.2
- **Markers**: CHARGE, FCs, DROP present; DRY not marked
- **Viewer**: Phase boundaries are derived from available markers (Drying phase extends from CHARGE to FCs)
- **Native sync**: Fields only; no `hash`/`signature` added; loads without warning

### Artisan 2.10.0
- **Note**: First 2.10.x generation in the corpus; key set drops `beansize` and adds `default_etypes` vs 2.8.2
- **Markers**: Standard set
- **Viewer**: Full profile rendering
- **Native sync**: Fields only; no `hash`/`signature` added; loads without warning

### Artisan 2.10.4
- **Reference**: `roastUUID` matches `UUID_A` used in M2a sensory store tests — useful for testing sidecar lookup
- **Viewer**: Full profile rendering; sensory data (if present in sidecar) displays alongside
- **Native sync**: Fields only; no `hash`/`signature` added; loads without warning

### Artisan 3.2.0
- **Markers**: Full set — CHARGE, DRY, FCs, DROP all marked
- **Viewer**: All three phase regions are shaded (Drying, Maillard, Development)
- **Native sync**: Fields only; no `hash`/`signature` added (pre-4.2); loads without warning

### Artisan 4.2.0
- **Integrity fields**: `hash` (64-character hex) and `signature` (128-character hex) present
- **Key set**: 196 keys including v4-specific `bbp_*`, PID configuration fields
- **Markers**: Full set — CHARGE, DRY, FCs, DROP all present
- **Viewer**: Full profile rendering with all phases shaded
- **Native sync**: Zero-warning on load — hash is **recomputed** after writing sensory fields; `signature` is preserved (it is content-independent in Artisan 4.2); the file loads in Artisan with no integrity warnings

## What the Viewer Shows

For all fixtures, the profile viewer renders:

- **Temperature curves**: BT (red) and ET (blue) over time from CHARGE
- **RoR curve**: Grey dashed line showing rate of temperature rise for BT
- **Phase shading**: Color-coded backgrounds for drying, Maillard, and development phases
- **Markers**: Vertical lines at CHARGE, DRY, FCs, DROP positions with colored dots on the curves
- **Events**: Small triangular flags on the ET curve at event times
- **Sensory panel**: Radar chart for flavor attributes; cupping history with scores and descriptors

For v4.2.0 fixtures specifically, the metadata panel shows the `artisan_version` as "4.2.0".

## Native Sync Behavior by Version

| Artisan Version | Sync Behavior | Artisan Load Result |
|---|---|---|
| 2.4.6 – 3.x.x | Writes sensory fields only; does **not** add `hash`/`signature` | Loads without warning |
| 4.2.0+ | Writes sensory fields; **recomputes `hash`**; preserves `signature` | Loads with zero warnings — integrity verified |

The native sync always creates a `.bak` backup of the original file before writing, and maintains an audit trail. For v4.2+ files, the hash recomputation uses the exact algorithm extracted from Artisan 4.2.0 (SHA-256 over canonical JSON representation with int→float conversion). See [research/m0-roundtrip.md](research/m0-roundtrip.md) for full details.
