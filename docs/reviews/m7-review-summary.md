# M7 Review Summary — GitHub Publication Prep

**Date:** 2026-10-24
**Milestone:** M7 — signing, CI/CD, README, screenshots, review fixes
**Commits reviewed:** `9c96a0f` (M7 changes) + `c95bc90` (review fixes)
**Review agents:**
- `review-mistral` — Mistral Large 4 (same model as main agent)
- `review-independent` — generic independent agent (GLM was attempted but config unavailable)

---

## Summary

| Metric | Count |
|---|---|
| **Total findings** | 10 |
| CRITICAL | 2 |
| HIGH | 5 |
| MEDIUM | 3 |
| **All resolved** | **Yes (10/10)** |
| Unaddressed | 0 |

---

## CRITICAL

### C-1: build-counter.txt was untracked

- **Attribution:** at least one agent (both reviews ran in parallel; exact split not recorded)
- **Issue:** `mobile/android/build-counter.txt` was not committed to git. The `versionCode` logic in `build.gradle` reads this file — without it, CI builds would fall back to `1`, causing versionCode collisions on Play Store uploads.
- **Fix:** Committed `build-counter.txt` (content: `1`) to the repo.
- **Files:** `mobile/android/build-counter.txt`

### C-2: versionName was hardcoded in release workflow

- **Attribution:** at least one agent
- **Issue:** The release workflow had a hardcoded `versionName` instead of deriving it from the git tag. Tagging `v0.2.0` would still produce a build labeled `0.1.0`.
- **Fix:** The workflow now strips the leading `v` from `GITHUB_REF_NAME` and passes it via `-PversionName` to Gradle. `build.gradle` reads `project.findProperty('versionName')` with a fallback to `0.1.0`.
- **Files:** `.github/workflows/release.yml`, `mobile/android/app/build.gradle`

---

## HIGH

### H-1: Contradictory environment variable in release.yml

- **Attribution:** at least one agent
- **Issue:** The release workflow contained a contradictory environment variable declaration that could confuse the signing config resolution.
- **Fix:** Removed the contradictory env var. The workflow now sets only `ARTISAN_RELEASE_STORE_PASSWORD`, `ARTISAN_RELEASE_KEY_ALIAS`, and `ARTISAN_RELEASE_KEY_PASSWORD` at the job level; `ARTISAN_RELEASE_STORE_FILE` is set in the "Decode release keystore" step.
- **Files:** `.github/workflows/release.yml`

### H-2: `continue-on-error: true` on Gradle setup step

- **Attribution:** at least one agent
- **Issue:** The Gradle setup step in the release workflow had `continue-on-error: true`, which would mask Gradle initialization failures and produce confusing downstream errors instead of failing fast.
- **Fix:** Removed `continue-on-error` from the Gradle setup step.
- **Files:** `.github/workflows/release.yml`

### H-3: AppCompat theme with ComponentActivity

- **Attribution:** at least one agent
- **Issue:** The app manifest declared an AppCompat theme (`Theme.AppCompat.*`) while the activity extends `ComponentActivity` (not `AppCompatActivity`). This mismatch can cause runtime crashes (`IllegalStateException: You need to use a Theme.AppCompat theme`).
- **Fix:** Created `Theme.ArtisanCompanion` based on `Theme.Material3.DayNight.NoActionBar` in `themes.xml`, added the Material3 dependency (`androidx.compose.material3:material3:1.1.2`), and updated the manifest to reference `@style/Theme.ArtisanCompanion`.
- **Files:** `mobile/android/app/src/main/res/values/themes.xml`, `mobile/android/app/src/main/AndroidManifest.xml`, `mobile/android/app/build.gradle`

### H-4: `java.time` crashes on API 24–25 (Android 7.x)

- **Attribution:** at least one agent
- **Issue:** The app uses `java.time` APIs (`LocalDate`, `YearMonth`) which are not available on Android API 24–25 (Android 7.0/7.1). With `minSdk = 24`, the app would crash with `NoClassDefFoundError` on those devices.
- **Fix:** Enabled core library desugaring: `isCoreLibraryDesugaringEnabled = true` in `compileOptions` and added `coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")` dependency.
- **Files:** `mobile/android/app/build.gradle`

### H-5: Weak keystore password

- **Attribution:** at least one agent
- **Issue:** The release keystore was created with the password `artisan2026` — a weak, guessable password that compromises the signing key if the keystore file leaks.
- **Fix:** Rotated the keystore with a strong random password. The old keystore was replaced; the new password is stored in the session scratchpad (not in the repo). CI secrets (`ARTISAN_RELEASE_STORE_PASSWORD`, `ARTISAN_RELEASE_KEY_PASSWORD`) must be updated to match.
- **Files:** `../ArtisanCompanion.keystore` (outside repo), `../ArtisanCompanion.keystore.b64`

---

## MEDIUM

### M-1: XSS in frontend.html

- **Attribution:** at least one agent
- **Issue:** The HTML frontend (`src/app/frontend.html`) interpolated user-controlled data (cupping descriptors, cupping dates, roast titles, beans, notes) directly into `innerHTML` without HTML escaping. A malicious `.alog` file or sensory sidecar with crafted content could inject arbitrary HTML/JavaScript.
- **Fix:** Added an `escapeHtml()` helper function and applied it to all user-controlled interpolations: roast titles, beans, dates, UUIDs, cupping descriptors, cupping dates, notes, and radar labels.
- **Files:** `src/app/frontend.html`

### M-2: mobile/README.md outdated version numbers

- **Attribution:** at least one agent
- **Issue:** `mobile/README.md` listed incorrect toolchain versions (wrong AGP, Kotlin, Compose, Material, Chaquopy, Gradle numbers) that didn't match the actual pinned versions in the Gradle files.
- **Fix:** Corrected all version numbers to match the actual `build.gradle` files: AGP 8.5.0, Kotlin 1.9.22, Compose Compiler 1.5.8, Compose UI 1.5.3, Material3 1.1.2, Material 1.11.0, Chaquopy 16.0.0, Gradle 8.7, compileSdk 34, minSdk 24, targetSdk 34.
- **Files:** `mobile/README.md`

### M-3: ci-setup.md wrong keystore path

- **Attribution:** at least one agent
- **Issue:** `docs/ci-setup.md` documented an incorrect keystore path and contained a stale `ARTISAN_RELEASE_STORE_FILE` secret reference that contradicted the actual workflow (which decodes the keystore from a base64 secret).
- **Fix:** Corrected the keystore path documentation to `../ArtisanCompanion.keystore` (relative to repo root), removed the stale secret reference, and clarified the local build vs. CI flow.
- **Files:** `docs/ci-setup.md`

---

## Unaddressed Findings

None. All 10 findings were resolved in commits `9c96a0f` and `c95bc90`.

---

## Notes

- **Attribution caveat:** Both review agents ran in parallel. The exact attribution of each finding to a specific agent is not perfectly recorded in the session summary. All findings are attributed as "at least one agent" — it is possible that both agents independently identified some or all of them.
- **Keystore rotation follow-up:** After the keystore password rotation (H-5), the GitHub repository secrets `ARTISAN_RELEASE_STORE_PASSWORD` and `ARTISAN_RELEASE_KEY_PASSWORD` must be updated before the next release build. The new password is in the session scratchpad.
- **CI verification:** The release workflow changes (C-2, H-1, H-2) have not been tested by an actual tag push. The first `git tag v0.1.0 && git push origin v0.1.0` will be the real test.
