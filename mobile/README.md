# Mobile (Android) — native Kotlin app

artisan-companion runs on Android as a **native Kotlin (Jetpack Compose) app**,
fully offline. The UI is native Material 3; the proven Python core
(`alog_core`, `store`, `sync`) is embedded via [Chaquopy](https://chaquo.com/chaquopy/)
and called through a thin JSON facade (`app/src/main/python/api.py`). No Python
source in `src/` is modified.

Full plan, architecture, storage model, milestones and risks:
[**docs/mobile-port.md**](../docs/mobile-port.md).

## Build the APK

`android/` is a Gradle project. On this machine everything needed to build and
install is already wired into the folder:

- `gradlew` / `gradlew.bat` + `gradle/wrapper/` — Gradle 8.7 wrapper.
- `local.properties` — points at the shared Android SDK in `~/dev/tools/android-sdk`.
- `tools/platform-tools/` — directory junction to the SDK's `platform-tools`
  (gives `adb` for direct installs). Machine-specific, gitignored.

```bash
cd mobile/android

# One-command build (bash):
./build.sh
# ...or (cmd):
build.cmd

# One-command build + install on a connected phone (USB debugging on):
./install.sh                   # bash — gradle installDebug, adb fallback, then launches the app
install.cmd                     # cmd equivalent

# Raw Gradle still works:
./gradlew assembleDebug         # Linux/macOS/Git Bash
gradlew.bat assembleDebug       # Windows
```

Requirements: Java 17 on PATH (JBR 17.0.14 on this machine). No other setup —
`local.properties` already exists; on a different machine copy it from
`local.properties.example` and set `sdk.dir`.

On first open, Android Studio may ask to align AGP/Kotlin/Compose/Chaquopy
versions — the pinned set in `build.gradle` / `app/build.gradle` is a
known-good starting point (AGP 8.5.0, Kotlin 1.9.22, Compose Compiler 1.5.8,
Compose UI 1.5.3, Material3 1.1.2, Material 1.11.0, Chaquopy 16.0.0,
Gradle 8.7, compileSdk 34, minSdk 24, targetSdk 34).

## Release signing

Release builds require a keystore. Secrets come from environment variables
only — nothing sensitive is committed to the repo.

### Local release build

```bash
cd mobile/android
export ARTISAN_RELEASE_STORE_FILE=../../../../ArtisanCompanion.keystore  # path from app/ module
export ARTISAN_RELEASE_STORE_PASSWORD=<your-store-password>
export ARTISAN_RELEASE_KEY_ALIAS=ArtisanCompanion_app
export ARTISAN_RELEASE_KEY_PASSWORD=<your-key-password>
./gradlew :app:assembleRelease :app:bundleRelease
```

The keystore lives **outside the repo** (same pattern as runBeat):
`../ArtisanCompanion.keystore` relative to the repo root.

### CI release build

Push a git tag (`git tag v0.1.0 && git push origin v0.1.0`) to trigger
`.github/workflows/release.yml`, which builds signed AAB + APK and creates
a GitHub Release. See [docs/ci-setup.md](../docs/ci-setup.md) for the
required GitHub Secrets.

### Version numbering

- `versionCode` — read from `build-counter.txt` (monotonically increasing
  integer, required by Play Store). Increment before each release.
- `versionName` — set via `-PversionName` in CI (derived from the git tag),
  defaults to `0.1.0` for local builds.

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
