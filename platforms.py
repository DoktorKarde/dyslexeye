"""
Platform handlers for Epic, GOG, Ubisoft, EA, Xbox.
All functions return a list of game name strings.
"""

import os
import json
import sqlite3
import logging
import subprocess
from pathlib import Path
import requests as _requests

log = logging.getLogger("stream_picker")

# ── Epic Games Store ──────────────────────────────────────────────────────────
def get_epic_games(cfg):
    """Try manifest files first; fall back to manual list in config."""
    games = _epic_from_manifests()
    if games:
        log.info(f"Epic: found {len(games)} games from manifests")
        return games
    manual = cfg.get("epic_manual", "")
    names = [l.strip() for l in manual.splitlines() if l.strip()]
    log.info(f"Epic: using {len(names)} manually entered games")
    return names

def _epic_from_manifests():
    manifest_dir = Path(os.environ.get("ProgramData", "C:/ProgramData")) /                    "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
    if not manifest_dir.exists():
        return []
    names = []
    for item_file in manifest_dir.glob("*.item"):
        try:
            with open(item_file, encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("DisplayName") or data.get("AppName")
            if name:
                names.append(name)
        except Exception as e:
            log.debug(f"Epic manifest parse error ({item_file.name}): {e}")
    return names




# ── GOG Galaxy ────────────────────────────────────────────────────────────────────────────
def get_gog_games(cfg=None):
    # 1. Profile URL/username if provided
    if cfg:
        profile = cfg.get("gog_profile", "").strip()
        if profile:
            games = _gog_from_profile(profile)
            if games:
                return games
    # 2. Local Galaxy DB
    return _gog_from_db()

def _gog_from_profile(profile):
    import urllib.request
    if "gog.com" in profile:
        username = profile.rstrip("/").split("/u/")[-1].split("/")[0]
    else:
        username = profile
    if not username:
        return []
    names = []
    page = 1
    while True:
        url = (
            f"https://www.gog.com/u/{username}/games/stats"
            f"?page={page}&sort=recent_playtime&order=desc&page_size=100"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
        except Exception as e:
            log.warning(f"GOG profile fetch failed (page {page}): {e}")
            break
        for item in data.get("_embedded", {}).get("items", []):
            title = item.get("game", {}).get("title")
            if title:
                names.append(title)
        if page >= data.get("pages", 1):
            break
        page += 1
    log.info(f"GOG: fetched {len(names)} games from profile '{username}'")
    return names

def _gog_from_db():
    db_path = Path(os.environ.get("ProgramData", "C:/ProgramData")) / \
              "GOG.com" / "Galaxy" / "storage" / "galaxy-2.0.db"
    if not db_path.exists():
        log.info("GOG: galaxy-2.0.db not found")
        return []
    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        cur.execute(
            "SELECT value FROM GamePieces WHERE releaseKey LIKE 'gog_%' "
            "AND value LIKE '%\"title\"%' LIMIT 2000"
        )
        rows = cur.fetchall()
        con.close()
        names = []
        for (val,) in rows:
            try:
                obj = json.loads(val)
                title = obj.get("title")
                if title and isinstance(title, str):
                    names.append(title)
            except Exception:
                pass
        names = list(dict.fromkeys(names))
        log.info(f"GOG: found {len(names)} games from local DB")
        return names
    except Exception as e:
        log.warning(f"GOG DB read failed: {e}")
        return []


# ── Ubisoft Connect ───────────────────────────────────────────────────────────
def get_ubisoft_games(cfg: dict) -> list[str]:
    """Manual input only — stored in config as 'ubisoft_games' (newline-separated)."""
    raw = cfg.get("ubisoft_games", "")
    return [l.strip() for l in raw.splitlines() if l.strip()]


# ── EA App / Origin ───────────────────────────────────────────────────────────
def get_ea_games(cfg: dict) -> list[str]:
    """Try registry auto-detection first; fall back to manual list in config."""
    games = _ea_from_registry()
    if games:
        log.info(f"EA: found {len(games)} games from registry")
        return games
    raw = cfg.get("ea_games", "")
    names = [l.strip() for l in raw.splitlines() if l.strip()]
    log.info(f"EA: using {len(names)} manually entered games")
    return names

def _ea_from_registry() -> list[str]:
    if os.name != "nt":
        return []
    try:
        import winreg
        names = []
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Electronic Arts"
        )
        i = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, i)
                # skip non-game entries
                if subkey_name.lower() not in {"ea desktop", "eadm", "origin"}:
                    names.append(subkey_name)
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
        return names
    except Exception as e:
        log.debug(f"EA registry read failed: {e}")
        return []


# ── Xbox / PC Game Pass ───────────────────────────────────────────────────────
_XBOX_PUBLISHER_SKIP = {
    "microsoft corporation", "microsoft game studios",
}
_XBOX_CATEGORY_KEYWORDS = {
    "game", "games", "entertainment",
}

def get_xbox_games(cfg: dict) -> list[str]:
    """Try PowerShell Get-AppxPackage; fall back to manual list."""
    games = _xbox_from_powershell()
    if games:
        log.info(f"Xbox: found {len(games)} games via PowerShell")
        return games
    manual = cfg.get("xbox_manual", "")
    names = [l.strip() for l in manual.splitlines() if l.strip()]
    log.info(f"Xbox: using {len(names)} manually entered games")
    return names

