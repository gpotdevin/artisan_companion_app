# Mobile port plan — artisan-companion as a native Android app

Goal: run artisan-companion on an Android phone as a **native Kotlin
(Jetpack Compose) app**, fully offline, with the proven Python core doing the
parsing and storage.

> Status: plan + folder reorganization + native app scaffold. The Android
> project (`mobile/android/`) is a scaffold to open and build in Android Studio;
> it is **not compiled in this environment** (no Android SDK here). The Python
> facade (`api.py`) is validated end-to-end against the real `.alog` fixtures.

---

## 1. Decision: native Kotlin UI + Python core (Chaquopy)

The app is now a **native Android app**, not a WebView wrapper. Two layers:

- **UI — Kotlin / Jetpack Compose (Material 3).** Native screens, navigation,
  and charts drawn on Compose `Canvas` (no web, no charting dependency):
  roast library, Artisan-style profile viewer (BT/ET/RoR, phase shading,
  markers), sensory editor (flavor radar, defect flags, cupping form),
  settings/import.
- **Core — Python, unchanged, embedded via Chaquopy.** `alog_core`, `store` and
  `sync` are pure stdlib and battle-tested (298 tests). A thin facade
  (`api.py`) exposes them to Kotlin as JSON-returning functions.

```
Compose UI (Kotlin)
   │  Repository (Dispatchers.IO)  ── JSON ──
   ▼
PythonBridge  (Chaquopy: Python.getInstance().getModule("api"))
   │  callAttr("list_roasts" | "get_profile" | "add_cupping" | ...)
   ▼
api.py  (mobile/android/app/src/main/python/api.py)  ── thin facade, same JSON
   │                                                 contract as the web app
   ▼
alog_core / store / sync  (src/ — UNCHANGED, stdlib only)
```

### Why not pure Kotlin (rewrite the core)?

The `.alog` parser is subtle and versioned: it reverse-engineers Artisan's
Python-repr pydump (`ast.literal_eval` + unicode unescape), tolerates key sets
across Artisan 2.4.6–4.2.0, and the M4 native sync recomputes the Artisan 4.2
integrity hash so files load with zero warnings. Reimplementing that in Kotlin
would duplicate ~1500 lines of tested logic and risk divergence. Chaquopy embeds
CPython in the APK, so the core runs as-is. The cost is APK size (see §6).

If you ever want **zero Python**, that is a separate, much larger rewrite —
not recommended.

---

## 2. Why this still ports cleanly

- **Pure-Python core, stdlib only.** `alog_core`, `store`, `sync` need nothing
  but `ast`, `json`, `sqlite3`, `pathlib`, `hashlib`, `re`, `datetime`. They run
  unchanged in Chaquopy's embedded CPython. **No `pip` installs are required.**
- **A clean, JSON data contract already exists.** The FastAPI app
  (`src/app/main.py`) exposes every operation the UI needs as JSON. The native
  facade `api.py` mirrors that contract exactly, so the native app and the web
  app are interchangeable and the Kotlin models (`data/Models.kt`) are a
  direct mapping.
- **Configurable data dirs.** The core takes `--logs-dir` / `--sensory-dir`;
  on Android these become app-specific storage paths injected by Kotlin.

**No Python source in `src/` is modified for the port.** The only new Python
file is the facade `api.py`.

---

## 3. Storage on the phone

- **Default:** app-specific external storage
  (`Android/data/com.artisancompanion/files/logs` and `.../files/sensory`).
  No runtime permission needed; survives updates; wiped on uninstall.
- **Importing roasts:** Settings → "Import .alog files" uses the Storage Access
  Framework (`OpenMultipleDocuments`) to let the user pick `.alog` files, which
  are copied into the app's `logs/` folder (`data/FileImport.kt`). The Python
  core then indexes real filesystem paths — unchanged. (v1 copies files in;
  a future version can read SAF trees directly without copying.)
- **Native sync (`sync/`):** stays **off** on Android for v1 — sensory data is
  sidecar-only. Writing back into `.alog` requires SAF write access to the
  user's original files, which is a later milestone. The sidecar store is the
  system of record and syncs to desktop via the folder.

---

## 4. Folder layout

