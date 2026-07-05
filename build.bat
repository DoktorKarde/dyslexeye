@echo off
setlocal enabledelayedexpansion
title DyslexEye Build

:: ─────────────────────────────────────────────────────────────────────────────
:: DyslexEye — Windows EXE build script
:: Requires: Python 3.10+, internet connection (first run)
:: Output:   dist\DyslexEye\DyslexEye.exe  (portable folder)
:: ─────────────────────────────────────────────────────────────────────────────

echo.
echo  DyslexEye Build Script
echo  ──────────────────────
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo  Python: %%v

:: ── Virtual environment ───────────────────────────────────────────────────────
if not exist ".venv" (
    echo  Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

:: ── Dependencies ──────────────────────────────────────────────────────────────
echo  Installing / verifying dependencies...
pip install --quiet --upgrade pip
pip install --quiet ^
    PyQt6 ^
    PyQt6-WebEngine ^
    PyQt6-WebEngine-Qt6 ^
    pyinstaller ^
    pytesseract ^
    pillow ^
    numpy ^
    deep-translator ^
    python-docx

:: ── PyInstaller spec ──────────────────────────────────────────────────────────
echo  Building EXE...

:: Collect all resource files
set FONTS=--add-data "OpenDyslexic3-Regular.ttf;." ^
          --add-data "OpenDyslexic3-Bold.ttf;." ^
          --add-data "OpenDyslexic-Regular.otf;."

set TESSDATA=
if exist "tessdata" set TESSDATA=--add-data "tessdata;tessdata"

set ICON=
if exist "icon.png" set ICON=--icon "icon.png"

pyinstaller ^
    --noconfirm ^
    --windowed ^
    --name "DyslexEye" ^
    %FONTS% ^
    %TESSDATA% ^
    %ICON% ^
    --collect-all PyQt6 ^
    --collect-all PyQt6.QtWebEngineCore ^
    --collect-all deep_translator ^
    --collect-submodules docx ^
    --hidden-import PyQt6.QtWebEngineWidgets ^
    --hidden-import PyQt6.QtWebChannel ^
    --hidden-import pytesseract ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageGrab ^
    --hidden-import deep_translator ^
    --hidden-import deep_translator.engines.google ^
    --hidden-import docx ^
    dyslexic_reader.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed. See above for details.
    pause & exit /b 1
)

echo.
echo  ✓ Build complete: dist\DyslexEye\DyslexEye.exe
echo.

:: ── Open output folder ────────────────────────────────────────────────────────
explorer dist\DyslexEye
pause
exit /b 0

:: =============================================================================
:: ANDROID + iOS — Why there is no build here
:: =============================================================================
::
:: PyQt6 does NOT support Android or iOS. Qt itself does, but the Python
:: bindings (PyQt6 / PySide6) have no official mobile target. These options
:: exist if you want to go cross-platform:
::
:: ── Android ──────────────────────────────────────────────────────────────────
::  Option A: BeeWare (Briefcase)
::    - Rewrite the UI using the Toga widget toolkit instead of PyQt6
::    - `briefcase create android` / `briefcase build android`
::    - https://beeware.org
::
::  Option B: Kivy + Buildozer  (Linux/macOS only for building)
::    - Rewrite UI in Kivy, then `buildozer android debug`
::    - Very large APK (~100 MB), no WebEngine equivalent
::
::  Option C: Progressive Web App
::    - Port the reader to HTML/JS (much of the reader logic is already JS)
::    - Host or package with Electron for desktop, PWA for mobile
::    - Works on Android, iOS, and desktop without rewriting twice
::    - RECOMMENDED path if cross-platform is a goal
::
:: ── iOS ──────────────────────────────────────────────────────────────────────
::  - Requires macOS + Xcode — cannot be built on Windows at all
::  - BeeWare Briefcase supports iOS with Toga UI
::  - Apple App Store requires code signing ($99/year developer account)
::
:: ── Recommended path for mobile ──────────────────────────────────────────────
::  The reader's core (font rendering, HTML display, URL loading) already runs
::  in a WebEngine (Chromium). Converting to a standalone web app / PWA would
::  reuse almost all the existing JS and give you Android + iOS for free.
::  Say the word and I can start that conversion.
::
:: =============================================================================
