# UI Specification (Proposal v0.1)

Status: **draft proposal** — open for discussion before implementation.
Depends on [feasibility-evaluation.md](feasibility-evaluation.md) (hybrid model:
sidecar store + opt-in native sync) and [implementation-plan.md](implementation-plan.md)
(local web app, offline, no Artisan interaction).

---

## 1. Design principles

1. **Roast-first navigation.** Users think in roasts ("the Abricot 5 batch from
   August 3rd"), not in database rows. Every screen is anchored on a roast.
2. **Non-destructive by default.** Nothing in the UI implies the `.alog` is
   editable. Writing to logs is a deliberate, explicit action (one dialog,
   opt-in, with diff preview).
3. **Artisan parity where it helps recognition.** The profile chart borrows
   Artisan's visual vocabulary (BT red / ET blue, event flags, phase
   background) so roasters feel at home — but simplifies everywhere Artisan's
   density is not needed for post-hoc review.
4. **Cupping workflow is the core loop.** The most frequent action is: "I just
   cupped batch X, record it." Getting from app start to a saved cupping must
   take under 60 seconds.
5. **Everything works offline.** No network calls, no account, no cloud.

## 2. App shell

Single-window layout, three persistent zones:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Top bar   [logo]  Roast Library   Compare   Settings      [dark/light] │
├──────────────┬────────────────────────────────────────────────────────┤
│              │                                                        │
│  Roast list  │                 Main content area                       │
│  (sidebar)   │           (chart / form / table, see screens)           │
│              │                                                        │
├──────────────┴────────────────────────────────────────────────────────┤
│ Status bar  230 roasts · 54 cupped · 3 need rest-check   [last sync…]  │
└──────────────────────────────────────────────────────────────────────┘
```

- **Roast list sidebar** — persistent, scrollable, grouped by month (newest
  first). Each row: date, title, bean (from filename/title if `beans` empty),
  sensory status dot (see 3.1). Keyboard: ↑/↓ move, Enter opens, / focuses
  filter box.
- **Dark theme default**, light available — roasters often review in dim
  environments; matches Artisan's own dark aesthetic.
- Responsive: below ~1100 px the sidebar collapses to a hamburger drawer.

## 3. Screen inventory

| # | Screen | Purpose | Primary user |
|---|---|---|---|
| S1 | Roast Library | Browse/search/filter corpus | All |
| S2 | Roast Detail — Profile view | Artisan-like chart of one roast | All |
| S3 | Roast Detail — Sensory view | Radar, cupping history, defects of one roast | All |
| S4 | Cupping Entry | Record a cupping session | All (core loop) |
| S5 | Compare | Overlay profiles + sensory of 2–6 roasts | Analysis |
| S6 | Native Sync | Write native fields back to `.alog` | Opt-in users |
| S7 | Settings | Folders, units, backup policy, sync defaults | Setup |

### 3.1 S1 — Roast Library

```
┌─────────────────────────────────────────────────────────────────────┐
│ Filter [bean name…    ]  Sort: date▼  | Cupped: all▼  | 2024 (…) ▼   │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────┐  Aug 3, 2024 — Abricot 5                                │
│ │ ~curve~ │  Honduras · 500→431 g · drop 232°C                      │
│ │ thumb   │  ● Cupped 8.5  · radar on file                         │
│ └─────────┘                                                         │
│ ┌─────────┐  Aug 3, 2024 — Abricot 4                                │
│ │ ~curve~ │  Honduras · 400 g · drop 229°C                         │
│ │ thumb   │  ◐ Rested 21d — cup me                              │
│ └─────────┘                                                         │
│ ┌─────────┐  Jul 1, 2024 — cafe 100 4                              │
│ │ ~curve~ │  · drop 231°C                                        │
│ │ thumb   │  ○ Never cupped                                       │
│ └─────────┘                                                         │
└─────────────────────────────────────────────────────────────────────┘
```

- **Row content:** auto-generated sparkline thumbnail (BT curve, ~120×48 px,
  rendered from `timex`/`temp2`), date, title, bean (inferred from title when
  `beans` is empty — corpus-wide inference table from filenames), weights,
  drop temp, sensory status.
- **Sensory status model:**
  - `● cupped` (green): ≥1 cupping session in sidecar; shows best `overall`.
  - `◐ needs cupping` (amber): roast age ≥ rest days (default 7, per-bean
    overridable) and no cupping yet.
  - `○ uncupped` (grey): roast younger than rest days.
  - `⚠ sync pending` (blue badge): sidecar has newer data than last native
    sync (S6).
- **Filters:** bean/name substring, date range, cupped status, drop temp
  range, batch prefix. Search covers sidecar notes too (SQLite index).
- **Actions:** click row → S2; right-click / `...` menu: "Record cupping" (→
  S4 pre-filled), "Compare…" (adds to compare set), "Show in folder".

### 3.2 S2 — Roast Detail, Profile view

```
┌─────────────────────────────────────────────────────────────────────┐
│ Abricot 5 — Aug 3, 2024 · Honduras · Phidget 2xTC · Artisan 2.10.4   │
│ [Profile] [Sensory] [Cupping history] [Events]                ⧉ cmp │
├─────────────────────────────────────────────────────────────────────┤
│ 250°C ┤ ET ╱╲__                                    ⚐ events       │
│       │    ╱   ╲ET ╲          B           ╱BT                       │
│ 200°C ┤ BT╱      ╲       DRY╲               ╲      FCs     DROP      │
│       │ ╱         ╲___      ╲    ___FCs╲    ╲___╱  ⚑       ⚑        │
│ 150°C ┤                ╲____╲__╱      ╲__TP                            │
│       └┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────────  │
│       0:00   2:00   4:00   6:00   8:00  10:00  12:00  (from CHARGE)  │
├─────────────────────────────────────────────────────────────────────┤
│ Phases: DRY 2:16 · MID 5:20 · FIN 1:40   RoR peak 12.4°/min @ 5:10  │
│ Weight 500→431 g (-13.8%) · ambient 34.5°C · sampling 2 s            │
└─────────────────────────────────────────────────────────────────────┘
```

- **Curves:** BT (`temp2`, red, thicker) and ET (`temp1`, blue) on the main
  axis; RoR (derived, °C/min, right axis, light) toggleable, on by default.
- **Time axis zeroed at CHARGE** (`timex[i] − timex[timeindex[0]]`); pre-charge
  region shaded out (dimmed) since it is machine warm-up, not roast.
- **Markers** (from `timeindex`, drawn as verticals + labels): CHARGE, DRY,
  FCs, DROP, COOL. TP derived (BT minimum) — dashed vertical.
- **Phase bands:** subtle background tint for DRY / MID / FINISH phases with
  durations in the summary strip.
- **Events:** flag glyphs (`specialevents`) on the ET curve at event time,
  hover tooltip shows `etypes` label + `specialeventsStrings` physical value
  ("Burner → 30mBar"). Click an event: highlight all events of same type.
- **Interactions:** hover crosshair with time/temp readout; scroll = zoom
  (x-axis only), drag = pan; double-click = reset. "Copy as image" export.
- **Background compare:** if `backgroundUUID` set (or user picks one),
  ghost curves of the reference roast (thin, dashed) overlay.
- **Events tab:** sortable table of all events/markers with absolute +
  roast-relative times; export CSV.
- **Summary strip:** from `computed` + weights: phase durations, RoR stats,
  weight loss, ambient. One line each, no walls of numbers.

### 3.3 S3 — Roast Detail, Sensory view

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Profile] [Sensory] [Cupping history]                                │
├───────────────────────────────┬─────────────────────────────────────┤
│   Flavor radar (as in Artisan) │  Cupping sessions                    │
│        Acidity 8.5             │  ┌ Aug 5 (2d) — 86.5 pts           │ │
│   10 ─────●──────────          │  │ apricot, black tea, floral       │ │
│  Fragrance    Clean Cup        │  │ "Very vibrant, acidity came     │ │
│      8.0 ●      10.0           │  │  through"           [edit][del] │ │
│  Sweetness ●  Aftertaste        │  ├ Aug 12 (9d) — 84.0 pts           │ │
│      8.0        7.5             │  │ …                                │ │
│  Aroma 8.5    Balance 8.0      │  └ [+ Record cupping]               │ │
│      Head 7.0  Body 7.0        │                                      │
│                               │  Defects: none observed              │
│   [edit radar] [sync to alog]  │  Color reading: — · Moisture: —      │
├───────────────────────────────┴─────────────────────────────────────┤
│ Native sync: last written 2026-10-21 · cuppingnotes + flavors ✓      │
└─────────────────────────────────────────────────────────────────────┘
```

