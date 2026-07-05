# Stream Recommender

**Show which games you own are worth streaming right now, ranked by live Twitch popularity.**

---

## What It Does

Stream Recommender cross-references your game library against Twitch's live top-game rankings.
It resolves your Steam library via API, fuzzy-matches game names against the current Twitch top 500,
and presents a scored, filterable table so you can pick the best streaming opportunity at a glance.

Optional platforms: Epic Games Store, GOG Galaxy, Ubisoft Connect, EA App, Xbox / PC Game Pass.

---

## Prerequisites

- Python 3.10+
- PyQt6
- requests

```
pip install PyQt6 requests
```

- A **Steam API key** — [get one here](https://steamcommunity.com/dev/apikey)
- A **Twitch application** (Client ID + Client Secret) — [register here](https://dev.twitch.tv/console)
- `steam_appids.csv` — bundled in the repo (maps Steam app IDs to game names)

---

## Installation

```bash
git clone https://github.com/<your-org>/stream-recommender.git
cd stream-recommender
pip install PyQt6 requests
python "Stream Recommender.pyw"
```

No build step required.

---

## Configuration

On first launch, click **Settings** and fill in:

| Tab | Field | Notes |
|-----|-------|-------|
| Steam | API Key | Masked; stored locally |
| Twitch | Client ID | From your Twitch app |
| Twitch | Client Secret | Masked; stored locally |
| Platforms | Epic / GOG / Ubisoft / EA / Xbox | Enable per-platform toggles |

Config is saved locally next to the script.
API keys are never written to log files.

---

## Usage

1. Enter your **Twitch username** and **Steam ID or vanity URL** in the top bar.
2. Click **Fetch**.
3. The app resolves your Steam library, fetches Twitch top games, fuzzy-matches, and scores results.
4. Results appear in a sortable table: game name, Twitch rank, viewer count, stream count, your playtime, growth score, and platform.
5. Use the **search box**, **tag filter** (TOP / NICHE / COMMUNITY), and **platform filter** to narrow results.
6. Wishlist toggle lets you show/hide/only games on your Steam wishlist.

---

## How Matching Works

1. Owned Steam app IDs are resolved to names via the bundled `steam_appids.csv`.
2. Twitch top 500 games are fetched (paginated).
3. Each owned game is fuzzy-matched against the Twitch list using `difflib.SequenceMatcher` (threshold ≥ 0.85), with punctuation stripped and names lowercased.
4. Matched games are scored by a **growth score** combining Twitch rank, viewer-to-stream ratio, and recency signals.
5. Results are tagged: **TOP** (high viewers), **NICHE** (low competition), **COMMUNITY** (high ratio).

---

## Project Structure

```
stream_picker.py        — main app, UI, fetch logic, matching
settings_dialog.py      — Settings dialog (Steam / Twitch / Platforms tabs)
platforms.py            — Epic, GOG, Ubisoft, EA, Xbox library readers
Stream Recommender.pyw  — launch entry point (no console window)
steam_appids.csv        — bundled Steam app ID → name lookup
build.bat               — PyInstaller build script
```

---

## Platform Support Details

| Platform | Method |
|----------|--------|
| Steam | Official API |
| Epic Games Store | Local manifest files; falls back to manual paste |
| GOG Galaxy | Local SQLite DB (`galaxy-2.0.db`); falls back to manual paste |
| Ubisoft Connect | Manual text input (no public API) |
| EA App / Origin | Registry scan; falls back to manual text input |
| Xbox / PC Game Pass | PowerShell `Get-AppxPackage` (Windows only); falls back to manual input |

---

## Building the Exe

Run `build.bat` to produce a standalone executable (no Python required):

```
build.bat
```

Output: `dist\StreamRecommender\StreamRecommender.exe`

---

## Logs & Bug Reports

The app writes a log file each session to a `logs/` folder next to the executable.
If you encounter a bug, attach the relevant log file when reporting the issue.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Changelog

### 2026-07-04
- Initial public release
- Steam + Twitch core flow
- Platform stubs: Epic, GOG, Ubisoft, EA, Xbox
- Gr