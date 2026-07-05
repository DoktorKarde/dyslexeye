"""
Stream Recommender
Shows which games you own are worth streaming right now, ranked by Twitch popularity.
"""

import sys
import os
import json
import csv
import math
import time
import difflib
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy, QTreeWidget, QTreeWidgetItem, QComboBox, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QColor, QPalette, QPainter, QLinearGradient, QRadialGradient,
    QBrush, QPen, QFont
)

# ââ paths âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
BASE_DIR = Path(__file__).parent
CONFIG_PATH      = BASE_DIR / "stream_picker_config.json"
CSV_PATH         = BASE_DIR / "steam_appids.csv"
LOGS_DIR         = BASE_DIR / "logs"
FILTER_CACHE_PATH = BASE_DIR / "filtered_games.csv"

# ââ palette âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
C_BG       = "#0a0a0e"
C_GOLD     = "#c8960c"
C_GOLD_BR  = "#e8b830"
C_GOLD_DIM = "#9a7218"
C_GREEN    = "#4ade80"
C_RED      = "#f87171"
C_AMBER    = "#ffb74d"
C_YELLOW   = "#fde047"
C_BLUE     = "#60a5fa"
C_PURPLE   = "#510E8C"

# ââ stylesheet constants ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
_L = f"color:{C_GOLD}; font-size:11px; background:transparent;"
_LH = f"color:{C_GOLD_DIM}; font-size:10px; background:transparent;"
_ENTRY = (
    f"QLineEdit {{ background:{C_BG}; color:{C_GOLD}; border:1px solid {C_GOLD};"
    f" border-radius:5px; font-size:11px; padding:2px 6px; }}"
    f"QLineEdit:focus {{ border:1px solid {C_GOLD_BR}; }}"
)
_BTN = (
    f"QPushButton {{ background:#111118; color:{C_GOLD}; border:1px solid {C_GOLD};"
    f" border-radius:5px; font-size:11px; padding:3px 10px; }}"
    f"QPushButton:hover {{ border-color:{C_GOLD_BR}; color:{C_GOLD_BR}; }}"
)
_ABTN_G = (
    f"QPushButton {{ background:#052210; color:{C_GREEN}; border:1px solid {C_GREEN};"
    f" border-radius:7px; font-size:13px; font-weight:bold; padding:4px 14px; }}"
    f"QPushButton:hover {{ background:#083318; }}"
    f"QPushButton:disabled {{ background:{C_BG}; color:#2a6040; border-color:#2a6040; }}"
)
_LIST = (
    f"QListWidget {{ background:{C_BG}; color:{C_GOLD}; border:1px solid {C_GOLD};"
    f" border-radius:5px; font-size:11px; }}"
    f"QListWidget::item:selected {{ background:rgba(200,150,12,0.25); }}"
    f"QScrollBar:vertical {{ width:5px; background:transparent; }}"
    f"QScrollBar::handle:vertical {{ background:rgba(200,150,12,0.5); border-radius:2px; }}"
    f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}"
)


# ââ logging âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def setup_logger() -> logging.Logger:
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%A-%B-%d-%H_%M_%S")
    log_file = LOGS_DIR / f"{ts}.txt"
    logger = logging.getLogger("stream_picker")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", "%H:%M:%S"))
    logger.addHandler(fh)
    return logger

log = setup_logger()


# ââ config ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
DEFAULT_CONFIG: dict = {
    "twitch_username": "",
    "steam_id": "",
    "steam_api_key": "",
    "twitch_client_id": "",
    "twitch_client_secret": "",
    "epic_enabled": False,
    "epic_manual": "",
    "gog_enabled": False,
    "ubisoft_enabled": False,
    "ubisoft_games": "",
    "ea_enabled": False,
    "ea_games": "",
    "xbox_enabled": False,
    "xbox_manual": "",
}

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            log.warning(f"Config load failed: {e}")
    return dict(DEFAULT_CONFIG)

def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ââ Steam CSV lookup ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
_appid_map: dict[int, str] = {}

def load_steam_csv() -> None:
    if not CSV_PATH.exists():
        log.warning("steam_appids.csv not found â name lookup will be empty")
        return
    with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                _appid_map[int(row["appid"])] = row["name"]
            except (KeyError, ValueError):
                pass
    log.info(f"Loaded {len(_appid_map)} app IDs from steam_appids.csv")


# ââ filter cache (ratio pre-filter) ââââââââââââââââââââââââââââââââââââââââââ
_filtered_twitch_ids: set[str] = set()

def load_filter_cache() -> None:
    global _filtered_twitch_ids
    if not FILTER_CACHE_PATH.exists():
        return
    with open(FILTER_CACHE_PATH, encoding="utf-8", newline="") as f:
        _filtered_twitch_ids = {row["twitch_id"] for row in csv.DictReader(f)}
    log.info(f"Filter cache: {len(_filtered_twitch_ids)} games pre-filtered")