- **Radar** renders the exact `flavors`/`flavorlabels` pair (Artisan parity:
  9 axes, start angle 90°, aspect 1.0). Empty state: "no radar scores yet".
- **Cupping sessions** listed newest-first with age at cupping
  (`days_after_roast`), total score, top descriptors, notes snippet.
- **Defects** shown as chips (the ten native flags); toggling writes only to
  the sidecar until S6 sync.
- **Sync status line** with "what Artisan will show" wording — reinforces that
  the sidecar is the source of truth.

### 3.4 S4 — Cupping Entry (core loop)

```
┌───────────────────────────────────────────────────────┐
│ Record cupping — Abricot 5 (roasted Aug 3, 2024)   ✕  │
├───────────────────────────────────────────────────────┤
│ Cupping date [2026-10-21]  Rest days: auto (48d)      │
│ Brew method [filter ▼]                               │
│                                                       │
│ SCA scores (0–10)        Radar preview (live)         │
│  Fragrance/Aroma [8.0]        ╱╲                      │
│  Flavor          [8.5]       ╱  ╲   ← updates as     │
│  Aftertaste      [7.5]      ╱   ╲    sliders move    │
│  Acidity         [8.5]     ●────●                    │
│  Body            [7.0]                               │
│  Balance         [8.0]   Total: [86.5] (auto)        │
│  Uniformity       [10]   Defects: [0]                │
│  Clean cup        [10]                                │
│  Sweetness        [8.0]                               │
│  Overall          [8.5]                               │
│                                                       │
│ Descriptors  [apricot✕] [black tea✕] [+ add          │
│              from lexicon ▼]                          │
│ Notes                                                │
│ ┌─────────────────────────────────────────────────┐ │
│ └─────────────────────────────────────────────────┘ │
│ ☐ Also update this roast's Artisan radar (sidecar    │
│   is always saved first)                              │
├───────────────────────────────────────────────────────┤
│                              [Cancel]  [Save cupping]│
└───────────────────────────────────────────────────────┘
```

