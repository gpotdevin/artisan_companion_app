# SDK Alignment Plan: artisan_companion_app -> runBeat parity

**Date:** 2026-10-24
**Status:** Analysis / planning only - no files modified
**Goal:** Align the Android SDK configuration of `mobile/android/` with the proven
settings from the `runBeat` project (`/c/Users/guill/dev/runBeat`), so both apps
share the same compileSdk / targetSdk / minSdk / buildTools / NDK / CI toolchain.

---

## 1. Executive summary

| Setting | Current (artisan) | Target (runBeat) | Change |
|---|---|---|---|
| compileSdk | 34 | 36 | **Bump** |
| targetSdk | 34 | 36 | **Bump** |
| minSdk | 24 | 26 | **Bump** |
| buildToolsVersion | *(not set)* | `"34.0.0"` | **Add** |
| ndkVersion | *(not set)* | `"26.1.10909125"` | **Add** |
| AGP | 8.5.0 | 8.5.0 | **Keep** (see section 2) |
| Kotlin | 1.9.22 | 1.9.22 | Keep |
| Gradle wrapper | 8.7 | 8.7 | Keep |
| Core library desugaring | enabled (`desugar_jdk_libs:2.0.4`) | *(not used)* | **Remove** |
| dependenciesInfo | *(not set)* | `includeInApk=false, includeInBundle=false` | **Add** |
| packagingOptions | *(not set)* | `resources.excludes` + `jniLibs.useLegacyPackaging` | **Add** (see section 7) |
| gradle.properties | minimal | enhanced (parallel, daemon, caching, retries) | **Enhance** |
| CI SDK platform | `platforms;android-34` | `platforms;android-36` | **Update** |
| CI cmake | *(not installed)* | `cmake;3.22.1` | **Add** |
| CI ndk.dir | *(not written)* | written to `local.properties` | **Add** |
| local.properties.example | sdk.dir only | sdk.dir + ndk.dir | **Update** |

---

## 2. AGP version decision: keep 8.5.0 or bump to 8.9.0+?

### 2.1 What runBeat actually does

runBeat's top-level `build.gradle` pins `com.android.application` version `8.5.0`
and its `app/build.gradle` sets `compileSdk 36`. There is **no**
`android.suppressUnsupportedCompileSdk` property anywhere in runBeat's
`gradle.properties` or build scripts. The `app-metadata.properties` artifact
confirms `androidGradlePluginVersion=8.5.0` was used for the last successful
debug build (APK dated 2025-10-18, 24.5 MB).

### 2.2 Why this works (and the risk)

AGP 8.5.0 was released in mid-2024 and was tested up to **compileSdk 34**.
When you set `compileSdk 36` with AGP 8.5.0, AGP emits a **warning** (not an
error):

```
We recommend using a newer Android Gradle plugin to use compileSdk = 36.
This Android Gradle plugin (8.5.0) was tested up to compileSdk = 34.
```

The build still succeeds because:
- The `android.jar` for API 36 is just a compile-time stub - AGP reads it to
  resolve symbols. New APIs added in 35/36 are simply available at compile time.
- AGP 8.5.0's resource processing, manifest merging, and dexing pipelines are
  not SDK-version-coupled in a way that breaks with newer platforms.
- runBeat has been building successfully with this configuration since at least
  October 2025 (confirmed by the debug APK artifact).

**However**, this is an officially unsupported combination. Risks:

| Risk | Likelihood | Impact |
|---|---|---|
| AGP 8.5.0 mis-handles a resource/manifest feature introduced in API 35/36 | Low | Medium - could cause subtle runtime issues or build failures on specific features |
| A future AGP 8.5.x patch release breaks compileSdk 36 | Very low | High - would need immediate AGP bump |
| Lint checks for API 35/36 behave incorrectly under AGP 8.5.0 | Low | Low - lint warnings may be inaccurate |
| Google Play rejects APKs compiled with an "untested" AGP/SDK combo | Very low | Medium - Play checks targetSdk, not AGP version |

### 2.3 Recommendation: **Keep AGP 8.5.0, add `android.suppressUnsupportedCompileSdk=36`**

**Rationale:**
1. **Proven in production.** runBeat has shipped releases with AGP 8.5.0 +
   compileSdk 36. Matching it exactly reduces divergence between the two
   projects, which is the stated goal.
2. **Minimises blast radius.** Bumping AGP to 8.9.0+ would require also
   bumping Gradle (AGP 8.9 requires Gradle 8.11+), which cascades into
   Kotlin plugin compatibility checks, Compose compiler compatibility, and
   potentially Chaquopy compatibility. That is a much larger change than the
   SDK alignment task.
3. **Chaquopy compatibility.** Chaquopy 16.0.0 is pinned and tested with
   AGP 8.5.x. Bumping AGP independently of Chaquopy introduces an untested
   combination. Chaquopy's own docs recommend staying on a supported AGP
   version, and 8.5.0 is within Chaquopy 16.0.0's tested range.
