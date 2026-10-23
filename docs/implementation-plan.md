# Implementation Plan — artisan-companion

Sequel to [feasibility-evaluation.md](feasibility-evaluation.md). Assumes the
hybrid storage model decided there: sidecar store keyed by `roastUUID`
(system of record) plus opt-in sync of native Artisan sensory fields.

> **Milestone status:** M0–M4 complete; M5 in progress; HEAD commit `d6c4538`.

## 0. Scope and non-goals

The app **complements existing `.alog` files offline, after the fact**. Sensory
information (cupping scores, descriptors, defects) is only available days or
weeks after the roast, once the beans are rested and brewed — it can never be
captured during roasting in Artisan. That gap is the app's entire reason to
exist.

Non-goals (out of scope by design):

- any live interface with a running Artisan instance (telemetry, recording,
  events, alarms, profile pushing);
- acting as a roasting tool or logging replacement;
- batch edits across many logs without explicit per-roast review.

Consequences for the architecture below: there is no daemon, no watcher, and
no Artisan-side component. The app reads the logs folder (or a copied corpus),
annotates, and renders. The only contact point with Artisan is the opt-in,
backup-first write of native sensory fields into the `.alog` files
(milestone M4) — which is exactly the "complement existing files" feature,
executed on closed files.

---

## 1. Architecture

```
┌─────────────────────────── artisan-companion ────────────────────────────┐
│                                                                           │
│  .alog logs ──► alog core (parser + profile model) ──► profile viewer     │
│      │                            │                                       │
│      │                     roast index (SQLite)                            │
│      │                            ▲                                       │
│      └── roastUUID ──► sensory store (JSON sidecars) ──► sensory editor    │
│                                                                           │
│  native-sync writer (opt-in): sensory store ──► flavors/cupping/defects    │
│                               written back into .alog (with backup)      │
└───────────────────────────────────────────────────────────────────────────┘
```

Four components, built in this order:

1. **`alog` core library** — parse `.alog` into a typed profile model; derived
   metrics (RoR, phases, event timeline). Pure Python, stdlib-only parser,
   zero dependencies for this layer. Reuse the proven `ast.literal_eval` +
   unicode-unescape logic from the existing extraction pipeline.
2. **Sensory store** — one JSON sidecar per roast: `<roastUUID>.json` in a
   `sensory/` folder next to the logs (configurable), plus a small SQLite index
   for listing/search. JSON is human-readable, git- and sync-friendly.
3. **Sensory editor** — form-driven entry of cupping sessions (SCA scores),
   aroma descriptors, defects, overall rating; renders the native flavor
   radar for parity with Artisan.
4. **Profile viewer** — Artisan-style graph (BT/ET curves, RoR, event flags,
   phase shading, DRY/FCs/DROP markers) with sensory data shown alongside;
   background-profile comparison via `backgroundUUID`.

## 2. Sensory data model (v1 draft)

Sidecar JSON, one file per roast, keyed by `roastUUID`:

```json
{
  "schema_version": 1,
  "roast_uuid": "41bc74340a464d98a8156045b5bfc495",
  "roast_ref": { "file": "Abricot 5_24-08-03_2018.alog", "date": "2024-08-03" },
  "cuppings": [
    {
      "date": "2024-08-05",
      "days_after_roast": 2,
      "scores": {
        "fragrance_aroma": 8.0, "flavor": 8.5, "aftertaste": 7.5,
        "acidity": 8.5, "body": 7.0, "balance": 8.0,
        "uniformity": 10.0, "clean_cup": 10.0, "sweetness": 8.0,
        "overall": 8.5, "defects": 0, "total": 86.5
      },
      "descriptors": ["apricot", "stone fruit", "black tea", "floral"],
      "notes": "Very vibrant, expected acidity came through."
    }
  ],
  "radar": {
    "labels": ["Acidity", "Aftertaste", "Clean Cup", "Head", "Fragrance",
                "Sweetness", "Aroma", "Balance", "Body"],
    "values": [8.5, 7.5, 10.0, 7.0, 8.0, 8.0, 8.5, 8.0, 7.0]
  },
  "defects_observed": { "tipping": false, "scorching": false },
  "native_sync": { "last_synced": "2026-10-21T09:00:00", "fields": ["radar", "cuppingnotes"] },
  "media": [{ "kind": "photo", "path": "../photos/abricot5_bag.jpg" }]
}
```

