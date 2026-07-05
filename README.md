# DyslexEye

**An open-source accessibility desktop application that helps people with dyslexia and visual impairments read more comfortably.**

DyslexEye uses the OpenDyslexic font, bionic reading techniques, color themes, and OCR to reformat any text, image, PDF, or webpage into a dyslexia-friendly reading experience.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
- [Configuration](#configuration)
- [License](#license)
- [Releases & Changelog](#releases--changelog)
- [Known Issues & Bug Tracker](#known-issues--bug-tracker)
- [Contributing](#contributing)

---

## What It Does

DyslexEye renders any content — scanned images, PDFs, plain text, Word documents, or web pages — using the OpenDyslexic typeface, which is specifically designed to reduce letter-reversal and improve reading flow for dyslexic readers. It combines several assistive features in one desktop app with a gold-and-purple aesthetic that avoids harsh contrasts.

---

## Installation

### Prerequisites

| Dependency | Purpose | Install |
|---|---|---|
| Python 3.10+ | Runtime | [python.org](https://www.python.org) |
| PyQt6 | GUI framework | `pip install PyQt6` |
| PyQt6-WebEngine | Embedded browser view | `pip install PyQt6-WebEngine` |
| Tesseract OCR | Image text extraction | [github.com/tesseract-ocr](https://github.com/tesseract-ocr/tesseract) |
| Pillow | Image processing | `pip install pillow` |
| pytesseract | Python Tesseract wrapper | `pip install pytesseract` |
| deep-translator | Translation support | `pip install deep-translator` |

### Quick Install

```bash
# Clone the repo
git clone https://github.com/DoktorKarde/dyslexeye.git
cd dyslexeye

# Install Python dependencies
pip install PyQt6 PyQt6-WebEngine pytesseract pillow deep-translator

# Install Tesseract (Windows)
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

# Run
python dyslexic_reader.py
```

### Fonts

The app ships with `OpenDyslexic3-Regular.ttf` and `OpenDyslexic3-Bold.ttf`. Place both files in the same directory as `dyslexic_reader.py`. The app loads them automatically on startup.

---

## Usage

### Opening Content

- **Files** — Click **📂 Open** or drag and drop any supported file onto the window.
- **Web pages** — Paste a URL into the **🌐 URL** bar and press Enter or click **Load**.

### Supported File Types

`txt`, `md`, `html`, `htm`, `csv`, `pdf`, `docx`, `rtf`, `json`, `log`, `py`, `js`, `ts`, `css`, `xml`, `png`, `jpg`, `jpeg`, `gif`, `bmp`, `webp`

### Reading Controls

| Control | Description |
|---|---|
| **Size slider** | Adjusts font size (12–36px) |
| **Theme dropdown** | Changes background and text color |
| **𝐁 Half-Bold** | Bolds the first half of every word (bionic reading) |
| **📏 Ruler** | Toggles a reading ruler that tracks the cursor and magnifies the current line |
| **▶ Read / ⏸ Pause / ⏹ Stop** | Text-to-speech controls |
| **Show Extracted Text ▸** | Switches between the image view and the raw OCR text |
| **🔍 Overlay** | Launches a floating always-on-top overlay window with live OCR |

---

## Features

### OpenDyslexic Font
Renders all content in OpenDyslexic 3, a typeface with weighted bottoms on letters to prevent rotation and reversal errors. Supports a separate bold weight for Half-Bold mode.

### Half-Bold (Bionic Reading)
The first syllable of each word is rendered in the bold font weight. This gives the eye anchoring points and reduces the cognitive load of tracking across lines.

### Color Themes
Seven built-in themes change both the reader background and the OCR overlay canvas:
- Dark gold (default)
- Cream
- Sky blue
- Mint
- Lavender
- Warm yellow
- Navy

### Reading Ruler with Magnification
A translucent gold strip follows the cursor. When hovering over a canvas-rendered image, the ruler re-samples that pixel strip at 1.35× zoom, showing a magnified view of the current line without re-running OCR.

### OCR Image Support
Images are processed with Tesseract OCR. The word bounding boxes are preserved and re-rendered on a canvas using the OpenDyslexic font, maintaining approximate layout. Theme changes redraw the canvas without re-running OCR.

### Web Page Import
Paste any URL into the URL bar. DyslexEye fetches the page, strips HTML tags and navigation, and displays the article text in the dyslexia-friendly reader.

### PDF Support
Multi-page PDFs are rendered page by page using PDF.js. Each page's text is extracted and displayed with the configured font and theme.

### Text-to-Speech
Uses the browser's built-in `SpeechSynthesis` API to read content aloud. Supports play, pause, and stop.

### Floating Overlay Mode
A draggable, resizable, always-on-top window captures whatever is behind it at configurable intervals (0.5s–5s) and runs OCR, displaying the extracted text in real time. Useful for reading content in other applications.

### Translation
Translates extracted text between languages using `deep-translator` (Google Translate backend) with argostranslate fallback.

---

## Configuration

Settings are stored locally next to the script and loaded automatically on startup.

---

## Logs & Bug Reports

The app writes a log file each session to a `logs/` folder next to the executable.
If you encounter a bug, attach the relevant log file when reporting the issue via [GitHub Issues](https://github.com/DoktorKarde/dyslexeye/issues).

---

## Building the Exe

Run `build.bat` to produce a standalone executable (no Python or Tesseract install required on the target machine — tessdata is bundled):

```
build.bat
```

Output: `dist\DyslexEye\DyslexEye.exe`

---

## Disclaimer

Made with Claude (Anthropic) assistance. DyslexEye does not transmit any content you open — all OCR and processing runs locally. Translation uses the Google Translate API via `deep-translator`; translated text is sent to Google's servers.

---

## License

DyslexEye is released under the **MIT License**.

```
MIT License

Copyright (c) 2026 Doktor Karde

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**OpenDyslexic** font is licensed under the [SIL Open Font License 1.1](https://opendyslexic.org/). It is free for personal and commercial use.

---

## Releases & Changelog

### v0.3.4 — Current
- Added ruler magnification: ruler re-samples canvas pixels at 1.35× zoom; scales text elements in HTML mode
- Added web page import via URL bar (strips HTML, displays article text)
- Fixed overlay "crash": main window no longer minimizes when overlay opens
- Moved "Show Extracted Text" toggle to top of image viewer

### v0.3.3
- Renamed app to **DyslexEye**
- Added toggle to show original image (hide OCR overlay)

### v0.3.2
- Toggle buttons (Half-Bold, Ruler, Original) turn green when active; green state persists on hover

### v0.3.1
- Triple-draw bold technique: draws bold text at x, x+0.5, x+1 for visibly heavier weight
- Replaced OTF fonts with OpenDyslexic3 TTF (Regular + Bold)

### v0.3.0
- Half-Bold (bionic reading) works on canvas-rendered images, not just HTML text
- Theme color fills entire canvas background, not just text bounding boxes

### v0.2.x
- Color theme system, reading ruler, TTS, OCR overlay, PDF support

---

## Known Issues & Bug Tracker

Submit bugs and feature requests via the [GitHub Issues](https://github.com/DoktorKarde/dyslexeye/issues) page.

### Current Known Issues

| # | Description | Status |
|---|---|---|
| 1 | Web page import may fail on JavaScript-rendered pages (SPA) | Open |
| 2 | Tesseract path not auto-detected on some Windows installs | Open |
| 3 | Overlay OCR accuracy depends on screen DPI scaling settings | Open |
| 4 | PDF pages with complex multi-column layouts may render out of order | Open |

### Reporting a Bug

Include:
- OS and Python version
- Steps to reproduce
- A screenshot if the issue is visual

---

## Contributing

Contributions are welcome. DyslexEye is written in Python and follows a straightforward single-file architecture.

### Getting Started

```bash
git clone https://github.com/DoktorKarde/dyslexeye.git
cd dyslexeye
pip install PyQt6 PyQt6-WebEngine pytesseract pillow deep-translator
python dyslexic_reader.py
```

### Code Structure

```
dyslexic_reader.py          — Main application
OpenDyslexic3-Regular.ttf   — OpenDyslexic font (regular)
OpenDyslexic3-Bold.ttf      — OpenDyslexic font (bold)
build.bat                   — PyInstaller build script
```

### Coding Conventions

- All edits to `dyslexic_reader.py` must be made via Python scripts (not direct text editing) to avoid truncating the large HTML_TEMPLATE string on line 1.
- Versioning format: `MAJOR.MINOR.PATCH`, rolls over at 10 (e.g. `0.0.9 → 0.1.0`).
- Follow the gold/purple theme palette for any new UI elements.

### Submitting a Pull Request

1. Fork the repository
2. Create a branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Submit a pull request with a clear description