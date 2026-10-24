@echo off
rem Build the debug APK. Requires Java 17 on PATH.
cd /d "%~dp0"
where java >nul 2>nul || (echo ERROR: java ^(17^) not found on PATH. & exit /b 1)
call gradlew.bat assembleDebug %*
if errorlevel 1 exit /b 1
echo.
echo APK: app\build\outputs\apk\debug\app-debug.apk