def update_filter_cache(results: list[dict]) -> None:
    """Add games outside 10â200 viewer/stream ratio to the blacklist."""
    existing: dict[str, dict] = {}
    if FILTER_CACHE_PATH.exists():
        with open(FILTER_CACHE_PATH, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                existing[row["twitch_id"]] = row
    for e in results:
        tid = e.get("twitch_id")
        if not tid or not e.get("stream_count"):
            continue
        ratio = e["viewers"] / e["stream_count"]
        if ratio < 10 or ratio > 200:
            existing[tid] = {
                "twitch_id": tid,
                "name": e["name"],
                "ratio": round(ratio, 1),
                "reason": "low" if ratio < 10 else "high",
            }
    with open(FILTER_CACHE_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["twitch_id", "name", "ratio", "reason"])
        w.writeheader()
        w.writerows(existing.values())
    _filtered_twitch_ids.update(existing.keys())
    log.info(f"Filter cache updated: {len(_filtered_twitch_ids)} total filtered")


def _blend(hex_color: str, r2: int, g2: int, b2: int, amount: float) -> str:
    """Blend hex_color toward an RGB target by amount (0â1)."""
    r1 = int(hex_color[1:3], 16)
    g1 = int(hex_color[3:5], 16)
    b1 = int(hex_color[5:7], 16)
    return (f"#{int(r1*(1-amount)+r2*amount):02x}"
            f"{int(g1*(1-amount)+g2*amount):02x}"
            f"{int(b1*(1-amount)+b2*amount):02x}")

def _red_tint(hex_color: str) -> str:
    return _blend(hex_color, 0xf8, 0x71, 0x71, 0.45)


# ââ Steam API âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def resolve_steam_id(vanity: str, key: str) -> str:
    if vanity.lstrip().startswith("765"):
        return vanity.strip()
    r = requests.get(
        "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
        params={"key": key, "vanityurl": vanity}, timeout=10
    )
    r.raise_for_status()
    resp = r.json().get("response", {})
    if resp.get("success") == 1:
        return resp["steamid"]
    raise ValueError(f"Steam ID not found for: {vanity}")

def get_owned_games(steam_id: str, key: str) -> list[dict]:
    r = requests.get(
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
        params={
            "key": key, "steamid": steam_id,
            "include_appinfo": "false",
            "include_played_free_games": "true",
            "format": "json",
        }, timeout=15
    )
    r.raise_for_status()
    games = r.json().get("response", {}).get("games", [])
    log.info(f"Got {len(games)} owned Steam games")
    return games

def get_wishlist_appids(steam_id, key):
    r = requests.get(
        "https://api.steampowered.com/IWishlistService/GetWishlist/v1/",
        params={"key": key, "steamid": steam_id}, timeout=15
    )
    r.raise_for_status()
    items = r.json().get("response", {}).get("items", [])
    log.info(f"Got {len(items)} wishlist items")
    return {int(item["appid"]) for item in items}


# ââ Twitch API ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
_twitch_token: str = ""
_twitch_token_expiry: float = 0.0

def get_twitch_token(client_id: str, client_secret: str) -> str:
    global _twitch_token, _twitch_token_expiry
    if _twitch_token and time.time() < _twitch_token_expiry:
        return _twitch_token
    r = requests.post("https://id.twitch.tv/oauth2/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }, timeout=10)
    r.raise_for_status()
    data = r.json()
    _twitch_token = data["access_token"]
    _twitch_token_expiry = time.time() + data.get("expires_in", 3600) - 60
    log.info("Twitch token obtained")
    return _twitch_token

def get_top_twitch_games(client_id: str, token: str, limit: int = 500) -> list[dict]:
    headers = {"Client-Id": client_id, "Authorization": f"Bearer {token}"}
    games: list[dict] = []
    cursor = None
    while len(games) < limit:
        params: dict = {"first": min(100, limit - len(games))}
        if cursor:
            params["after"] = cursor
        r = requests.get("https://api.twitch.tv/helix/games/top",
                         headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        batch = data.get("data", [])
        if not batch:
            break
        games.extend(batch)
        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            break
    log.info(f"Got {len(games)} top Twitch games")
    return games

def get_stream_stats(game_id: str, client_id: str, token: str) -> tuple[int, int]:
    """Returns (total_viewers, stream_count) for up to 100 live streams."""
    headers = {"Client-Id": client_id, "Authorization": f"Bearer {token}"}
    r = requests.get("https://api.twitch.tv/helix/streams",
                     headers=headers,
                     params={"game_id": game_id, "first": 100},
                     timeout=8)
    if r.status_code != 200:
        return 0, 0
    streams = r.json().get("data", [])
    viewers = sum(s.get("viewer_count", 0) for s in streams)
    return viewers, len(streams)

def batch_resolve_twitch_ids(names: list[str], client_id: str, token: str) -> dict[str, str]:
    """Batch-query Twitch /helix/games by name. Returns {name: game_id} for matches."""
    headers = {"Client-Id": client_id, "Authorization": f"Bearer {token}"}
    result: dict[str, str] = {}
    for i in range(0, len(names), 100):
        batch = names[i:i+100]
        try:
            r = requests.get("https://api.twitch.tv/helix/games",
                             headers=headers,
                             params=[("name", n) for n in batch],
                             timeout=10)
            if r.status_code != 200:
                continue
            for g in r.json().get("data", []):
                result[g["name"].lower()] = g["id"]
        except Exception as e:
            log.warning(f"batch_resolve_twitch_ids error: {e}")
    return result

def get_steamspy_players(appid: int) -> int:
    """Returns players_2weeks from SteamSpy as a community activity proxy. 0 on failure."""
    try:
        r = requests.get(
            "https://steamspy.com/api.php",
            params={"request": "appdetails", "appid": appid},
            timeout=8
        )
        if r.status_code == 200:
            return r.json().get("players_2weeks", 0) or 0
    except Exception:
        pass
    return 0


# ââ matching ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
import re as _re

def _norm(s: str) -> str:
    s = s.lower()
    s = _re.sub(r"[^\w\s]", "", s)
    return _re.sub(r"\s+", " ", s).strip()

def _best_twitch_match(name, twitch_norm):
    nn = _norm(name)
    best_ratio, best_tg, best_rank = 0.0, None, None
    for rank, (tn, tg) in enumerate(twitch_norm, 1):
        if nn == tn:
            return 1.0, tg, rank
        ratio = difflib.SequenceMatcher(None, nn, tn).ratio()
        if ratio > best_ratio:
            best_ratio, best_tg, best_rank = ratio, tg, rank
    return best_ratio, best_tg, best_rank

def build_game_entries(
    steam_games: list[dict],
    wishlist_appids: set,
    extra_entries: list[tuple],   # (name, platform)
    top500: list[dict],
    client_id: str,
    token: str,
    status_cb=None,
) -> list[dict]:
    """
    Primary: look up every owned game on Twitch directly and fetch live stats.
    Fallback: for games with no Twitch presence, query SteamSpy for community activity.
    Returns a list of result dicts sorted by viewers descending.
    """
    top500_norm = {_norm(g["name"]): g for g in top500}
    top500_rank  = {g["id"]: rank for rank, g in enumerate(top500, 1)}

    # --- collect all (appid, name, playtime_h, wishlist, platforms) ----
    entries: list[dict] = []
    seen_norm: set[str] = set()

    for game in steam_games:
        name = _appid_map.get(game["appid"])
        if not name:
            continue
        nn = _norm(name)
        if nn in seen_norm:
            continue
        seen_norm.add(nn)
        entries.append({
            "appid": game["appid"],
            "name": name,
            "playtime_h": round(game.get("playtime_forever", 0) / 60, 1),
            "wishlist": False,
            "platforms": ["Steam"],
        })

    for appid in wishlist_appids:
        name = _appid_map.get(appid)
        if not name:
            continue
        nn = _norm(name)
        if nn in seen_norm:
            continue
        seen_norm.add(nn)
        entries.append({
            "appid": appid,
            "name": name,
            "playtime_h": 0,
            "wishlist": True,
            "platforms": ["Steam"],
        })

    for name, platform in extra_entries:
        nn = _norm(name)
        if nn in seen_norm:
            # merge platform into existing
            for e in entries:
                if _norm(e["name"]) == nn:
                    if platform not in e["platforms"]:
                        e["platforms"].append(platform)
                    break
            continue
        seen_norm.add(nn)
        entries.append({
            "appid": None,
            "name": name,
            "playtime_h": 0,
            "wishlist": False,
            "platforms": [platform],
        })

    # --- Step 1: resolve Twitch IDs via top-500 fuzzy match -----------------
    for e in entries:
        nn = _norm(e["name"])
        # exact match against top 500 first
        if nn in top500_norm:
            g = top500_norm[nn]
            e["twitch_id"] = g["id"]
            e["twitch_rank"] = top500_rank[g["id"]]
            continue
        # fuzzy match
        best_ratio, best_g = 0.0, None
        for tn, g in top500_norm.items():
            r = difflib.SequenceMatcher(None, nn, tn).ratio()
            if r > best_ratio:
                best_ratio, best_g = r, g
        if best_ratio >= 0.85 and best_g:
            e["twitch_id"] = best_g["id"]
            e["twitch_rank"] = top500_rank[best_g["id"]]

    # --- Step 2: batch-resolve IDs for games still missing ------------------
    unresolved = [e for e in entries if "twitch_id" not in e]
    if unresolved:
        if status_cb:
            status_cb(f"Looking up {len(unresolved)} niche games on Twitch...")
        name_map = batch_resolve_twitch_ids(
            [e["name"] for e in unresolved], client_id, token)
        for e in unresolved:
            gid = name_map.get(e["name"].lower())
            if gid:
                e["twitch_id"] = gid
                e["twitch_rank"] = None  # not in top 500

    # --- Step 3: fetch live stream stats for all games with a Twitch ID -----
    has_twitch = [e for e in entries if "twitch_id" in e]
    no_twitch  = [e for e in entries if "twitch_id" not in e]

    if status_cb:
        status_cb(f"Fetching live stats for {len(has_twitch)} games...")

    results: list[dict] = []
    done_count = 0

    def _fetch_one(e):
        try:
            return e, *get_stream_stats(e["twitch_id"], client_id, token)
        except Exception:
            return e, 0, 0

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_fetch_one, e): e for e in has_twitch}
        for fut in as_completed(futures):
            nonlocal_e, viewers, stream_count = fut.result()
            done_count += 1
            if done_count % 20 == 0 and status_cb:
                status_cb(f"Fetching live stats... ({done_count}/{len(has_twitch)})")

            tag = "TOP" if nonlocal_e.get("twitch_rank") else ("NICHE" if stream_count > 0 else None)
            if tag is None:
                no_twitch.append(nonlocal_e)
                continue

            results.append({
                "name": nonlocal_e["name"],
                "twitch_rank": nonlocal_e.get("twitch_rank"),
                "twitch_id": nonlocal_e["twitch_id"],
                "viewers": viewers,
                "stream_count": stream_count,
                "playtime_h": nonlocal_e["playtime_h"],
                "wishlist": nonlocal_e["wishlist"],
                "platforms": nonlocal_e["platforms"],
                "tag": tag,
                "community_players": 0,
                "owned_status": "wishlist" if nonlocal_e["wishlist"] else "owned",
            })

    # --- Step 4: SteamSpy fallback for games with no live streams -----------
    if no_twitch:
        if status_cb:
            status_cb(f"Checking community activity for {len(no_twitch)} games...")

        def _spy_one(e):
            return e, get_steamspy_players(e["appid"]) if e.get("appid") else 0

        with ThreadPoolExecutor(max_workers=10) as pool:
            for e, players in pool.map(_spy_one, no_twitch):
                if players >= 500:
                    results.append({
                        "name": e["name"],
                        "twitch_rank": None,
                        "twitch_id": e.get("twitch_id"),
                        "viewers": 0,
                        "stream_count": 0,
                        "playtime_h": e["playtime_h"],
                        "wishlist": e["wishlist"],
                        "platforms": e["platforms"],
                        "tag": "COMMUNITY",
                        "community_players": players,
                        "owned_status": "wishlist" if e["wishlist"] else "owned",
                    })

    # sort: live viewers desc, then community_players desc
    results.sort(key=lambda x: (-(x["viewers"]), -(x["community_players"])))

    # append unowned top-500 games (not already in results)
    result_norms = {_norm(r["name"]) for r in results}
    for g in top500:
        nn = _norm(g["name"])
        if nn in result_norms:
            continue
        results.append({
            "name": g["name"],
            "twitch_rank": top500_rank[g["id"]],
            "twitch_id": g["id"],
            "viewers": 0,
            "stream_count": 0,
            "playtime_h": 0,
            "wishlist": False,
            "platforms": [],
            "tag": "TOP",
            "community_players": 0,
            "owned_status": "unowned",
        })
    log.info(
        f"Results: {sum(1 for r in results if r['tag']=='TOP')} top, "
        f"{sum(1 for r in results if r['tag']=='NICHE')} niche, "
        f"{sum(1 for r in results if r['tag']=='COMMUNITY')} community, "
        f"{sum(1 for r in results if r['wishlist'])} wishlist"
    )
    return results


# ââ background widget âââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
class BackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0
        self._blobs = [
            {
                "x": 0.1 + i * 0.12, "y": 0.2 + (i % 3) * 0.25,
                "r": 0.08 + (i % 4) * 0.02,
                "dx": 0.0003 * (1 if i % 2 == 0 else -1),
                "dy": 0.0002 * (1 if i % 3 == 0 else -1),
            }
            for i in range(9)
        ]
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(33)

    def _tick(self):
        self._t += 0.02
        for b in self._blobs:
            b["x"] = (b["x"] + b["dx"]) % 1.0
            b["y"] = (b["y"] + b["dy"]) % 1.0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        sweep = 0.5 + 0.5 * math.sin(self._t * 0.3)
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(10, 10, 14))
        grad.setColorAt(max(0.0, sweep - 0.15), QColor(10, 10, 14))
        grad.setColorAt(sweep, QColor(81, 14, 140, 110))
        grad.setColorAt(min(1.0, sweep + 0.15), QColor(10, 10, 14))
        grad.setColorAt(1.0, QColor(10, 10, 14))
        p.fillRect(0, 0, w, h, grad)

        for i, b in enumerate(self._blobs):
            pulse = 0.9 + 0.1 * math.sin(self._t + i * 0.7)
            cx, cy = b["x"] * w, b["y"] * h
            r = b["r"] * min(w, h) * pulse
            rg = QRadialGradient(cx, cy, r)
            rg.setColorAt(0.0, QColor(143, 111, 255, 55))
            rg.setColorAt(0.5, QColor(81, 14, 140, 25))
            rg.setColorAt(1.0, QColor(10, 10, 14, 0))
            p.setBrush(QBrush(rg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), r, r)
        p.end()


