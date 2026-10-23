# Mobile port plan — artisan-companion on Android

Goal: run artisan-companion on an Android phone as a real, installable,
**fully offline** app, reusing the existing UI and the existing Python core.

> Status: plan + folder reorganization. The Android project is a scaffold
> (see `mobile/android/`); it must be opened and built in Android Studio.
> The Termux path (`mobile/termux/`) works today with no Android toolchain.

---

## 1. Why this app ports well

The prototype was built in a way that happens to be ideal for a phone:

- **Pure-Python core, stdlib only.** `alog_core` (parser), `store` (JSON
  sidecars + SQLite index) and `sync` (native `.alog` writer) depend on
  nothing but the standard library (`ast`, `json`, `sqlite3`, `pathlib`).
  They run unchanged on Android's CPython.
- **Self-contained web UI.** `src/app/frontend.html` and `src/app/viewer.html`
  have all CSS/JS inline, draw charts on `<canvas>`, the radar as inline SVG,
  and reference **no CDN, no external fonts, no remote assets**. The whole UI
  works with zero network.
- **Local-only server.** The FastAPI app binds to `127.0.0.1` and reads local
  files. There is nothing to deploy; on a phone it just serves the device
  itself.
- **Configurable data dirs.** The server already accepts `--logs-dir` and
  `--sensory-dir`, so pointing it at phone storage is a configuration change,
  not a code change.

The one thing that does **not** port is the desktop assumption that "the user
runs a command with CLI flags." On a phone there is no shell, so the Android
wrapper must inject those paths programmatically. The existing `sys.argv`
parsing in `src/app/main.py` is reused as-is: the wrapper sets `sys.argv`
before starting the server.

**No Python source changes are required for the port.**

---

## 2. Options considered

| Option | What it is | Keeps the HTML UI? | Fully offline APK? | Effort | Verdict |
|---|---|---|---|---|---|
| **Termux** | Run the server inside the Termux Linux env on the phone; open Chrome at `127.0.0.1:8000` | Yes | Server is local; needs Termux running | Lowest | **Do now** — works today |
| **Chaquopy** | Android Studio/Gradle app that embeds CPython; Python runs the same FastAPI server on `127.0.0.1`; a WebView loads it | Yes | Yes — real installable APK | Medium | **Recommended APK path** |
| **BeeWare Briefcase + Toga** | Official "Python on Android"; rebuild the UI with native Toga widgets | No — UI rewrite | Yes | High (UI rewrite) | Only if a native UI is wanted |
| **Kivy / KivyMD + buildozer** | Rebuild the UI in Kivy; buildozer makes the APK | No — UI rewrite | Yes | High (UI rewrite); buildozer wants Linux/WSL | Not recommended |
| **PWA** | Install the web UI to the home screen | Yes | Needs the server running (Termux) | Low | Nice add-on to the Termux path |

**Recommendation:** use **Termux** to get the app on the phone this week, then
build the real APK with **Chaquopy**. Both reuse the same Python packages; the
only new code is a thin Android shell (Kotlin WebView + a ~15-line Python
launcher). Toga/Kivy would mean throwing away a UI that already works and is
already offline-capable, so they are only worth considering if you specifically
want native Android widgets.

---

## 3. Recommended architecture (Chaquopy APK)

```
Android app (Kotlin, WebView)
   │  starts CPython via Chaquopy
   │  calls launcher.start_server(logsDir, sensoryDir) on a background thread
   ▼
launcher.py            (mobile/android/app/src/main/python/launcher.py)
   │  mkdir logs/ + sensory/
   │  sys.argv = ["artisan-companion", "--logs-dir", logs, "--sensory-dir", sensory]
   │  uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
   ▼
FastAPI app  (src/app/main.py — unchanged)
   │  startup builds the roast index + opens the sensory store
   ▼
alog_core / store / sync  (src/ — unchanged, stdlib only)
```

- The Gradle project adds the repo's `src/` as a Chaquopy Python source dir, so
  `alog_core`, `store`, `sync` and `app` are **single-sourced** — the APK and
  the desktop app share one copy of the code.
- `fastapi` + `uvicorn` are installed into the embedded Python via Chaquopy's
  `pip {}` block. Both are pure-Python (uvicorn falls back to the stdlib
  asyncio loop on Android; pydantic-core ships manylinux `aarch64` wheels), so
  they run on-device.
- The WebView loads `http://127.0.0.1:8000`. `android:usesCleartextTraffic`
  is enabled because the UI is served over plain HTTP to localhost.
- The server runs entirely on the device; the app needs no network.

### Storage on the phone

The app needs a folder of `.alog` files and a `sensory/` store. Plan:

- **Default:** app-specific external storage
  (`Android/data/com.artisancompanion/files/logs` and `.../files/sensory`).
  No permissions needed, survives updates, wiped on uninstall.
