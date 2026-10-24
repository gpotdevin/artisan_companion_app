# CI/CD Setup for Artisan Companion

## GitHub Secrets

Configure these secrets in the GitHub repository settings
(Settings → Secrets and variables → Actions → Secrets):

| Secret | Description | How to get it |
|---|---|---|
| `ARTISAN_RELEASE_KEYSTORE_BASE64` | Base64-encoded keystore file | `base64 -w0 ../ArtisanCompanion.keystore` |
| `ARTISAN_RELEASE_STORE_PASSWORD` | Keystore password | Set when creating the keystore |
| `ARTISAN_RELEASE_KEY_ALIAS` | Key alias | `ArtisanCompanion_app` |
| `ARTISAN_RELEASE_KEY_PASSWORD` | Key password | Set when creating the keystore |

## Keystore Location

The keystore is stored **outside the repository** at:

```
../ArtisanCompanion.keystore          (relative to repo root)
```

i.e., `/c/Users/guill/dev/ArtisanCompanion.keystore` (same pattern as runBeat).

A base64-encoded copy is also kept at `../ArtisanCompanion.keystore.b64`
for easy CI secret setup.

## Local Release Build

```bash
cd mobile/android
# Use an absolute path to the keystore (simplest, avoids relative-path confusion):
export ARTISAN_RELEASE_STORE_FILE=/path/to/dev/ArtisanCompanion.keystore
export ARTISAN_RELEASE_STORE_PASSWORD=<password>
export ARTISAN_RELEASE_KEY_ALIAS=ArtisanCompanion_app
export ARTISAN_RELEASE_KEY_PASSWORD=<password>
./gradlew :app:assembleRelease :app:bundleRelease
```

The keystore lives **outside the repo** at `../ArtisanCompanion.keystore`
relative to the repo root (same pattern as runBeat).

## Version Numbering

- `versionCode` is read from `mobile/android/build-counter.txt` (monotonically increasing integer)
- `versionName` is set in `app/build.gradle` (semantic version, e.g., `0.1.0`)
- Increment `build-counter.txt` before each Play Store upload

## Release Flow

1. Update `versionName` in `app/build.gradle`
2. Increment `build-counter.txt`
3. Commit and push to `dev`
4. Create a git tag: `git tag v0.1.0 && git push origin v0.1.0`
5. GitHub Actions builds AAB + APK and creates a GitHub Release
