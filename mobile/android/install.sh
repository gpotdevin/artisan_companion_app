#!/usr/bin/env bash
# Build and install the debug APK on a connected phone (USB debugging on).
# Uses Gradle's installDebug; falls back to a direct adb install via tools/.
set -e
cd "$(dirname "$0")"

if ! command -v java >/dev/null 2>&1; then
    echo "ERROR: java (17) not found on PATH." >&2
    exit 1
fi

ADB="tools/platform-tools/adb.exe"

if ./gradlew installDebug "$@"; then
    echo "Installed via Gradle."
else
    echo "Gradle installDebug failed - trying direct adb install..."
    "$ADB" wait-for-device
    "$ADB" install -r app/build/outputs/apk/debug/app-debug.apk
    echo "Installed via adb."
fi
"$ADB" shell am start -n com.artisancompanion/.MainActivity 2>/dev/null || true