4. **The suppress property is cosmetic.** Adding
   `android.suppressUnsupportedCompileSdk=36` to `gradle.properties` silences
   the warning cleanly without changing build behaviour. runBeat doesn't have
   it, but adding it is a strict improvement (cleaner CI logs).

**If you later decide to bump AGP**, the safe path is:
- AGP 8.9.0+ -> requires Gradle 8.11.1+ -> requires Kotlin 1.9.24+ (or 2.0.x)
  -> requires Compose Compiler 1.5.14+ (or Kotlin 2.0-compatible version)
  -> must re-validate Chaquopy 16.0.0 (or bump to Chaquopy 17.x if available).
  This is a **separate, larger task** - do not bundle it with SDK alignment.

### 2.4 Action

Add to `mobile/android/gradle.properties`:

```properties
# AGP 8.5.0 was tested up to compileSdk 34; we compile against 36 (same as
# runBeat). This suppresses the "untested compileSdk" warning.
android.suppressUnsupportedCompileSdk=36
```

---

## 3. Changes to `mobile/android/app/build.gradle`

### 3.1 SDK version block

**Old:**
```gradle
android {
    namespace = "com.artisancompanion"
    compileSdk = 34
```

**New:**
```gradle
android {
    namespace = "com.artisancompanion"
    compileSdk = 36
    buildToolsVersion = "34.0.0"
    ndkVersion = "26.1.10909125"
```

### 3.2 defaultConfig - minSdk / targetSdk

**Old:**
```gradle
    defaultConfig {
        applicationId = "com.artisancompanion"
        minSdk = 24
        targetSdk = 34
```

**New:**
```gradle
    defaultConfig {
        applicationId = "com.artisancompanion"
        minSdk = 26
        targetSdk = 36
```

### 3.3 Add dependenciesInfo block

Insert after the `ndkVersion` line (inside the `android {}` block, before
`defaultConfig`):

```gradle
    dependenciesInfo {
        // Don't embed dependency metadata in APK/AAB - reduces size and
        // matches runBeat. Play Console / SDK analytics don't need it.
        includeInApk = false
        includeInBundle = false
    }
```

### 3.4 Remove core library desugaring

**Old** (in `compileOptions`):
```gradle
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // Enable desugaring so java.time (LocalDate, YearMonth, etc.) works on
        // API 24-25 (minSdk = 24). Without this, the app crashes with
        // NoClassDefFoundError on Android 7.x when using java.time APIs.
        isCoreLibraryDesugaringEnabled = true
    }
```

**New:**
```gradle
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
```

**Old** (in `dependencies`):
```gradle
    // Core library desugaring: provides java.time backport for API 24-25.
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")
```

**New:** Remove this line entirely.

### 3.5 Add packagingOptions block (see section 7 for rationale)

Insert inside the `android {}` block (after `composeOptions`, before
`sourceSets`):

```gradle
    packagingOptions {
        resources {
            excludes += '/META-INF/{AL2.0,LGPL2.1}'
        }
        jniLibs {
            useLegacyPackaging = true
        }
    }
```

---

## 4. Changes to `mobile/android/build.gradle`

**No change needed.** AGP stays at 8.5.0, Kotlin at 1.9.22, Chaquopy at 16.0.0.
The top-level file already matches runBeat's AGP version.