# ââ fetch worker ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
class FetchWorker(QThread):
    done   = pyqtSignal(list)
    error  = pyqtSignal(str, str)   # (message, level)
    status = pyqtSignal(str)

    def __init__(self, cfg: dict, extra_games: list[str]):
        super().__init__()
        self._cfg = cfg
        self._extra = extra_games
        self._retried = False

    def run(self):
        cfg = self._cfg
        log.info("FetchWorker.run() started")
        try:
            if not cfg.get("steam_api_key"):
                self.error.emit("Steam API key missing â open Settings", "amber"); return
            if not cfg.get("steam_id"):
                self.error.emit("Steam ID / vanity URL missing", "amber"); return

            self.status.emit("Resolving Steam ID...")
            steam_id = resolve_steam_id(cfg["steam_id"], cfg["steam_api_key"])

            self.status.emit("Fetching owned Steam games...")
            owned = get_owned_games(steam_id, cfg["steam_api_key"])

            self.status.emit("Fetching wishlist...")
            try:
                wishlist_appids = get_wishlist_appids(steam_id, cfg["steam_api_key"])
            except Exception as e:
                log.warning(f"Wishlist fetch failed (non-fatal): {e}")
                wishlist_appids = set()

            self.status.emit("Authenticating with Twitch...")
            token = get_twitch_token(cfg["twitch_client_id"], cfg["twitch_client_secret"])

            self.status.emit("Fetching Twitch top 500 for ranking context...")
            top500 = get_top_twitch_games(cfg["twitch_client_id"], token)

            results = build_game_entries(
                steam_games=owned,
                wishlist_appids=wishlist_appids,
                extra_entries=self._extra,
                top500=top500,
                client_id=cfg["twitch_client_id"],
                token=token,
                status_cb=self.status.emit,
            )

            update_filter_cache(results)
            self.done.emit(results)

        except ValueError as e:
            self.error.emit(str(e), "red")
        except requests.RequestException as e:
            if not self._retried:
                log.warning(f"Network error, retrying: {e}")
                self._retried = True
                time.sleep(1.5)
                self.run()
            else:
                self.error.emit(f"Network error: {e}", "red")
        except Exception as e:
            log.error(f"Unexpected error: {e}", exc_info=True)
            self.error.emit(f"Error: {e}", "red")



