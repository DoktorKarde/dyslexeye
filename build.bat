@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   Stream Recommender -- Build Script
echo ================================================
echo.

:: ── Check Python ─────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

:: ── Check required files ──────────────────────────
if not exist "stream_picker.py" (
    echo [ERROR] stream_picker.py not found.
    pause & exit /b 1
)
if not exist "steam_appids.csv" (
    echo [ERROR] steam_appids.csv not found.
    pause & exit /b 1
)

:: ── Install dependencies ──────────────────────────
echo [1/3] Installing dependencies...
python -m pip install --upgrade pyinstaller PyQt6 requests --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause & exit /b 1
)

:: ── Clean previous build ──────────────────────────
echo [2/3] Cleaning previous build...
if exist "build"  rmdir /s /q "build"
if exist "dist"   rmdir /s /q "dist"
if exist "StreamRecommender.spec" del /q "StreamRecommender.spec"

:: ── Build ─────────────────────────────────────────
echo [3/3] Building executable...
echo.

pyinstaller ^
    --onedir ^
    --windowed ^
    --name "StreamRecommender" ^
    --add-data "steam_appids.csv;." ^
    --add-data "stream_picker.py;." ^
    --add-data "settings_dialog.py;." ^
    --add-data "platforms.py;." ^
    --collect-all PyQt6 ^
    --hidden-import "difflib" ^
    --hidden-import "sqlite3" ^
    --hidden-import "stream_picker" ^
    --hidden-import "settings_dialog" ^
    --hidden-import "platforms" ^
    --noconfirm ^
    --clean ^
    "Stream Recommender.pyw"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above.
    pause & exit /b 1
)

echo.
echo ================================================
echo   Done!
echo.
echo   Output folder:  dist\StreamRecommender\
echo   Run:            dist\StreamRecommender\StreamRecommender.exe
echo ================================================
echo.
pause