- **Total auto-computed** (sum), defect count subtracts.
- **Descriptor lexicon:** curated tag list (fruit/floral/sweet/nutty/cocoa/
  spices/sour/fermented/green/other with sub-tags) with free-text fallback;
  stored in sidecar only.
- **Save order guaranteed:** sidecar JSON written and verified first; the
  optional Artisan-radar update (checkbox, remembers last choice) routes
  through the same safe writer as S6 with automatic `.bak`.
- Keyboard: Tab through scores, Enter saves, Esc cancels.
- After save: toast "Cupping saved · rest-counter cleared", return to S3.

### 3.5 S5 — Compare

- Roster panel (left): pick 2–6 roasts (or a saved set, e.g., "all Abricot").
- **Overlay chart:** BT curves colored per roast; FCs/DROP markers per curve;
  alignment toggle: *by time from CHARGE* vs *by time from FCs* (roasters
  compare development).
- **Sensory table:** roasts as rows, radar axes as columns, cells colored
  (score heat); best-in-column highlighted.
- **Radar multi-polygon:** all selected roasts' radars overlaid.
- Export: chart image, table CSV.

### 3.6 S6 — Native Sync (explicit, opt-in)

```
┌──────────────────────────────────────────────────────┐
│ Write sensory data to Artisan log files               │
├──────────────────────────────────────────────────────┤
│ 3 roast(s) have sidecar data newer than their .alog: │
│                                                       │
│ ✔ Abricot 5  → flavors, cuppingnotes  (backup → .bak) │
│ ✔ cafe 100 4 → flavors, defects      (backup → .bak)  │
│ ☐ Kenya fausto → flavors  ⚠ v4.2 hash/signature file │
│    (M0 experiment not confirmed — blocked)            │
│                                                       │
│ [Preview diff] shows old→new values per field before  │
│ anything is written.                                  │
├──────────────────────────────────────────────────────┤
│              [Cancel]  [Write 2 files (with backup)] │
└──────────────────────────────────────────────────────┘
```