- **User folder (recommended for real use):** let the user pick a folder via
  the Storage Access Framework (SAF, `ACTION_OPEN_DOCUMENT_TREE`) so they can
  point at a Syncthing/Dropbox/USB-synced roast folder. Pass the resulting
  content URI / path to `launcher.start_server` as `--logs-dir`. The sensory
  store can live beside it or stay in app storage.

This is a small addition to the Kotlin shell (an SAF launcher + persisting the
chosen URI), not a change to the Python app.

---

## 4. Folder reorganization

The existing `src/` split already separates the reusable core from the web UI,
which is exactly what mobile needs, so the Python packages are **not moved**.
The reorganization is additive:

```
artisan_companion_app/
├── pyproject.toml              # unchanged (desktop/server packaging)
├── src/
│   ├── alog_core/              # pure python — shared with mobile
│   ├── store/                  # pure python — shared with mobile
│   ├── sync/                   # pure python — shared with mobile
│   └── app/                    # FastAPI web UI — shared with mobile
├── mobile/                     # NEW — everything Android
│   ├── README.md               #   how to build/run both paths
│   ├── android/                #   Chaquopy Gradle project (the APK)
│   │   ├── settings.gradle
│   │   ├── build.gradle
│   │   ├── gradle.properties
│   │   ├── local.properties.example
│   │   └── app/
│   │       ├── build.gradle            # chaquopy plugin + python srcDirs
│   │       └── src/main/
│   │           ├── AndroidManifest.xml
│   │           ├── python/launcher.py  # starts uvicorn with phone paths
│   │           ├── java/.../MainActivity.kt   # WebView shell
│   │           └── res/...
│   └── termux/
│       └── setup.sh            # zero-toolchain install on the phone
├── docs/
│   └── mobile-port.md          # NEW — this plan
├── tests/                      # unchanged
└── README.md                   # + Mobile section
```

`.gitignore` is extended for Gradle/Android artifacts under `mobile/android/`.

---

## 5. Milestones

| # | Milestone | Scope | Exit criteria |
|---|---|---|---|
| P0 | Folder reorg + plan | `mobile/` tree, this doc, README/.gitignore | Done in this change |
| P1 | Termux path works | `mobile/termux/setup.sh`; app runs on phone in Chrome | App reachable at `127.0.0.1:8000` on a real device |
| P2 | Chaquopy scaffold builds | Open `mobile/android` in Android Studio, produces a debug APK | `assembleDebug` succeeds |
| P3 | In-app server + WebView | `launcher.py` + `MainActivity.kt` wired; UI loads in the WebView | Roast list renders inside the app, offline |
| P4 | Storage UX | SAF folder picker for `--logs-dir`; default app storage | User can point at their synced `.alog` folder |
| P5 | Polish | App icon/splash, PWA-style standalone feel, back-button handling, release signing | Installable, signed release APK |

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Chaquopy DSL / plugin version drift (the Gradle snippet may need adjusting to your Android Studio + Chaquopy version) | `mobile/android/` is a scaffold; pin AGP/Kotlin/Chaquopy versions to your toolchain on first open. The Python side (`launcher.py`, srcDirs) is the stable part. |
| `pydantic-core` / `uvicorn` wheels on Android | Both ship manylinux `aarch64` wheels and pure-Python fallbacks; Chaquopy installs them via `pip`. If a wheel is missing, fall back to serving the ASGI app with the stdlib `wsgiref` (see §7). |
| Cleartext HTTP blocked on API 28+ | `android:usesCleartextTraffic="true"` in the manifest (localhost is exempt from the cleartext ban only when configured; we set it explicitly). |
| Server startup race (WebView loads before uvicorn is ready) | `MainActivity` retries the load until the server responds, instead of a fixed delay. |
| Large `.alog` folders on a phone | The SQLite index makes listing fast; the viewer loads one roast at a time. No change needed. |
| Editing `.alog` on Android storage | Native sync (`sync/`) is opt-in and backup-first (`.bak`); on Android prefer keeping the sensory store sidecar-only and syncing on desktop. |

---

## 7. Fallback server (if uvicorn is problematic on-device)

The FastAPI app is a standard ASGI app, so if uvicorn ever causes trouble on
Android it can be served by the standard library with a tiny WSGI/ASGI shim —
or the routes can be re-exposed through `http.server`. This is a contingency,
not the plan: uvicorn is expected to work under Chaquopy.

---

## 8. What is NOT changing

- The Python packages (`alog_core`, `store`, `sync`, `app`) — no source edits.
- The desktop/server workflow (`pip install -e ".[app]"`, `artisan-companion`).
- The test suite — must stay green (298 passed / 1 skipped at the time of
  this plan).
