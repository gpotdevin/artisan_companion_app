#!/usr/bin/env bash
# Build the debug APK.
# Requires: Java 17 on PATH, Android SDK at the path in local.properties
# (auto-provisioned here via the junction in tools/ and local.properties).
set -e
cd "$(dirname "$0")"

if ! command -v java >/dev/null 2>&1; then
    echo "ERROR: java (17) not found on PATH." >&2
    echo "This machine uses JBR 17: C:\\Users\\guill\\.jdks\\jbr-17.0.14" >&2
    exit 1
fi

./gradlew assembleDebug "$@"
echo
echo "APK: app/build/outputs/apk/debug/app-debug.apk"
