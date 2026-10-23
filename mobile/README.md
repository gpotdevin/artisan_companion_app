# Mobile (Android) — native Kotlin app

artisan-companion runs on Android as a **native Kotlin (Jetpack Compose) app**,
fully offline. The UI is native Material 3; the proven Python core
(`alog_core`, `store`, `sync`) is embedded via [Chaquopy](https://chaquo.com/chaquopy/)
and called through a thin JSON facade (`app/src/main/python/api.py`). No Python
source in `src/` is modified.

Full plan, architecture, storage model, milestones and risks:
[**docs/mobile-port.md**](../docs/mobile-port.md).

## Build the APK

`android/` is a Gradle project. It is a **scaffold** — open it in Android Studio
and build there (it is not compiled in this repo's environment; there is no
Android SDK here).

```bash
cd mobile/android
# 1. Create local.properties from the example and set your SDK path:
cp local.properties.example local.properties   # then edit sdk.dir
# 2. Build a debug APK:
./gradlew assembleDebug        # Linux/macOS
gradlew.bat assembleDebug      # Windows
# 3. Install on a connected phone (USB debugging on):
./gradlew installDebug
```

On first open, Android Studio may ask to align AGP/Kotlin/Compose/Chaquopy
versions — the pinned set in `build.gradle` / `app/build.gradle` is a
known-good starting point (AGP 8.5.2, Kotlin 2.0.0, Compose BOM 2024.09.00,
Compose Compiler 1.5.14, Chaquopy 16.0.0).

### How it fits together

- `app/src/main/python/api.py` — facade over the core. Mirrors the FastAPI JSON
  contract, so the native app and the web app are interchangeable. Validated
  end-to-end against the real `.alog` fixtures.
- `data/PythonBridge.kt` — Chaquopy wrapper (`Python.getInstance().getModule("api")`).
- `data/Repository.kt` — suspend API; every call runs on `Dispatchers.IO`.
- `data/Models.kt` — `kotlinx.serialization` models matching the JSON contract.
- `data/FileImport.kt` — copies SAF-picked `.alog` files into app storage.
- `ui/` — `library`, `viewer` (+ `ProfileChart` Canvas), `editor` (+ `RadarChart`
  Canvas), `settings`, `theme`.

The Gradle project single-sources the Python core from the repo:
`sourceSets { main { python.srcDir("../../../src") } }`.

### Using it

1. Launch the app → it indexes `Android/data/com.artisancompanion/files/logs`.
2. Settings → **Import .alog files** → pick your `.alog` files → they are copied
   into app storage and the index rebuilds.
3. Library lists your roasts; tap one for the profile chart; Edit opens the
   sensory editor (radar, defects, cuppings). Everything is stored in the
   `sensory/` sidecar folder and is fully offline.

Native write-back into `.alog` files (`sync/`) is disabled on Android for v1 —
sensory data is sidecar-only and syncs to desktop via the folder.

## Optional: Termux (non-native, no toolchain)

`termux/setup.sh` runs the **web UI** in Termux + Chrome — a quick, no-build way
to try the data layer on a phone. It is not the native app.

```bash
# In Termux, from a checkout of this repo:
bash mobile/termux/setup.sh
source .venv-mobile/bin/activate
artisan-companion --logs-dir ./logs
# then open Chrome at http://127.0.0.1:8000
```