def _xbox_from_powershell() -> list[str]:
    if os.name != "nt":
        return []
    try:
        cmd = (
            "Get-AppxPackage | "
            "Where-Object { $_.SignatureKind -eq 'Store' } | "
            "Select-Object Name, PackageFullName | "
            "ConvertTo-Json -Depth 1"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []

        packages = json.loads(result.stdout)
        if isinstance(packages, dict):
            packages = [packages]

        # Heuristic: include packages whose Name looks like a game title
        # (exclude system/framework packages with dots and version strings)
        names: list[str] = []
        for pkg in packages:
            name = pkg.get("Name", "")
            # skip framework / system packages
            if (name.startswith("Microsoft.") and
                    any(skip in name.lower() for skip in
                        ["framework", "runtime", "vclib", "desktop", "ui.", "net.",
                         "windowsstore", "edge", "onedrive", "office"])):
                continue
            # basic heuristic: if it has 3+ parts separated by dots it's probably not a game
            if name.count(".") >= 3:
                continue
            # strip publisher prefix (e.g. "XboxGameStudios.Halo")
            display = name.split(".")[-1] if "." in name else name
            # remove camel-case spacing heuristic: "HaloInfinite" -> "Halo Infinite"
            import re
            display = re.sub(r"([a-z])([A-Z])", r"\1 \2", display)
            if display:
                names.append(display)
        return names
    except Exception as e:
        log.warning(f"Xbox PowerShell read failed: {e}")
        return []



# No Xbox web login: getting a usable Xbox Live session requires the user to
# paste a login.live.com redirect URL back into this app, and Microsoft shows
# an explicit anti-phishing warning on that exact page for exactly this
# pattern. get_xbox_library/get_xbox_wishlist below are kept for API
# compatibility but are never given a real session — Xbox relies on local
# PowerShell detection (get_xbox_games) or the manual list fallback instead.


def _xbox_headers(session_json: str) -> dict | None:
    if not session_json:
        return None
    try:
        sess = json.loads(session_json)
    except Exception:
        return None
    uhs, xsts = sess.get("uhs"), sess.get("xsts")
    if not uhs or not xsts:
        return None
    return {"Authorization": f"XBL3.0 x={uhs};{xsts}", "Accept": "application/json"}


def get_xbox_library(session_json: str) -> list[str]:
    """Fetch Xbox owned games + play history. `session_json` is
    {"uhs":..., "xsts":...} from xbox_login()."""
    headers = _xbox_headers(session_json)
    if not headers:
        return []
    try:
        headers["x-xbl-contract-version"] = "2"
        r = _requests.get(
            "https://titlehub.xboxlive.com/users/me/titles/titlehistory/decoration/detail",
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        titles = r.json().get("titles", [])
        names = [t["name"] for t in titles if t.get("name")]
        log.info(f"Xbox library: {len(names)} items")
        return names
    except Exception as e:
        log.warning(f"Xbox library fetch failed: {e}")
        return []

# Version 0.0.2



# ═══════════════════════════════════════════════════════════════════════════════
# Wishlist fetchers — use session tokens captured via login_browser.py
# ═══════════════════════════════════════════════════════════════════════════════


# No Epic OAuth login: the resulting code/token grants full account access
# (purchases, wallet, friends, cloud saves), and Epic's own API response says
# not to share it with any 3rd-party app — which this would be. get_epic_library
# is kept for import compatibility but is never given a real token; Epic relies
# on local manifest detection (get_epic_games) or the manual list fallback.
def get_epic_library(access_token: str) -> list[str]:
    return []


# EA / Origin: manual entry only. EA retired the old Origin entitlements
# API (api2.origin.com) when it moved everyone to the EA app — the
# consolidatedentitlements endpoint 404s unconditionally now. The
# replacement is a GraphQL-based API ("Juno") with a different login flow
# entirely; not worth chasing (open-source Origin plugins have been stuck
# on this same migration for over a year). get_ea_games() below already
# covers registry auto-detect + manual fallback.


# Ubisoft Connect: manual entry only. No public API; email/password login
# against Ubisoft's own server was tried and dropped — 2FA blocks it and
# there is no way to complete that challenge from a headless flow.


def get_xbox_wishlist(session_json: str) -> list[str]:
    """Fetch Xbox wishlist. `session_json` is {"uhs":..., "xsts":...}
    from xbox_login() — same session as get_xbox_library."""
    headers = _xbox_headers(session_json)
    if not headers:
        return []
    try:
        r = _requests.get(
            "https://wishlist.xboxlive.com/users/me/lists/wishlist",
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        # Response: {"lists": [{"items": [{"title": "...", ...}]}]}
        names = []
        for lst in data.get("lists", []):
            for item in lst.get("items", []):
                title = item.get("title") or item.get("productTitle")
                if title:
                    names.append(title)
        log.info(f"Xbox wishlist: {len(names)} items")
        return names
    except Exception as e:
        log.warning(f"Xbox wishlist fetch failed: {e}")
        return []