# -- main window ---------------------------------------------------------------

TAG_COLORS = {
    "TOP":       "#4ade80",
    "NICHE":     "#fde047",
    "COMMUNITY": "#60a5fa",
}

_TREE_STYLE = (
    "QTreeWidget { background:#0a0a0e; color:#c8960c; border:1px solid #c8960c;"
    " border-radius:5px; font-size:10px; outline:0; }"
    "QTreeWidget::item { padding:2px 0; }"
    "QTreeWidget::item:selected { background:rgba(200,150,12,0.25); }"
    "QHeaderView::section { background:#111118; color:#c8960c;"
    " border:1px solid #9a7218; padding:3px 6px; font-size:10px; font-weight:bold; }"
    "QHeaderView::section:hover { color:#e8b830; border-color:#e8b830; }"
    "QScrollBar:vertical { width:5px; background:transparent; }"
    "QScrollBar::handle:vertical { background:rgba(200,150,12,0.5); border-radius:2px; }"
    "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
)

_COMBO_STYLE = (
    "QComboBox { background:#0a0a0e; color:#c8960c; border:1px solid #c8960c;"
    " border-radius:5px; font-size:10px; padding:2px 6px; }"
    "QComboBox:hover { border-color:#e8b830; }"
    "QComboBox::drop-down { border:none; width:18px; }"
    "QComboBox QAbstractItemView { background:#0a0a0e; color:#c8960c;"
    " selection-background-color:rgba(200,150,12,0.25); border:1px solid #c8960c; }"
)

