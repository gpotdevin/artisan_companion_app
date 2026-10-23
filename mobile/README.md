# Mobile (Android)

Two ways to run artisan-companion on an Android phone. Both reuse the same
Python code; neither requires changing the app.

| Path | What you get | Toolchain needed | Time |
|---|---|---|---|
| [`termux/`](termux/) | App runs in Chrome via the Termux Linux env | None (Termux from F-Droid) | ~15 min |
| [`android/`](android/) | A real, installable, fully-offline APK (WebView + embedded Python via Chaquopy) | Android Studio + SDK | A few hours to first build |

The full plan, architecture, risks and milestones are in
[**docs/mobile-port.md**](../docs/mobile-port.md).

## Path 1 — Termux (fastest, no Android toolchain)

Get the repo onto the phone (git clone in Termux, or sync the folder with
Syncthing/Dropbox/USB), then from inside the checkout:

```bash
bash mobile/termux/setup.sh
source .venv-mobile/bin/activate
artisan-companion --logs-dir ./logs
```

Open Chrome at `http://127.0.0.1:8000`. Use Chrome's *Add to Home screen* to pin
it like an app.

## Path 2 — Chaquopy APK (real app)

`android/` is a Gradle project that embeds CPython with
[Chaquopy](https://chaquo.com/chaquopy/) and loads the existing web UI in a
WebView. The Python packages (`alog_core`, `store`, `sync`, `app`) are
**single-sourced** from the repo's `src/` via a Gradle `python.srcDir` — the
APK and the desktop app share one copy of the code.

> This is a **scaffold**: it is meant to be opened in Android Studio and built
> there. It has not been compiled in this environment (no Android SDK here).
> On first open, align the AGP/Kotlin/Chaquopy plugin versions in the root
> `build.gradle` with your toolchain, create `local.properties` from
> `local.properties.example`, and run `assembleDebug`.

```bash
# 1. Copy local.properties.example -> local.properties and set sdk.dir
# 2. Open mobile/android in Android Studio, or from the command line:
cd mobile/android
./gradlew assembleDebug        # Linux/macOS
gradlew.bat assembleDebug      # Windows
# Install on a connected phone:
./gradlew installDebug
```

The app starts the FastAPI server on `127.0.0.1:8000` inside the embedded
Python (`app/src/main/python/launcher.py`) and the WebView loads it. Storage
defaults to app-specific external files
(`Android/data/com.artisancompanion/files/`); see
[docs/mobile-port.md §3](../docs/mobile-port.md) for wiring a user-picked
folder via the Storage Access Framework.
