@echo off
rem Build and install the debug APK on a connected phone (USB debugging on).
cd /d "%~dp0"
where java >nul 2>nul || (echo ERROR: java ^(17^) not found on PATH. & exit /b 1)

call gradlew.bat installDebug %*
if errorlevel 1 (
    echo Gradle installDebug failed - trying direct adb install...
    tools\platform-tools\adb.exe wait-for-device
    tools\platform-tools\adb.exe install -r app\build\outputs\apk\debug\app-debug.apk
    if errorlevel 1 exit /b 1
)
echo Installed.
tools\platform-tools\adb.exe shell am start -n com.artisancompanion/.MainActivity