_FILTER_ENTRY = (
    "QLineEdit { background:#0a0a0e; color:#c8960c; border:1px solid #c8960c;"
    " border-radius:5px; font-size:10px; padding:2px 6px; }"
    "QLineEdit:focus { border-color:#e8b830; }"
)

_POPUP_STYLE = (
    "QFrame#ratioPopup { background:#0d0d12; border:1px solid #c8960c; border-radius:6px; }"
)


# Ratio ranges: (label, lo, hi_exclusive)
RATIO_RANGES = [
    ("Dead    < 5:1",    0,    5),
    ("Low   5-10:1",    5,   10),
    ("Good 10-50:1",   10,   50),
    ("Hot  50-200:1",  50,  200),
    ("Huge  > 200:1", 200,  9e9),
]


class RatioFilterPopup(QFrame):
    """Popup panel with multi-state ratio range filters and format toggle."""
    changed = pyqtSignal()

    _STATE_LABELS = ["[ ]", "[x]", "[-]"]

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("ratioPopup")
        self.setStyleSheet(_POPUP_STYLE)
        self._states = [0] * len(RATIO_RANGES)   # 0=neutral 1=include 2=exclude
        self._fmt_vc  = True                       # True = "v:c", False = "x.x v/ch"
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(3)

        hdr = QLabel("Ratio = [viewers]:[channels]")
        hdr.setStyleSheet("color:#9a7218; font-size:10px; background:transparent;")
        lay.addWidget(hdr)

        self._fmt_btn = QPushButton("Format: v:c  (click to switch)")
        self._fmt_btn.setStyleSheet(_BTN)
        self._fmt_btn.clicked.connect(self._toggle_fmt)
        lay.addWidget(self._fmt_btn)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:rgba(200,150,12,0.3);")
        lay.addWidget(sep)

        self._range_btns = []
        for i, (label, _, _hi) in enumerate(RATIO_RANGES):
            btn = QPushButton(f"[ ]  {label}")
            btn.setStyleSheet(_BTN)
            btn.clicked.connect(lambda _, idx=i: self._cycle(idx))
            lay.addWidget(btn)
            self._range_btns.append(btn)

        self.adjustSize()

    def _cycle(self, idx):
        self._states[idx] = (self._states[idx] + 1) % 3
        lbl = self._STATE_LABELS[self._states[idx]]
        name = RATIO_RANGES[idx][0]
        self._range_btns[idx].setText(f"{lbl}  {name}")
        self.changed.emit()

    def _toggle_fmt(self):
        self._fmt_vc = not self._fmt_vc
        if self._fmt_vc:
            self._fmt_btn.setText("Format: v:c  (click to switch)")
        else:
            self._fmt_btn.setText("Format: x viewers/channel  (click to switch)")
        self.changed.emit()

    def format_ratio(self, viewers: int, streams: int) -> str:
        if not streams:
            return "--"
        ratio = viewers / streams
        return f"{round(ratio):,}:1"

    def ratio_sort_key(self, viewers: int, streams: int) -> float:
        """Growth score: peak at 50-200:1, penalise dead (<5) and huge (>200) ends."""
        if not streams:
            return 0.0
        ratio = viewers / streams
        # Score 0-1 based on growth potential
        if ratio < 5:      # Dead
            return ratio / 5 * 0.1
        elif ratio < 10:   # Low
            return 0.1 + (ratio - 5) / 5 * 0.2
        elif ratio < 50:   # Good
            return 0.3 + (ratio - 10) / 40 * 0.3
        elif ratio < 200:  # Hot — best growth range
            return 0.6 + (1 - abs(ratio - 100) / 100) * 0.4
        else:              # Huge — saturated, hard to grow
            return max(0.0, 0.6 - (ratio - 200) / 800 * 0.6)

    def passes(self, viewers: int, streams: int) -> bool:
        ratio = (viewers / streams) if streams else 0.0
        has_include = any(s == 1 for s in self._states)
        for i, (_, lo, hi) in enumerate(RATIO_RANGES):
            in_range = lo <= ratio < hi
            if self._states[i] == 2 and in_range:   # explicitly excluded
                return False
            if self._states[i] == 1 and in_range:   # explicitly included
                return True
        return not has_include   # if any [x] active, only show matched ranges


class SortableItem(QTreeWidgetItem):
    def __lt__(self, other):
        col = self.treeWidget().sortColumn()
        if col == -1:  # growth score mode
            a = self.data(2, Qt.ItemDataRole.UserRole + 1)
            b = other.data(2, Qt.ItemDataRole.UserRole + 1)
            try: return float(a or 0) < float(b or 0)
            except: return False
        a = self.data(col, Qt.ItemDataRole.UserRole)
        b = other.data(col, Qt.ItemDataRole.UserRole)
        # Columns with no UserRole → alphabetical
        if a is None and b is None:
            return str(self.text(col)) < str(other.text(col))
        try:
            return float(a or 0) < float(b or 0)
        except (TypeError, ValueError):
            return str(self.text(col)) < str(other.text(col))