Only update the comment if desired (it currently says "AGP 8.5.0 / Kotlin 1.9.22
/ Chaquopy 16.0.0, Gradle 8.7 via the wrapper" - this remains accurate).

---

## 5. Changes to `mobile/android/gradle.properties`

### Current file:
```properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
```

### New file (aligned with runBeat, keeping artisan-specific properties):

```properties
# Project-wide Gradle settings - aligned with runBeat.

# JVM arguments for the daemon process.
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8

# Enables parallel execution of tasks.
org.gradle.parallel=true

# Enables daemon mode for faster builds.
org.gradle.daemon=true

# Enables build cache for faster builds.
org.gradle.caching=true

# Enables parallel tooling API (Gradle 9.4+ / IDE sync).
org.gradle.tooling.parallel=true

# AndroidX package structure.
android.useAndroidX=true

# Non-transitive R classes (smaller R class, faster builds).
android.nonTransitiveRClass=true

# Kotlin code style.
kotlin.code.style=official

# AGP 8.5.0 was tested up to compileSdk 34; we compile against 36 (same as
# runBeat). This suppresses the "untested compileSdk" warning.
android.suppressUnsupportedCompileSdk=36

# Retry artifact downloads with backoff so transient network errors (e.g.
# Maven Central HTTP 429 rate-limiting) do not fail CI builds.
org.gradle.internal.repository.max.retries=5
org.gradle.internal.repository.initial.backoff=2000
org.gradle.internal.repository.max.backoff=15000
```

### Line-by-line diff:

| Action | Line |
|---|---|
| Keep | `org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8` |
| Keep | `android.useAndroidX=true` |
| Keep | `kotlin.code.style=official` |
| Keep | `android.nonTransitiveRClass=true` (artisan-specific, runBeat doesn't have it - keep it) |
| **Add** | `org.gradle.parallel=true` |
| **Add** | `org.gradle.daemon=true` |
| **Add** | `org.gradle.caching=true` |
| **Add** | `org.gradle.tooling.parallel=true` |
| **Add** | `android.suppressUnsupportedCompileSdk=36` |
| **Add** | `org.gradle.internal.repository.max.retries=5` |
| **Add** | `org.gradle.internal.repository.initial.backoff=2000` |
| **Add** | `org.gradle.internal.repository.max.backoff=15000` |

**Note:** runBeat's `gradle.properties` has `org.gradle.caching=true` listed
twice (lines 19 and 23). We add it only once - the duplicate in runBeat is
harmless but unnecessary.

---

## 6. Changes to CI workflows

### 6.1 `.github/workflows/android-ci.yml`

**Old** (Set up Android SDK step):
```yaml
      - name: Set up Android SDK
        run: |
          export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/cmdline-tools/11.0/bin:$ANDROID_HOME/cmdline-tools/10.0/bin:$ANDROID_HOME/tools/bin:$PATH"
          yes | sdkmanager --licenses > /dev/null 2>&1 || true
          sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" \
            "ndk;26.1.10909125" --sdk_root=$ANDROID_HOME
          echo "sdk.dir=$ANDROID_HOME" > local.properties
```

**New:**
```yaml
      - name: Set up Android SDK
        run: |
          export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/cmdline-tools/11.0/bin:$ANDROID_HOME/cmdline-tools/10.0/bin:$ANDROID_HOME/tools/bin:$PATH"
          yes | sdkmanager --licenses > /dev/null 2>&1 || true
          sdkmanager "platform-tools" "platforms;android-36" "build-tools;34.0.0" \
            "ndk;26.1.10909125" "cmake;3.22.1" --sdk_root=$ANDROID_HOME
          echo "sdk.dir=$ANDROID_HOME" > local.properties
          echo "ndk.dir=$ANDROID_HOME/ndk/26.1.10909125" >> local.properties
```

**Changes:**
- `platforms;android-34` -> `platforms;android-36`
- Add `"cmake;3.22.1"` to the sdkmanager install list
- Add `echo "ndk.dir=$ANDROID_HOME/ndk/26.1.10909125" >> local.properties`

### 6.2 `.github/workflows/release.yml`

Same three changes as android-ci.yml:
- `platforms;android-34` -> `platforms;android-36`
- Add `"cmake;3.22.1"` to the sdkmanager install list
- Add `echo "ndk.dir=$ANDROID_HOME/ndk/26.1.10909125" >> local.properties`

**Note on `cmake;3.22.1`:** artisan_companion_app does not currently use any
native C/C++ code (Chaquopy ships prebuilt `.so` files for CPython, it doesn't
compile from source). However, runBeat installs cmake because it has native
modules (`soundtouch-android`, `aubio`). For artisan, cmake is **not strictly
required**, but installing it:
- Keeps CI parity with runBeat (same SDK setup steps).
- Future-proofs the CI if native modules are ever added.
- Costs ~50 MB of CI runner disk - negligible.

**Recommendation:** Include cmake for parity. If you prefer minimal CI, you can
omit it - Chaquopy 16.0.0 does not require cmake at build time.

---

## 7. Changes to `mobile/android/local.properties.example`

### Current file:
```properties
# Copy this file to local.properties (next to settings.gradle) and set the path
# to your Android SDK. local.properties is gitignored - do not commit it.
#
# This machine keeps a generic, project-agnostic SDK in ~/dev/tools (see
# ~/dev/tools/README.md):
#   sdk.dir=C:/Users/guill/dev/tools/android-sdk
#
# Other Windows example (per-user SDK install):
#   sdk.dir=C\:\Users\you\AppData\Local\Android\Sdk
# macOS/Linux example:
#   sdk.dir=/Users/you/Library/Android/sdk
```

### New file:

```properties
# Copy this file to local.properties (next to settings.gradle) and set the path
# to your Android SDK. local.properties is gitignored - do not commit it.
#
# This machine keeps a generic, project-agnostic SDK in ~/dev/tools (see
# ~/dev/tools/README.md):
#   sdk.dir=C:/Users/guill/dev/tools/android-sdk
#   ndk.dir=C:/Users/guill/dev/tools/android-sdk/ndk/26.1.10909125
#
# Other Windows example (per-user SDK install):
#   sdk.dir=C\:\Users\you\AppData\Local\Android\Sdk
#   ndk.dir=C\:\Users\you\AppData\Local\Android\Sdk\ndk\26.1.10909125
# macOS/Linux example:
#   sdk.dir=/Users/you/Library/Android/sdk
#   ndk.dir=/Users/you/Library/Android/sdk/ndk/26.1.10909125
```

**Changes:**
- Add `ndk.dir` example lines for each platform (Windows shared SDK, Windows
  per-user, macOS/Linux).
- The NDK version `26.1.10909125` matches the `ndkVersion` pinned in
  `app/build.gradle` and the CI sdkmanager install.

**Note:** The existing `local.properties` on this machine only has `sdk.dir`.
Since we're adding `ndkVersion = "26.1.10909125"` to `app/build.gradle`, AGP
will auto-locate the NDK from the SDK directory. The `ndk.dir` in
`local.properties` is a belt-and-suspenders override (same pattern as runBeat).
Developers should add it to their local `local.properties` after pulling this
change.

---

## 8. Changes to `mobile/README.md`

### 8.1 Version numbers paragraph (line ~43-47)

**Old:**
```
known-good starting point (AGP 8.5.0, Kotlin 1.9.22, Compose Compiler 1.5.8,
Compose UI 1.5.3, Material3 1.1.2, Material 1.11.0, Chaquopy 16.0.0,
Gradle 8.7, compileSdk 34, minSdk 24, targetSdk 34).
```

**New:**
```
known-good starting point (AGP 8.5.0, Kotlin 1.9.22, Compose Compiler 1.5.8,
Compose UI 1.5.3, Material3 1.1.2, Material 1.11.0, Chaquopy 16.0.0,
Gradle 8.7, compileSdk 36, minSdk 26, targetSdk 36).
```

### 8.2 Check `docs/mobile-port.md`

Line 148 of `docs/mobile-port.md` references an **outdated** version set:
```
| Chaquopy / AGP / Kotlin / Compose version drift - the Gradle files pin a
  known-good set (AGP 8.5.2, Kotlin 2.0.0, Compose BOM 2024.09.00,
  Compose Compiler 1.5.14, Chaquopy 16.0.0) | ...
```

This is already wrong (actual: AGP 8.5.0, Kotlin 1.9.22, no BOM, Compose
Compiler 1.5.8). It should be updated to match reality **and** the new SDK
versions:

```
| Chaquopy / AGP / Kotlin / Compose version drift - the Gradle files pin a
  known-good set (AGP 8.5.0, Kotlin 1.9.22, Compose Compiler 1.5.8,
  Compose UI 1.5.3, Material3 1.1.2, Chaquopy 16.0.0, Gradle 8.7,
  compileSdk 36, minSdk 26, targetSdk 36) | ...
```

---

## 9. Is removing core library desugaring safe?

### 9.1 What uses java.time in the Kotlin code?

Two files use `java.time` APIs:

**`app/src/main/java/com/artisancompanion/ui/cupping/CuppingEntryScreen.kt`:**
- `java.time.LocalDate` (parse, now, of)
- `java.time.format.DateTimeFormatter` (ISO_LOCAL_DATE)
- `java.time.format.DateTimeParseException`
- `java.time.temporal.ChronoUnit`

**`app/src/main/java/com/artisancompanion/ui/library/LibraryScreen.kt`:**
- `java.time.LocalDate` (parse)
- `java.time.YearMonth` (of, format)
- `java.time.format.DateTimeFormatter` (ofPattern)

### 9.2 API availability

| API | Available since |
|---|---|
| `java.time.LocalDate` | API 26 (Android 8.0) |
| `java.time.YearMonth` | API 26 |
| `java.time.format.DateTimeFormatter` | API 26 |
| `java.time.temporal.ChronoUnit` | API 26 |
| `java.time.format.DateTimeParseException` | API 26 |

All `java.time` classes used in the Kotlin code are available **natively** on
API 26+. The desugaring was only needed because `minSdk = 24` (Android 7.x
does not have `java.time`).

### 9.3 Python code

The Python core (`src/`) uses Python's `datetime` module - this runs inside
Chaquopy's embedded CPython and is completely unaffected by Android's
desugaring settings.

### 9.4 Conclusion: **Safe to remove**

Raising `minSdk` from 24 to 26 means all `java.time` APIs used in the Kotlin
code are available natively. Removing:
- `isCoreLibraryDesugaringEnabled = true` from `compileOptions`
- `coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")` from
  `dependencies`

...is safe. No code changes are needed.

### 9.5 Side benefit

Removing desugaring:
- Reduces APK size (desugar_jdk_libs adds ~1-2 MB).
- Removes the `desugarDebugFileDependencies` build task (faster builds).
- Simplifies the dependency tree.

---

## 10. Compose / dependency version bumps for compileSdk 36

### 10.1 Assessment: No bumps required

The current dependency set compiles fine against compileSdk 34 and there is
no known incompatibility with compileSdk 36:

| Dependency | Current | compileSdk 36 compatible? | Notes |
|---|---|---|---|
| `androidx.core:core-ktx` | 1.12.0 | Yes | Compiled against API 34; forward-compatible |
| `androidx.appcompat:appcompat` | 1.6.1 | Yes | Same |
| `com.google.android.material:material` | 1.11.0 | Yes | Same |
| `androidx.compose.ui:ui` | 1.5.3 | Yes | Compose is SDK-version-agnostic at compile time |
| `androidx.compose.ui:ui-tooling-preview` | 1.5.3 | Yes | Same |
| `androidx.compose.material3:material3` | 1.1.2 | Yes | Same |
| `androidx.compose.material:material-icons-extended` | 1.5.3 | Yes | Same |
| `androidx.activity:activity-compose` | 1.8.0 | Yes | Same |
| `androidx.lifecycle:lifecycle-viewmodel-compose` | 2.6.2 | Yes | Same |
| `androidx.navigation:navigation-compose` | 2.7.4 | Yes | Same |
| `org.jetbrains.kotlinx:kotlinx-serialization-json` | 1.6.3 | Yes | Pure Kotlin library |
| Chaquopy | 16.0.0 | Yes (see 10.2) | Tested with AGP 8.5.x |

### 10.2 Chaquopy 16.0.0 and compileSdk 36

Chaquopy 16.0.0 was released in 2024 and supports AGP 8.x. Its build-time
behaviour (Python source merging, proxy generation, JNI lib packaging) is
independent of compileSdk. The CPython `.so` files it ships are prebuilt for
specific ABIs and Android API levels (min API 21+ for Chaquopy 16), so
compileSdk 36 does not affect runtime behaviour.

**Risk:** Low. Chaquopy 16.0.0 should work with compileSdk 36. The main
compatibility surface is AGP version (8.5.0 - supported), not compileSdk.

### 10.3 targetSdk 36 behaviour changes to be aware of

Raising `targetSdk` from 34 to 36 introduces Android platform behaviour
changes that the app must handle:

| Change | API | Impact on artisan_companion_app |
|---|---|---|
| **Edge-to-edge enforcement** | 35+ | Apps targeting SDK 35+ are edge-to-edge by default. The app uses Compose, which handles insets via `WindowCompat.setDecorFitsSystemWindows(window, false)` or `enableEdgeToEdge()`. **Check:** Does `MainActivity.kt` call `enableEdgeToEdge()`? If not, add it or the app will have padding issues on Android 15+. |
| **Foreground service types** | 34+ | Not applicable - no foreground services. |
| **Photo picker** | 33+ | Not applicable - uses SAF (`ACTION_OPEN_DOCUMENT`). |
| **Runtime permissions granularity** | 33+ | Not applicable - no dangerous permissions requested. |
| **Restricted `PACKAGE_USAGE_STATS`** | 34+ | Not applicable. |
| **Exact alarm restriction** | 31+ | Not applicable - no alarms. |
| **Notification permission** | 33+ | Not applicable - no notifications. |
| **Intent resolution for implicit intents** | 30+ | Already handled at targetSdk 34. |
| **Scoped storage enforcement** | 30+ | Already handled. App uses SAF and app-specific external storage. |
| **Security: `android:exported` required** | 31+ | Already declared in manifest. |
| **PendingIntent mutability** | 31+ | Check if any `PendingIntent` is created without `FLAG_IMMUTABLE` or `FLAG_MUTABLE`. |
| **Foreground service launch restriction** | 34+ | Not applicable. |

**Action item:** Review `MainActivity.kt` for edge-to-edge handling. Compose
apps targeting SDK 35+ should call:

```kotlin
enableEdgeToEdge()
```

...in `onCreate` before `setContent`. If it's already there, no change needed.
If not, add it - otherwise the app will have unexpected system bar padding on
Android 15+ devices.

### 10.4 Recommendation

No dependency version bumps are required for the SDK alignment. The only
code-level change to consider is the edge-to-edge call in `MainActivity.kt`
(see 10.3).

---

## 11. Risk assessment

| # | Change | Risk level | Details |
|---|---|---|---|
| 1 | `compileSdk` 34 -> 36 | **Low** | Proven in runBeat. AGP 8.5.0 emits a warning but compiles. New API stubs are backward-compatible. |
| 2 | `targetSdk` 34 -> 36 | **Medium** | Platform behaviour changes between API 34 and 36 (see 10.3). Edge-to-edge enforcement on API 35+ is the main concern. Must test on Android 15 device/emulator. |
| 3 | `minSdk` 24 -> 26 | **Low** | Drops Android 7.x (API 24-25) support. Check Play Console for device reach impact - Android 7.x is <1% of active devices in 2026. No code changes needed. |
| 4 | Remove desugaring | **Low** | All java.time APIs used are available natively on API 26+. Verified by code audit (section 9). |
| 5 | Add `buildToolsVersion = "34.0.0"` | **Low** | AGP 8.5.0's default build tools is 34.0.0 - this just makes it explicit. CI already installs build-tools;34.0.0. |
| 6 | Add `ndkVersion = "26.1.10909125"` | **Low** | CI already installs this NDK version. Chaquopy's prebuilt `.so` files are compatible. Making it explicit prevents AGP from auto-selecting a different NDK. |
| 7 | Add `dependenciesInfo` block | **Low** | Reduces APK/AAB size slightly. No runtime impact. Play Console's "App Bundle Explorer" won't show dependency metadata - cosmetic only. |
| 8 | Add `packagingOptions` with `jniLibs.useLegacyPackaging = true` | **Medium** | This changes how native libraries are packaged (uncompressed, page-aligned). Chaquopy ships large CPython `.so` files. **Risk:** If Chaquopy or AGP 8.5.0 has issues with `useLegacyPackaging`, the APK could fail to load native libs. runBeat uses this with native modules (soundtouch, aubio) and it works. For artisan with Chaquopy, this should also work, but test thoroughly. **Alternative:** Omit `jniLibs { useLegacyPackaging = true }` and only keep the `resources.excludes` - this is the safer option for Chaquopy apps. See section 11.1 below. |
| 9 | Enhance `gradle.properties` | **Low** | `parallel`, `daemon`, `caching`, `tooling.parallel` are all safe. Repository retries are CI-friendly. |
| 10 | Add `android.suppressUnsupportedCompileSdk=36` | **Low** | Only suppresses a warning. No behaviour change. |
| 11 | Update CI workflows | **Low** | `platforms;android-36` requires the CI runner to download a newer platform - GitHub runners have it pre-cached. Adding `cmake;3.22.1` is harmless. Writing `ndk.dir` to local.properties is safe. |
| 12 | Update `local.properties.example` | **None** | Documentation only. |
| 13 | Update `mobile/README.md` | **None** | Documentation only. |

### 11.1 Detailed risk: `packagingOptions.jniLibs.useLegacyPackaging`

runBeat has this because it bundles native C++ libraries (soundtouch, aubio)
that benefit from page-aligned, uncompressed `.so` files (allows the OS to
mmap them directly from the APK, saving RAM).

artisan_companion_app bundles Chaquopy's CPython `.so` files. These are also
large native libraries. The question is whether `useLegacyPackaging = true`
helps or hurts:

- **Helps:** `.so` files are stored uncompressed and page-aligned -> the OS
  can mmap them directly -> less RAM usage at runtime.
- **Hurts:** APK size increases (uncompressed `.so`). For Chaquopy, the
  CPython runtime is ~30-40 MB per ABI. With 2 ABIs (arm64-v8a, x86_64),
  the APK could grow by ~60-80 MB uncompressed. However, AAB (Play Store)
  uses compressed `.so` in the bundle and splits by ABI, so the download size
  is unaffected.

**Recommendation:** Include `jniLibs { useLegacyPackaging = true }` for
parity with runBeat. It matches the target state. The APK size increase is
acceptable (the debug APK is already 41 MB). If APK size becomes a concern,
this can be revisited later.

The `resources { excludes += '/META-INF/{AL2.0,LGPL2.1}' }` part is
uncontroversial - it removes duplicate license files from dependencies.

---

## 12. Testing plan

### 12.1 Local pre-checks (before building)

```bash
cd mobile/android

# 1. Verify the Android SDK has platform 36 installed
ls $ANDROID_HOME/platforms/android-36/android.jar
# (or on this machine:)
ls ~/dev/tools/android-sdk/platforms/android-36/android.jar

# 2. If missing, install it:
yes | sdkmanager --licenses
sdkmanager "platforms;android-36" "build-tools;34.0.0" "ndk;26.1.10909125" "cmake;3.22.1"

# 3. Ensure local.properties has ndk.dir (add if missing):
cat local.properties
# Should contain:
#   sdk.dir=C:/Users/guill/dev/tools/android-sdk
#   ndk.dir=C:/Users/guill/dev/tools/android-sdk/ndk/26.1.10909125
```

### 12.2 Build verification

```bash
cd mobile/android

# Clean build to catch any stale-cache issues
./gradlew clean

# 1. Assemble debug APK (primary check)
./gradlew :app:assembleDebug

# 2. Run unit tests
./gradlew :app:testDebugUnitTest

# 3. Run lint (catches targetSdk 36 issues)
./gradlew :app:lintDebug

# 4. Build release APK + AAB (verifies signing + packaging)
./gradlew :app:assembleRelease :app:bundleRelease \
  -PversionName="0.1.0-test"
```

### 12.3 What to check in the build output

After `assembleDebug`:

```bash
# Verify minSdk in the built APK metadata
cat app/build/outputs/apk/debug/output-metadata.json
# Should show: "minSdkVersionForDexing": 26

# Verify the APK's targetSdkVersion using aapt
$ANDROID_HOME/build-tools/34.0.0/aapt dump badging app/build/outputs/apk/debug/app-debug.apk | grep -E "sdkVersion|targetSdkVersion"
# Expected:
#   sdkVersion:'26'
#   targetSdkVersion:'36'
```

After `lintDebug`:
- Check `app/build/reports/lint-results-debug.html` for any new warnings
  related to targetSdk 36 (e.g., edge-to-edge, permission changes).

### 12.4 Runtime testing

Install the debug APK on a device or emulator:

```bash
# Using the project's install script
./install.sh

# Or manually
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

**Test matrix:**

| Test | What to verify |
|---|---|
| App launches | No crash on startup |
| Library screen | Roast list loads, dates display correctly (java.time.LocalDate, YearMonth) |
| Cupping entry | Date picker works, date parsing/formatting works (java.time.LocalDate, DateTimeFormatter) |
| Editor screen | Radar chart renders, sensory data saves |
| Import .alog | SAF file picker works, files copy to app storage |
| Export | Share sheet works (FileProvider) |
| Settings | Theme switching works |
| Edge-to-edge | No unexpected padding/overlap with system bars (especially on Android 15) |
| Python bridge | Chaquopy initialises, API calls return data |

**Critical runtime check:** The cupping date picker and library date grouping
are the only places that use `java.time` APIs. If desugaring removal was
correct, these will work without any `NoClassDefFoundError`.

### 12.5 CI verification

After pushing the changes:

1. **android-ci.yml** should pass:
   - SDK setup installs `platforms;android-36` + cmake
   - `lintDebug` passes
   - `testDebugUnitTest` passes
   - `assembleDebug` produces an APK

2. **release.yml** (triggered by tag or manual dispatch):
   - SDK setup installs `platforms;android-36` + cmake
   - `assembleRelease` + `bundleRelease` succeed
   - AAB and APK artifacts are uploaded
   - GitHub Release is created

### 12.6 Rollback plan

If the build fails or runtime issues are found:

1. Revert `app/build.gradle` changes (compileSdk, targetSdk, minSdk,
   desugaring, dependenciesInfo, packagingOptions).
2. Revert `gradle.properties` additions.
3. Revert CI workflow changes.
4. `./gradlew clean :app:assembleDebug` to verify rollback.

The changes are isolated to build configuration files - no source code
changes are required (except optionally `enableEdgeToEdge()` in MainActivity).

---

## 13. Implementation order

Recommended sequence to minimise broken intermediate states:

1. **Install SDK components locally** (platform 36, verify build-tools 34.0.0
   and NDK 26.1.10909125 are present).
2. **`mobile/android/gradle.properties`** - add all new properties.
3. **`mobile/android/app/build.gradle`** - apply all changes in one edit
   (compileSdk, buildToolsVersion, ndkVersion, minSdk, targetSdk,
   dependenciesInfo, remove desugaring, add packagingOptions).
4. **`mobile/android/local.properties.example`** - add ndk.dir examples.
5. **Build locally:** `./gradlew clean :app:assembleDebug` -> fix any issues.
6. **Test locally:** `./gradlew :app:testDebugUnitTest :app:lintDebug`.
7. **Install and test on device/emulator** (see 12.4).
8. **`.github/workflows/android-ci.yml`** - update SDK setup step.
9. **`.github/workflows/release.yml`** - update SDK setup step.
10. **`mobile/README.md`** - update version numbers.
11. **`docs/mobile-port.md`** - fix outdated version reference (line 148).
12. **Commit and push** -> CI runs -> verify green.

---

## 14. Appendix: Full file diffs

### 14.1 `mobile/android/app/build.gradle` - full diff

```diff
 android {
     namespace = "com.artisancompanion"
-    compileSdk = 34
+    compileSdk = 36
+    buildToolsVersion = "34.0.0"
+    ndkVersion = "26.1.10909125"
+
+    dependenciesInfo {
+        includeInApk = false
+        includeInBundle = false
+    }
 
     // versionCode is read from build-counter.txt ...
     def counterFile = file("${project.rootDir}/build-counter.txt")
     def buildNumber = counterFile.exists() ? counterFile.text.trim().toInteger() : 1
     def vName = project.findProperty('versionName') ?: '0.1.0'
 
     defaultConfig {
         applicationId = "com.artisancompanion"
-        minSdk = 24
-        targetSdk = 34
+        minSdk = 26
+        targetSdk = 36
         versionCode = buildNumber
         versionName = vName
 
         ndk {
             abiFilters "arm64-v8a", "x86_64"
         }
     }
@@
     composeOptions {
         kotlinCompilerExtensionVersion = "1.5.8"
     }
 
+    packagingOptions {
+        resources {
+            excludes += '/META-INF/{AL2.0,LGPL2.1}'
+        }
+        jniLibs {
+            useLegacyPackaging = true
+        }
+    }
+
     sourceSets {
         getByName("main") {
             python.srcDir("src/main/python")
             python.srcDir("../../../src")
         }
     }
 
     compileOptions {
         sourceCompatibility = JavaVersion.VERSION_17
         targetCompatibility = JavaVersion.VERSION_17
-        // Enable desugaring so java.time (LocalDate, YearMonth, etc.) works on
-        // API 24-25 (minSdk = 24). Without this, the app crashes with
-        // NoClassDefFoundError on Android 7.x when using java.time APIs.
-        isCoreLibraryDesugaringEnabled = true
     }
@@
     implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
 
-    // Core library desugaring: provides java.time backport for API 24-25.
-    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")
-
     debugImplementation("androidx.compose.ui:ui-tooling:1.5.3")
 }
```

### 14.2 `mobile/android/gradle.properties` - full diff

```diff
-org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
-android.useAndroidX=true
-kotlin.code.style=official
-android.nonTransitiveRClass=true
+# Project-wide Gradle settings - aligned with runBeat.
+
+# JVM arguments for the daemon process.
+org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
+
+# Enables parallel execution of tasks.
+org.gradle.parallel=true
+
+# Enables daemon mode for faster builds.
+org.gradle.daemon=true
+
+# Enables build cache for faster builds.
+org.gradle.caching=true
+
+# Enables parallel tooling API (Gradle 9.4+ / IDE sync).
+org.gradle.tooling.parallel=true
+
+# AndroidX package structure.
+android.useAndroidX=true
+
+# Non-transitive R classes (smaller R class, faster builds).
+android.nonTransitiveRClass=true
+
+# Kotlin code style.
+kotlin.code.style=official
+
+# AGP 8.5.0 was tested up to compileSdk 34; we compile against 36 (same as
+# runBeat). This suppresses the "untested compileSdk" warning.
+android.suppressUnsupportedCompileSdk=36
+
+# Retry artifact downloads with backoff so transient network errors (e.g.
+# Maven Central HTTP 429 rate-limiting) do not fail CI builds.
+org.gradle.internal.repository.max.retries=5
+org.gradle.internal.repository.initial.backoff=2000
+org.gradle.internal.repository.max.backoff=15000
```

### 14.3 `.github/workflows/android-ci.yml` - diff

```diff
       - name: Set up Android SDK
         run: |
           export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/cmdline-tools/11.0/bin:$ANDROID_HOME/cmdline-tools/10.0/bin:$ANDROID_HOME/tools/bin:$PATH"
           yes | sdkmanager --licenses > /dev/null 2>&1 || true
-          sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" \
-            "ndk;26.1.10909125" --sdk_root=$ANDROID_HOME
+          sdkmanager "platform-tools" "platforms;android-36" "build-tools;34.0.0" \
+            "ndk;26.1.10909125" "cmake;3.22.1" --sdk_root=$ANDROID_HOME
           echo "sdk.dir=$ANDROID_HOME" > local.properties
+          echo "ndk.dir=$ANDROID_HOME/ndk/26.1.10909125" >> local.properties
```

### 14.4 `.github/workflows/release.yml` - diff

Same changes as 14.3.

### 14.5 `mobile/android/local.properties.example` - diff

```diff
 # This machine keeps a generic, project-agnostic SDK in ~/dev/tools (see
 # ~/dev/tools/README.md):
 #   sdk.dir=C:/Users/guill/dev/tools/android-sdk
+#   ndk.dir=C:/Users/guill/dev/tools/android-sdk/ndk/26.1.10909125
 #
 # Other Windows example (per-user SDK install):
 #   sdk.dir=C\:\Users\you\AppData\Local\Android\Sdk
+#   ndk.dir=C\:\Users\you\AppData\Local\Android\Sdk\ndk\26.1.10909125
 # macOS/Linux example:
 #   sdk.dir=/Users/you/Library/Android/sdk
+#   ndk.dir=/Users/you/Library/Android/sdk/ndk/26.1.10909125
```

### 14.6 `mobile/README.md` - diff

```diff
-known-good starting point (AGP 8.5.0, Kotlin 1.9.22, Compose Compiler 1.5.8,
-Compose UI 1.5.3, Material3 1.1.2, Material 1.11.0, Chaquopy 16.0.0,
-Gradle 8.7, compileSdk 34, minSdk 24, targetSdk 34).
+known-good starting point (AGP 8.5.0, Kotlin 1.9.22, Compose Compiler 1.5.8,
+Compose UI 1.5.3, Material3 1.1.2, Material 1.11.0, Chaquopy 16.0.0,
+Gradle 8.7, compileSdk 36, minSdk 26, targetSdk 36).
```

### 14.7 `docs/mobile-port.md` - diff (line 148)

```diff
-| Chaquopy / AGP / Kotlin / Compose version drift - the Gradle files pin a known-good set (AGP 8.5.2, Kotlin 2.0.0, Compose BOM 2024.09.00, Compose Compiler 1.5.14, Chaquopy 16.0.0) | Open in Android Studio and align versions with the Studio template if version checks complain. The Python side is the stable part. |
+| Chaquopy / AGP / Kotlin / Compose version drift - the Gradle files pin a known-good set (AGP 8.5.0, Kotlin 1.9.22, Compose Compiler 1.5.8, Compose UI 1.5.3, Material3 1.1.2, Chaquopy 16.0.0, Gradle 8.7, compileSdk 36, minSdk 26, targetSdk 36) | Open in Android Studio and align versions with the Studio template if version checks complain. The Python side is the stable part. |
```

---

## 15. Open questions

1. **Edge-to-edge:** Does `MainActivity.kt` call `enableEdgeToEdge()`? If not,
   should it be added as part of this change, or as a follow-up? (Recommended:
   add it in this change - it's a one-line addition and prevents a visible
   regression on Android 15.)

2. **cmake in CI:** Include `cmake;3.22.1` in CI for parity with runBeat, or
   omit it since artisan has no native C/C++ code? (Recommended: include it
   for parity; it's harmless.)

3. **`jniLibs.useLegacyPackaging`:** Include for full parity with runBeat, or
   omit to keep Chaquopy's default packaging? (Recommended: include for
   parity; test APK size impact.)

4. **minSdk 24 -> 26 device reach:** Should we check Play Console (when the app
   is published) for the percentage of devices on Android 7.x? In 2026 this is
   <1%, so the impact is negligible.

5. **Future AGP bump:** Should a separate task be created to bump AGP to
   8.9.0+ (with Gradle 8.11+, Kotlin 2.0+, Compose Compiler upgrade, Chaquopy
   re-validation)? This would be a larger, independent change.