- Reached from Settings (batch) or per-roast (S3/S4). Never automatic.
- Always: `.bak` copy → parse check of the written file → verify by
  re-reading → update sidecar `native_sync` audit entry.
- v4.2 files with `hash`/`signature` are blocked until the M0 experiment
  settles their behavior (risk R-1).

### 3.7 S7 — Settings

- Paths: logs folder, sidecar folder, backup folder. "Scan now" button with
  per-file parse report (link to any unparsable file).
- Rest days default (global + per-bean overrides table).
- Units: °C/°F display (files stay °C; conversion is display-only).
- Sync defaults: enable checkbox default off; which fields (flavors,
  cuppingnotes, defects) participate.
- Import/export: pack sidecar store as zip (backup/move machine).

## 4. States and edge cases

| Situation | Behavior |
|---|---|
| Empty corpus / no logs folder | Onboarding panel: pick folder, what the app does, 3-step setup |
| Unparsable `.alog` | Row shown greyed with ⚠ and error tooltip; never blocks others |
| Roast without `roastUUID` (2 oldest files) | Identity falls back to filename hash; "re-key" prompt if Artisan later adds a UUID |
| Sidecar exists, log missing | Listed in a "orphaned sensory data" section of Settings with export option |
| Duplicate UUID (corpus has candidates) | Grouped visually; merge dialog offers keep-both/merge |
| Long titles / non-ASCII (French) | Unescaped for display; truncation with tooltip |
| Huge corpus (230+ and growing) | Sidebar virtualized; index built incrementally on start (<2 s target) |

## 5. Accessibility and quality bar

- All actions keyboard-reachable; visible focus ring in dark theme.
- Contrast ≥ 4.5:1 for text; chart palettes checked for the two most common
  color-vision deficiencies (BT/ET distinguished also by line style).
- Toasts never auto-dismiss errors; destructive actions (delete cupping,
  write to .alog) always confirm.
- All UI strings behind a translation layer from day 1 (the corpus owner's
  logs mix French and English).

## 6. Open questions for review

1. Radar axes: keep Artisan's default 9 labels vs SCA cupping form categories
   mapped onto the radar? (Proposal: keep Artisan's labels for the *file*
   radar, show SCA form separately in S4 — they serve different purposes.)
2. Should the sparkline thumbnails in S1 be full curves or FCs→DROP segment?
3. Compare alignment "by FCs" — useful enough to keep? (roaster feedback)
4. Naming: "sensory view" vs "cupping view" in tab labels.
5. Whether the rest-days nudge (◐) is worth its noise, or should be a
   filter-only feature.

## 7. Acceptance criteria (v0.1 proposal)

- S1→S4→save round trip under 60 s for an existing roast.
- S2 chart renders visually equivalent to Artisan's graph on the 7-version
  fixture corpus (markers, phases, events positioned correctly).
- All writes to `.alog` files pass: backup created → rewrite → re-parse ok.
- Killing the app at any point never corrupts a sidecar (atomic write via
  temp file + rename).
- No screen requires horizontal scrolling at 1280×800.