class MainWindow(QMainWindow):
    _WL_ALL  = 0
    _WL_ONLY = 1
    _WL_HIDE = 2

    def __init__(self, cfg: dict):
        super().__init__()
        self._cfg      = cfg
        self._sessions = {
            k: cfg[f"{k}_session"]
            for k in ("epic", "xbox")
            if cfg.get(f"{k}_session")
        }
        self._worker       = None
        self._results      = []
        self._wl_state     = self._WL_ALL
        self._hide_unowned = True
        self._sort_col     = -1                         # -1 = growth score mode
        self._sort_order   = Qt.SortOrder.DescendingOrder

        self.setWindowTitle("Stream Recommender")
        self.setFixedSize(860, 900)

        self._bg = BackgroundWidget(self)
        self.setCentralWidget(self._bg)

        root = QVBoxLayout(self._bg)
        root.setContentsMargins(14, 14, 14, 8)
        root.setSpacing(6)

        # top bar
        top = QHBoxLayout(); top.setSpacing(6)

        self._twitch_in = QLineEdit(placeholderText="Twitch username")
        self._twitch_in.setStyleSheet(_ENTRY)
        self._twitch_in.setText(cfg.get("twitch_username", ""))

        self._steam_in = QLineEdit(placeholderText="Steam ID or vanity URL")
        self._steam_in.setStyleSheet(_ENTRY)
        self._steam_in.setText(cfg.get("steam_id", ""))

        self._fetch_btn = QPushButton("  Fetch")
        self._fetch_btn.setStyleSheet(_ABTN_G)
        self._fetch_btn.clicked.connect(self._start_fetch)
        self._fetch_btn.setFixedWidth(100)

        self._settings_btn = QPushButton("Settings")
        self._settings_btn.setStyleSheet(_BTN)
        self._settings_btn.clicked.connect(self._open_settings)

        top.addWidget(self._twitch_in, 2)
        top.addWidget(self._steam_in, 2)
        top.addWidget(self._fetch_btn)
        top.addWidget(self._settings_btn)
        root.addLayout(top)

        # filter bar
        fbar = QHBoxLayout(); fbar.setSpacing(6)

        self._search = QLineEdit(placeholderText="Search game name...")
        self._search.setStyleSheet(_FILTER_ENTRY)
        self._search.textChanged.connect(self._apply_filters)

        self._tag_cb = QComboBox()
        self._tag_cb.addItems(["All Tags", "TOP", "NICHE", "COMMUNITY"])
        self._tag_cb.setStyleSheet(_COMBO_STYLE)
        self._tag_cb.setFixedWidth(100)
        self._tag_cb.currentIndexChanged.connect(self._apply_filters)

        self._plat_cb = QComboBox()
        self._plat_cb.addItem("All Platforms")
        self._plat_cb.setStyleSheet(_COMBO_STYLE)
        self._plat_cb.setFixedWidth(110)
        self._plat_cb.currentIndexChanged.connect(self._apply_filters)

        # ratio filter popup button
        self._ratio_popup = RatioFilterPopup(self)
        self._ratio_popup.changed.connect(self._apply_filters)
        self._ratio_popup.hide()
        self._ratio_btn = QPushButton("Ratio Filter")
        self._ratio_btn.setStyleSheet(_BTN)
        self._ratio_btn.setFixedWidth(100)
        self._ratio_btn.clicked.connect(self._show_ratio_popup)

        self._wl_btn = QPushButton("[ ] Wishlist")
        self._wl_btn.setStyleSheet(_BTN)
        self._wl_btn.setFixedWidth(100)
        self._wl_btn.clicked.connect(self._cycle_wishlist)

        self._owned_btn = QPushButton("[x] Owned Only")
        self._owned_btn.setStyleSheet(_BTN)
        self._owned_btn.setFixedWidth(112)
        self._owned_btn.clicked.connect(self._toggle_owned)

        self._growth_btn = QPushButton("[x] Growth Sort")
        self._growth_btn.setStyleSheet(_BTN)
        self._growth_btn.setFixedWidth(112)
        self._growth_btn.clicked.connect(self._toggle_growth_sort)

        fbar.addWidget(self._search, 3)
        fbar.addWidget(self._tag_cb)
        fbar.addWidget(self._plat_cb)
        fbar.addWidget(self._ratio_btn)
        fbar.addWidget(self._wl_btn)
        fbar.addWidget(self._owned_btn)
        fbar.addWidget(self._growth_btn)
        root.addLayout(fbar)

        # tree
        self._tree = QTreeWidget()
        self._tree.setStyleSheet(_TREE_STYLE)
        self._tree.setFont(QFont("Consolas", 10))
        self._tree.setRootIsDecorated(False)
        self._tree.setSortingEnabled(True)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        cols = ["Tag", "Game Name", "Ratio", "Playtime", "Platform", "Owned"]
        self._tree.setColumnCount(len(cols))
        self._tree.setHeaderLabels(cols)

        hdr = self._tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed);       self._tree.setColumnWidth(0, 72)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed);       self._tree.setColumnWidth(2, 110)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed);       self._tree.setColumnWidth(3, 68)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed);       self._tree.setColumnWidth(4, 80)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed);       self._tree.setColumnWidth(5, 62)
        hdr.setSortIndicatorShown(False)  # default mode is growth score — no column selected
        hdr.sectionClicked.connect(self._on_sort_column)

        root.addWidget(self._tree, 1)

        self._status = QLabel("Ready.")
        self._status.setStyleSheet(_L)
        root.addWidget(self._status)



    # helpers

    def _set_status(self, msg: str, color: str = C_GOLD):
        self._status.setStyleSheet(f"color:{color}; font-size:11px; background:transparent;")
        self._status.setText(msg)

    def _show_ratio_popup(self):
        btn_pos = self._ratio_btn.mapToGlobal(self._ratio_btn.rect().bottomLeft())
        self._ratio_popup.move(btn_pos)
        self._ratio_popup.show()
        self._ratio_popup.raise_()

    def _cycle_wishlist(self):
        self._wl_state = (self._wl_state + 1) % 3
        labels = {self._WL_ALL: "[ ] Wishlist", self._WL_ONLY: "[x] Wishlist", self._WL_HIDE: "[-] Wishlist"}
        self._wl_btn.setText(labels[self._wl_state])
        self._apply_filters()

    def _toggle_growth_sort(self):
        if self._sort_col == -1:
            # Deactivate — fall back to Ratio numeric desc
            self._sort_col   = 2
            self._sort_order = Qt.SortOrder.DescendingOrder
            self._growth_btn.setText("[ ] Growth Sort")
        else:
            self._sort_col   = -1
            self._sort_order = Qt.SortOrder.DescendingOrder
            self._growth_btn.setText("[x] Growth Sort")
        self._apply_filters()

    def _on_sort_column(self, col: int):
        # Column click deactivates growth sort
        if self._sort_col == -1:
            self._growth_btn.setText("[ ] Growth Sort")
        if col == self._sort_col:
            self._sort_order = (
                Qt.SortOrder.AscendingOrder
                if self._sort_order == Qt.SortOrder.DescendingOrder
                else Qt.SortOrder.DescendingOrder
            )
        else:
            self._sort_col = col
            self._sort_order = (
                Qt.SortOrder.DescendingOrder if col in (2, 3)
                else Qt.SortOrder.AscendingOrder
            )
        self._apply_filters()

    def _toggle_owned(self):
        self._hide_unowned = not self._hide_unowned
        self._owned_btn.setText("[x] Owned Only" if self._hide_unowned else "[ ] Owned Only")
        self._apply_filters()

    def _apply_filters(self):
        search    = self._search.text().strip().lower()
        tag_filt  = self._tag_cb.currentText()
        plat_filt = self._plat_cb.currentText()

        self._tree.setUpdatesEnabled(False)
        self._tree.clear()

        owned_rows = []
        wish_rows  = []

        for e in self._results:
            is_wish = bool(e.get("wishlist"))

            if self._wl_state == self._WL_ONLY and not is_wish:
                continue
            if self._wl_state == self._WL_HIDE and is_wish:
                continue
            if self._hide_unowned and e.get('owned_status') == 'unowned':
                continue
            if search and search not in e["name"].lower():
                continue
            if tag_filt != "All Tags" and e.get("tag") != tag_filt:
                continue
            if plat_filt != "All Platforms" and plat_filt not in e.get("platforms", []):
                continue
            if not self._ratio_popup.passes(e.get("viewers", 0), e.get("stream_count", 0)):
                continue

            row = self._make_row(e)
            (wish_rows if is_wish else owned_rows).append(row)

        self._tree.addTopLevelItems(owned_rows + wish_rows)

        if self._sort_col == -1:
            # Growth-score mode: manual reorder. Keep sortingEnabled OFF and
            # the header indicator hidden — calling setSortIndicator() with
            # sortingEnabled True would trigger Qt's built-in column-2 sort
            # and silently clobber this ordering right after we set it.
            self._tree.setSortingEnabled(False)
            items = [self._tree.takeTopLevelItem(0)
                     for _ in range(self._tree.topLevelItemCount())]
            items.sort(key=lambda it: it.data(2, Qt.ItemDataRole.UserRole + 1) or 0,
                       reverse=(self._sort_order == Qt.SortOrder.DescendingOrder))
            self._tree.addTopLevelItems(items)
            self._tree.header().setSortIndicatorShown(False)
        else:
            self._tree.setSortingEnabled(True)
            self._tree.sortItems(self._sort_col, self._sort_order)
            self._tree.header().setSortIndicatorShown(True)
            self._tree.header().setSortIndicator(self._sort_col, self._sort_order)
        self._tree.setUpdatesEnabled(True)

    def _make_row(self, e: dict) -> SortableItem:
        tag      = e.get("tag", "TOP")
        owned_st = e.get("owned_status", "owned")
        platforms = ", ".join(e.get("platforms", []))
        viewers  = e.get("viewers", 0)
        streams  = e.get("stream_count", 0)
        playtime = e.get("playtime_h", 0)
        comm     = e.get("community_players", 0)

        # row colour: dim unowned games
        if owned_st == "unowned":
            row_color = QColor(C_GOLD_DIM)
        else:
            row_color = QColor(TAG_COLORS.get(tag, C_GOLD))

        ratio_disp = self._ratio_popup.format_ratio(viewers or comm, streams)
        t_disp     = f"{playtime}h" if playtime else "--"

        # owned column: coloured symbol
        if owned_st == "owned":
            owned_disp = "✓"
            owned_color = QColor(C_GREEN)
        elif owned_st == "wishlist":
            owned_disp = "—"
            owned_color = QColor(C_GOLD_DIM)
        else:
            owned_disp = "✗"
            owned_color = QColor(C_RED)

        raw_ratio   = (viewers or comm) / streams if streams else 0.0
        growth_score = self._ratio_popup.ratio_sort_key(viewers or comm, streams)
        item = SortableItem([tag, e["name"], ratio_disp, t_disp, platforms, owned_disp])
        item.setData(2, Qt.ItemDataRole.UserRole, raw_ratio)          # numeric ratio
        item.setData(2, Qt.ItemDataRole.UserRole + 1, growth_score)   # growth score
        item.setData(3, Qt.ItemDataRole.UserRole, float(playtime))

        for col in range(5):
            item.setForeground(col, row_color)
        item.setForeground(5, owned_color)
        return item

    def _update_platform_combo(self):
        current = self._plat_cb.currentText()
        platforms = set()
        for e in self._results:
            platforms.update(e.get("platforms", []))
        self._plat_cb.blockSignals(True)
        self._plat_cb.clear()
        self._plat_cb.addItem("All Platforms")
        for p in sorted(platforms):
            self._plat_cb.addItem(p)
        idx = self._plat_cb.findText(current)
        self._plat_cb.setCurrentIndex(max(0, idx))
        self._plat_cb.blockSignals(False)

    # fetch

    def _start_fetch(self):
        if self._worker and self._worker.isRunning():
            return
        self._cfg["twitch_username"] = self._twitch_in.text().strip()
        self._cfg["steam_id"]        = self._steam_in.text().strip()
        save_config(self._cfg)
        try:
            extra = self._gather_extra_games()
        except Exception as exc:
            import traceback as _tb
            log.error("gather_extra_games: " + str(exc) + "\n" + _tb.format_exc())
            self._set_status("Platform load error: " + str(exc), C_RED)
            return
        self._tree.clear()
        self._fetch_btn.setEnabled(False)
        self._set_status("Starting...")

        self._worker = FetchWorker(self._cfg, extra)
        self._worker.done.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.status.connect(self._set_status)
        self._worker.start()

    def _gather_extra_games(self) -> list:
        from platforms import (
            get_epic_games, get_epic_library,
            get_gog_games,
            get_ubisoft_games,
            get_ea_games,
            get_xbox_games, get_xbox_library, get_xbox_wishlist,
        )
        games = []

        # ── Epic ─────────────────────────────────────────────────────────────
        if self._cfg.get("epic_enabled"):
            sess = self._sessions.get("epic")
            if sess:
                # Session: full library + wishlist via API
                games.extend((n, "Epic") for n in get_epic_library(sess))
            else:
                # No session: local manifests (installed games only)
                games.extend((n, "Epic") for n in get_epic_games(self._cfg))

        # ── GOG ──────────────────────────────────────────────────────────────
        if self._cfg.get("gog_enabled"):
            games.extend((n, "GOG") for n in get_gog_games(self._cfg))

        # ── Ubisoft ──────────────────────────────────────────────────────────
        # Manual entry only — no login flow (2FA blocks Ubisoft's own login API).
        if self._cfg.get("ubisoft_enabled"):
            games.extend((n, "Ubisoft") for n in get_ubisoft_games(self._cfg))

        # ── EA ────────────────────────────────────────────────────────────────
        # Manual entry only — EA retired the old Origin cookie-auth API.
        if self._cfg.get("ea_enabled"):
            games.extend((n, "EA") for n in get_ea_games(self._cfg))

        # ── Xbox ─────────────────────────────────────────────────────────────
        if self._cfg.get("xbox_enabled"):
            sess = self._sessions.get("xbox")
            if sess:
                # Session: full library + wishlist
                games.extend((n, "Xbox") for n in get_xbox_library(sess))
                games.extend((n, "Xbox") for n in get_xbox_wishlist(sess))
            else:
                # No session: installed games via PowerShell
                games.extend((n, "Xbox") for n in get_xbox_games(self._cfg))

        return games

    def _on_results(self, results: list):
        self._fetch_btn.setEnabled(True)
        self._results = results
        self._update_platform_combo()
        self._apply_filters()
        top_c   = sum(1 for e in results if e.get("tag") == "TOP")
        niche_c = sum(1 for e in results if e.get("tag") == "NICHE")
        comm_c  = sum(1 for e in results if e.get("tag") == "COMMUNITY")
        wish_c  = sum(1 for e in results if e.get("wishlist"))
        ts = datetime.now().strftime("%H:%M:%S")
        self._set_status(
            f"{top_c} top  {niche_c} niche  {comm_c} community  {wish_c} wishlist -- {ts}",
            C_GREEN)
        log.info(f"Displayed {len(results)} results")

    def _on_error(self, msg: str, level: str):
        self._fetch_btn.setEnabled(True)
        self._set_status(msg, C_RED if level == "red" else C_AMBER)
        if level == "amber":
            self._open_settings()

    def _open_settings(self):
        from settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._cfg, self._sessions, self)
        if dlg.exec():
            self._cfg     = dlg.get_config()
            self._sessions.update(dlg.get_sessions())
            save_config(self._cfg)

    def resizeEvent(self, e):
        self._bg.resize(self.size())
        super().resizeEvent(e)


# ââ entry point âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
def main():
    load_steam_csv()
    load_filter_cache()
    cfg = load_config()
    log.info(
        "Session initialised. Primary source: Steam library. "
        "Additional platform integrations (Epic, GOG, Ubisoft, EA, Xbox) "
        "are available under Settings."
    )

    # WebEngine flags — must be set BEFORE QApplication is created
    try:
        from PyQt6.QtWebEngineCore import QWebEngineUrlScheme  # noqa
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        # Disable GPU rendering — prevents renderer process crashes on many systems
        import os as _os
        _os.environ.setdefault(
            "QTWEBENGINE_CHROMIUM_FLAGS",
            "--disable-gpu --disable-software-rasterizer --no-sandbox"
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,      QColor(10, 10, 14))
    pal.setColor(QPalette.ColorRole.WindowText,  QColor(200, 150, 12))
    pal.setColor(QPalette.ColorRole.Base,        QColor(10, 10, 14))
    pal.setColor(QPalette.ColorRole.Text,        QColor(200, 150, 12))
    app.setPalette(pal)

    win = MainWindow(cfg)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# Version 0.0.1