Mapping to native Artisan fields (opt-in sync):
`radar.values` → `flavors`, `radar.labels` → `flavorlabels`,
`cuppings[0].notes` → `cuppingnotes`, `defects_observed` → the ten defect
booleans. Anything else (cupping history, media, descriptors) stays sidecar-only.

## 3. Tech stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Same ecosystem as Artisan; proven parser logic already exists; natural for data work |
| Core library | stdlib only (`ast`, `json`, `sqlite3`, `pathlib`) | The parser must stay dependency-free to be trustworthy and trivially installable |
| App/UI | Local web app: FastAPI + small frontend (Plotly or lightweight chart lib) | Cross-platform without Qt licensing/size; charts are strong; runs offline at `localhost` |
| Packaging | PyInstaller single binary (later) | For non-Python users; deferred to a late milestone |
| Tests | pytest with a reduced multi-version fixture corpus | Every Artisan version 2.4.6–4.2.0 represented; golden-file parse tests |

Rejected alternatives: PyQt desktop clone (heavier, duplicates Artisan UX),
Electron (runtime weight), Electron-free pure-Python TUI (poor charts for the
viewer).

## 4. Milestones

| # | Milestone | Scope | Exit criteria | Status |
|---|---|---|---|---|
| M0 | Pre-flight experiments | R-1 round-trip test (rewrite copy of a v4.2 log with native fields; open in Artisan; check warning/behavior). R-2: confirm unknown-key load tolerance on all 7 corpus versions with file copies | Written findings in research/; go/no-go for native sync | Done |
| M1 | `alog` core library | Loader, profile model, unescape, RoR, phases, event timeline, roast index build | Parses 230/230 corpus files; published as `pip install`-able package skeleton | Done |
| M2 | Sensory store + editor | Sidecar JSON schema v1, CRUD UI for cupping sessions, radar editor, search/list | Can annotate a roast end-to-end; store survives app restarts; original `.alog` untouched | Done |
| M3 | Profile viewer | Artisan-style chart with events/phases/RoR, roast list, side-by-side sensory panel | A roast renders visually equivalent to Artisan's graph for the corpus sample | Done |
| M4 | Native sync (opt-in) | Backup-then-write of `flavors`/`flavorlabels`/`cuppingnotes`/defect flags; keep signature + recompute hash for v4.2+ (zero-warning writes); nothing added for pre-4.2; sync audit trail; refusal on unknown schema keys | Round-trip verified against Artisan versions available locally; gated on M0 results | Done |
| M5 | Public release prep | License, README, CI (pytest + fixture corpus), packaging, sample gallery | First tagged GitHub release | In progress |

## 5. Repository layout (target)

```
artisan_companion_app/
├── README.md
├── LICENSE                      # MIT License
├── pyproject.toml               # package: alog_core + app
├── .gitignore
├── docs/                        # feasibility, plan, format notes
├── research/                    # evidence collected during evaluation
├── src/
│   ├── alog_core/               # parser, model, metrics (stdlib only)
│   ├── store/                   # sensory sidecars + SQLite index
│   ├── sync/                    # native-field writer (backup-first)
│   └── app/                     # FastAPI + web UI
└── tests/
    ├── fixtures/alogs/          # small anonymized multi-version sample
    └── unit/ …
```

## 6. Open decisions

| Decision | Options | Status |
|---|---|---|
| License | MIT vs Apache-2.0 (AGPL-3.0 is *contagious* — Artisan itself is AGPL; we only read its files, which does not force our license) | **MIT** — decided; `LICENSE` added |
| Project name | `artisan-companion` (working) vs distinct brand (Artisan trademark caution) | **Keep `artisan-companion`** — affiliation disclaimer added to README; revisit branding before any public (non-private) release |
| Distribution | PyPI + zip binary vs GitHub releases only | **GitHub releases first** — decided |
| Viewer tech | Plotly vs D3 vs matplotlib-server-rendered | **Canvas + SVG (vanilla JS)** — M3 shipped a pure HTML/JS viewer using canvas for BT/ET/RoR charts and SVG for the flavor radar; zero external dependencies |

## 7. Guardrails

- Never write to a `.alog` without creating a `.bak` copy first; native sync is
  opt-in and off by default.
- Parser accepts unknown keys and versions defensively (`.get()` everywhere);
  it must never crash on a future Artisan version.
- `ast.literal_eval` only; the app never executes log content.
- All timestamps stored in ISO 8601 UTC plus roast-local offset (the corpus
  shows `roastepoch` + `roasttzoffset` is reliable).
- Fixture files published in the repo must be anonymized (operator, machine
  paths — the corpus contains absolute local paths in `backgroundpath`).