```
artisan_companion_app/
├── src/                          # UNCHANGED — shared by desktop + mobile
│   ├── alog_core/  store/  sync/ # pure python core
│   └── app/                      # FastAPI web UI (desktop/server)
├── mobile/
│   ├── README.md
│   ├── android/                  # Native Kotlin app (the APK)
│   │   ├── build.gradle  settings.gradle  gradle.properties  local.properties.example
│   │   └── app/
│   │       ├── build.gradle          # Compose + Chaquopy; python.srcDir("../../../src")
│   │       └── src/main/
│   │           ├── AndroidManifest.xml   # no network permission (fully offline)
│   │           ├── python/api.py         # facade over the core (JSON contract)
│   │           └── java/com/artisancompanion/
│   │               ├── MainActivity.kt        # starts Chaquopy, hosts Compose
│   │               ├── ArtisanCompanionApp.kt # theme + NavHost
│   │               ├── data/
│   │               │   ├── Models.kt          # kotlinx.serialization models
│   │               │   ├── PythonBridge.kt    # Chaquopy call wrapper
│   │               │   ├── Repository.kt      # suspend API over the bridge
│   │               │   └── FileImport.kt      # SAF .alog copy into app storage
│   │               └── ui/
│   │                   ├── theme/  (Color.kt, Theme.kt)
│   │                   ├── library/LibraryScreen.kt
│   │                   ├── viewer/ViewerScreen.kt + ProfileChart.kt (Canvas)
│   │                   ├── editor/EditorScreen.kt + RadarChart.kt (Canvas)
│   │                   └── settings/SettingsScreen.kt
│   └── termux/setup.sh           # OPTIONAL: run the web UI in Termux (not native)
├── docs/mobile-port.md           # this plan
└── README.md                     # + Mobile section
```

The Gradle project **single-sources** the Python: `sourceSets { main { python.srcDir("../../../src") } }`
makes `alog_core`, `store`, `sync`, `app` available to the embedded interpreter
from the repo's `src/`, so the APK and the desktop app share one copy of the
code. Only `api.py` lives inside the Gradle project.

---

## 5. Milestones

| # | Milestone | Scope | Exit criteria | Status |
|---|---|---|---|---|
| P0 | Plan + reorg + facade | `docs/mobile-port.md`, `mobile/android/` scaffold, `api.py` | Facade validated vs fixtures | **Done** |
| P1 | Native app builds | Open in Android Studio, `assembleDebug` | Debug APK builds | Open |
| P2 | Library + viewer | `LibraryScreen`, `ViewerScreen` + `ProfileChart` render from the core | Roast list + BT/ET/RoR chart with markers/phases, offline | Open |
| P3 | Sensory editor | `EditorScreen` + `RadarChart`: radar, defects, cupping form | Add/edit cuppings + radar, persisted to sidecars | Open |
| P4 | Import + storage UX | `SettingsScreen` SAF import, rebuild index, empty states | User imports `.alog` files; library populates | Open |
| P5 | Polish | App icon/splash, release signing, back handling, tablet layout | Signed release APK | Open |

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Chaquopy / AGP / Kotlin / Compose version drift — the Gradle files pin a known-good set (AGP 8.5.2, Kotlin 2.0.0, Compose BOM 2024.09.00, Compose Compiler 1.5.14, Chaquopy 16.0.0) | Open in Android Studio and align versions with the Studio template if version checks complain. The Python side is the stable part. |
| APK size — embedded CPython adds ~15–25 MB | Acceptable for a companion app; Chaquopy can strip unused stdlib modules later. |
| Kotlin/Compose code is **uncompiled** here (no Android SDK) | It is a scaffold. Build in Android Studio; expect minor API adjustments (imports, Material3 opt-ins). The data layer (`Models`, `PythonBridge`, `Repository`, `api.py`) is the most stable. |
| `python.srcDir("../../../src")` path | Relative to the `app` module; resolves to the repo `src/`. If packages aren't found, check this path. |
| Threading — Python core does disk I/O | `Repository` wraps every call in `Dispatchers.IO`; the bridge is never called on the main thread. |
| SAF gives content URIs, not paths | v1 copies picked files into app storage so the core sees real paths (see §3). |
| Native `.alog` write-back on Android | Disabled for v1 (sidecar-only); requires SAF write access — later milestone. |

---

## 7. Optional: Termux (non-native, zero toolchain)

`mobile/termux/setup.sh` still runs the **web UI** in Termux + Chrome as a
quick, no-build way to try the data layer on a phone. It is not the native app;
use it only as a stopgap or for development.

---

## 8. What is NOT changing

- The Python packages in `src/` (`alog_core`, `store`, `sync`, `app`) — no edits.
- The desktop/server workflow (`pip install -e ".[app]"`, `artisan-companion`).
- The test suite — must stay green (298 passed / 1 skipped at the time of
  this plan).
