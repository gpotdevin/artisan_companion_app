# artisan-companion (working title)

A companion app for [Artisan](https://artisan-scope.org/) scope users who log their
coffee roasts as `.alog` files and want to attach **sensory information** (cupping
notes, flavor scores, defects) to each roast, and to **review roast profiles**
(curves, events, phases) without opening Artisan.

> Status: M0–M4 complete; 298 tests passed / 1 skipped; CI green; M5 release prep in progress on branch `dev`.

## Goals

1. **Sensory annotation** — add structured sensory data (SCA-style cupping scores,
   aroma descriptors, defects, brew impressions) to existing Artisan `.alog` roast
   logs, in a way that is safe for the original files and, where possible, visible
   inside Artisan itself.
2. **Profile viewer** — render a roast profile (ET/BT curves, RoR, event markers,
   phase boundaries) from a `.alog` file, similar to what Artisan shows, but as a
   lightweight standalone viewer with the sensory data displayed alongside.

## Scope

The app works **offline on existing `.alog` files**, long after the roast
happened — sensory impressions arrive days or weeks later, once beans are
rested and cupped, which is exactly the information that cannot be captured in
Artisan during a roast or shortly after. It deliberately does **not**:

- interface with Artisan while it runs (no live telemetry, no recording,
  no daemon, no plugin or messaging connection);
- replace any part of Artisan's logging workflow.

Artisan only ever re-encounters the data indirectly: when the user opens an
annotated log in Artisan, the sensory summary written to the native fields is
visible there like any data entered in Artisan itself.

## Features

- **stdlib-only `.alog` parser** — Pure Python, zero dependencies for parsing and indexing Artisan roast logs; handles all Artisan versions 2.4.6–4.2.0
- **Sensory store** — JSON sidecar files keyed by `roastUUID` store cupping sessions, flavor radar, defects, and media references; SQLite index for listing/search
- **Sensory editor web UI** — Form-driven entry of cupping sessions (SCA scores), aroma descriptors, defects, overall rating; renders the native flavor radar
- **Profile viewer** — Artisan-style chart with BT/ET curves, RoR, event flags, phase shading (DRY/FCs/DROP markers)
- **Opt-in native sync** — Backup-first write of sensory fields (`flavors`, `flavorlabels`, `cuppingnotes`, defect flags) into `.alog` files; for Artisan 4.2+ the integrity hash is recomputed so files load with zero warnings; a `.bak` backup is always made first

## Install

Development install (from repo root):

```bash
pip install -e ".[app]"
```

The `app` extra provides FastAPI + uvicorn for the web UI. Add the `dev`
extra (`pip install -e ".[app,dev]"`) to also run the test suite.

## Run

Start the local web UI:

```bash
artisan-companion
```

or

```bash
python -m app
```

The app serves on `http://127.0.0.1:8000` by default.

CLI flags:
- `--logs-dir PATH` — directory containing `.alog` files (default: `./logs` or current directory)
- `--sensory-dir PATH` — directory for sensory sidecar files (default: `<logs-dir>/../sensory`)

## Try it with sample data

The repository includes 7 anonymized `.alog` fixtures in `tests/fixtures/alogs/`, one per Artisan version 2.4.6–4.2.0. See `docs/sample-gallery.md` for a detailed gallery and how to view them.

To view a fixture roast, run the app against the fixtures (from the repo root):

```bash
artisan-companion --logs-dir tests/fixtures/alogs
```

Then:

1. Open `http://127.0.0.1:8000/viewer?uuid=<roast-uuid>` in your browser
2. Use the UUID from the fixture's `roastUUID` field, or browse from the library page

The app keeps its sensory store next to the logs directory by default
(`tests/fixtures/sensory/`, gitignored); pass `--sensory-dir PATH` to put it
elsewhere.

## Mobile (Android)

The app runs on an Android phone as a **native Kotlin (Jetpack Compose) app**,
fully offline. The UI is native Material 3 with Canvas-drawn charts; the proven
Python core (`alog_core`, `store`, `sync`) is embedded via Chaquopy and exposed
through a thin JSON facade — no Python source is modified.

- Build the APK from [`mobile/android/`](mobile/android/) (Android Studio).
- See [`mobile/README.md`](mobile/README.md) for build/usage and
  [`docs/mobile-port.md`](docs/mobile-port.md) for the full plan.

A non-native stopgap (web UI in Termux + Chrome) is also available at
[`mobile/termux/`](mobile/termux/).

## Documentation

| Document | Content |
|---|---|
| [docs/feasibility-evaluation.md](docs/feasibility-evaluation.md) | What the `.alog` format allows, what survives a round trip through Artisan, and the verdict |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Architecture, data model, tech stack, milestones, risks |
| [docs/ui-spec.md](docs/ui-spec.md) | Proposed UI specification: screens, wireframes, states, acceptance criteria |
| [docs/mobile-port.md](docs/mobile-port.md) | Android port: native Kotlin (Compose) app + embedded Python core, storage, milestones |
| [docs/sample-gallery.md](docs/sample-gallery.md) | Gallery of the 7 fixture roasts with version-specific notes |
| [research/upstream-findings.md](research/upstream-findings.md) | Evidence collected from the Artisan source code and a 230-file log corpus |
| [research/m0-roundtrip.md](research/m0-roundtrip.md) | Artisan 4.2 integrity findings and native sync design |

## Context

The evaluation was performed against a real corpus of 230 `.alog` files
(2021–2026, Artisan versions 2.4.6 → 4.2.0) and the open-source Artisan code base
(https://github.com/artisan-roaster-scope/artisan). Format analysis details are in
that evidence file and in the pre-existing technical descriptions of the corpus.

## License

MIT — see [LICENSE](LICENSE).

## Affiliation

artisan-companion is an independent project. It is not affiliated with, endorsed by, or sponsored by Artisan (artisan-scope.org). 'Artisan' is a trademark of its respective owners. This project only reads and writes the public `.alog` file format.
