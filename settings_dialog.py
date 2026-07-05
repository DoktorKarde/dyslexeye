"""
Settings dialog — Steam, Twitch, Platforms tabs.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette

# ── palette constants (duplicated to keep this module self-contained) ─────────
C_BG       = "#0a0a0e"
C_GOLD     = "#c8960c"
C_GOLD_BR  = "#e8b830"
C_GOLD_DIM = "#9a7218"
C_GREEN    = "#4ade80"
C_RED      = "#f87171"

_L = f"color:{C_GOLD}; font-size:11px; background:transparent;"
_LH = f"color:{C_GOLD_DIM}; font-size:10px; background:transparent;"
_ENTRY = (
    f"QLineEdit {{ background:{C_BG}; color:{C_GOLD}; border:1px solid {C_GOLD};"
    f" border-radius:5px; font-size:11px; padding:2px 6px; }}"
    f"QLineEdit:focus {{ border:1px solid {C_GOLD_BR}; }}"
)
_TE = (
    f"QTextEdit {{ background:{C_BG}; color:{C_GOLD}; border:1px solid {C_GOLD};"
    f" border-radius:5px; font-size:11px; padding:4px; }}"
)
_BTN = (
    f"QPushButton {{ background:#111118; color:{C_GOLD}; border:1px solid {C_GOLD};"
    f" border-radius:5px; font-size:11px; padding:3px 10px; }}"
    f"QPushButton:hover {{ border-color:{C_GOLD_BR}; color:{C_GOLD_BR}; }}"
)
_BTN_RED = (
    f"QPushButton {{ background:#1a0505; color:{C_RED}; border:1px solid {C_RED};"
    f" border-radius:5px; font-size:11px; padding:3px 10px; }}"
    f"QPushButton:hover {{ background:#2a0808; }}"
)
_ABTN_G = (
    f"QPushButton {{ background:#052210; color:{C_GREEN}; border:1px solid {C_GREEN};"
    f" border-radius:7px; font-size:13px; font-weight:bold; padding:4px 14px; }}"
    f"QPushButton:hover {{ background:#083318; }}"
)
_TABS = (
    f"QTabWidget::pane {{ border:1px solid rgba(143,111,255,80); background:{C_BG}; }}"
    f"QTabBar::tab {{ background:{C_BG}; color:{C_GOLD_DIM}; padding:5px 14px;"
    f" font-size:11px; border:1px solid rgba(143,111,255,50); }}"
    f"QTabBar::tab:selected {{ color:{C_GOLD}; border-bottom:2px solid {C_GOLD}; }}"
    f"QTabBar::tab:hover {{ color:{C_GOLD_BR}; }}"
)
_CHECK = (
    f"QCheckBox {{ color:{C_GOLD}; font-size:11px; }}"
    f"QCheckBox::indicator {{ width:14px; height:14px; background:{C_BG};"
    f" border:1px solid {C_GOLD}; border-radius:3px; }}"
    f"QCheckBox::indicator:checked {{ background:#0a2210; border-color:{C_GREEN}; }}"
)
_SCROLLBAR = (
    f"QScrollBar:vertical {{ width:5px; background:transparent; }}"
    f"QScrollBar::handle:vertical {{ background:rgba(200,150,12,0.5); border-radius:2px; }}"
    f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}"
)


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color:rgba(200,150,12,0.2);")
    return f


def _masked_row(label_text):
    lbl = QLabel(label_text)
    lbl.setStyleSheet(_L)
    field = QLineEdit()
    field.setStyleSheet(_ENTRY)
    field.setEchoMode(QLineEdit.EchoMode.Password)
    toggle = QPushButton("Show")
    toggle.setStyleSheet(_BTN)
    toggle.setFixedWidth(52)
    toggle.setCheckable(True)

    def _toggle(checked):
        field.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
        toggle.setText("Hide" if checked else "Show")

    toggle.toggled.connect(_toggle)
    return lbl, field, toggle


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, sessions: dict, parent=None):
        super().__init__(parent)
        self._cfg      = dict(cfg)
        # sessions: {platform_key: token_str} — in-memory, not in config unless user opts in
        self._sessions = dict(sessions)

        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setStyleSheet(f"QDialog {{ background:{C_BG}; color:{C_GOLD}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        tabs = QTabWidget()
        tabs.setStyleSheet(_TABS + _SCROLLBAR)
        root.addWidget(tabs)

        tabs.addTab(self._steam_tab(),     "Steam")
        tabs.addTab(self._twitch_tab(),    "Twitch")
        tabs.addTab(self._platforms_tab(), "Platforms")

        root.addWidget(_sep())

        # Save / Cancel
        btns = QHBoxLayout()
        btns.addStretch()
        save = QPushButton("Save")
        save.setStyleSheet(_ABTN_G)
        save.clicked.connect(self._save)
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(_BTN)
        cancel.clicked.connect(self.reject)
        btns.addWidget(save)
        btns.addWidget(cancel)
        root.addLayout(btns)

    # ── login helper ──────────────────────────────────────────────────────────

    def _make_login_row(self, platform_key: str, lay):
        """Add a Login button + status label + save-session checkbox to lay."""
        from login_browser import get_login_dialog, PLATFORM_CONFIGS
        cfg_p = PLATFORM_CONFIGS[platform_key]

        row = QHBoxLayout()
        row.setSpacing(8)

        # Login / Disconnect button
        has_session = bool(self._sessions.get(platform_key))
        login_btn = QPushButton("Disconnect" if has_session else "Login")
        login_btn.setStyleSheet(_BTN_RED if has_session else _BTN)
        login_btn.setFixedWidth(90)

        # Status label
        status_lbl = QLabel(
            f"Connected ✓" if has_session else "Not connected"
        )
        status_lbl.setStyleSheet(
            f"color:{C_GREEN}; font-size:10px;" if has_session
            else f"color:{C_GOLD_DIM}; font-size:10px;"
        )

        # Save session checkbox
        save_cb = QCheckBox("Save session to config")
        save_cb.setStyleSheet(_CHECK)
        save_cb.setChecked(bool(self._cfg.get(f"{platform_key}_session")))
        save_cb.setToolTip(
            "If checked, your session token is written to stream_picker_config.json "
            "on your local machine. It is never sent anywhere else."
        )

        def _login():
            nonlocal has_session
            if has_session:
                # Disconnect
                self._sessions.pop(platform_key, None)
                self._cfg.pop(f"{platform_key}_session", None)
                has_session = False
                login_btn.setText("Login")
                login_btn.setStyleSheet(_BTN)
                status_lbl.setText("Not connected")
                status_lbl.setStyleSheet(f"color:{C_GOLD_DIM}; font-size:10px;")
                save_cb.setChecked(False)
                return

            dlg = get_login_dialog(platform_key, self)
            if dlg.exec() and dlg.get_token():
                token = dlg.get_token()
                self._sessions[platform_key] = token
                has_session = True
                login_btn.setText("Disconnect")
                login_btn.setStyleSheet(_BTN_RED)
                status_lbl.setText(f"Connected ✓")
                status_lbl.setStyleSheet(f"color:{C_GREEN}; font-size:10px;")

        login_btn.clicked.connect(_login)

        row.addWidget(login_btn)
        row.addWidget(status_lbl)
        row.addStretch()
        row.addWidget(save_cb)
        lay.addLayout(row)

        # Store save_cb reference by platform key so _save() can read it
        setattr(self, f"_{platform_key}_save_cb", save_cb)

    # ── tabs ──────────────────────────────────────────────────────────────────

    def _steam_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        lay.addWidget(self._lbl("Steam API Key"))
        lbl_k, self._steam_key, tog_k = _masked_row("")
        self._steam_key.setText(self._cfg.get("steam_api_key", ""))
        self._steam_key.setPlaceholderText("Get one at steamcommunity.com/dev/apikey")
        hint_k = QLabel("Stored locally. Never written to log files.")
        hint_k.setStyleSheet(_LH)
        row_k = QHBoxLayout()
        row_k.addWidget(self._steam_key)
        row_k.addWidget(tog_k)
        lay.addLayout(row_k)
        lay.addWidget(hint_k)

        lay.addStretch()
        return w

    def _twitch_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        lay.addWidget(self._lbl("Client ID"))
        self._twitch_id = QLineEdit(self._cfg.get("twitch_client_id", ""))
        self._twitch_id.setStyleSheet(_ENTRY)
        self._twitch_id.setPlaceholderText("From dev.twitch.tv/console")
        lay.addWidget(self._twitch_id)

        lay.addWidget(_sep())

        lay.addWidget(self._lbl("Client Secret"))
        lbl_s, self._twitch_secret, tog_s = _masked_row("")
        self._twitch_secret.setText(self._cfg.get("twitch_client_secret", ""))
        self._twitch_secret.setPlaceholderText("From dev.twitch.tv/console")
        hint_s = QLabel("Stored locally. Never written to log files.")
        hint_s.setStyleSheet(_LH)
        row_s = QHBoxLayout()
        row_s.addWidget(self._twitch_secret)
        row_s.addWidget(tog_s)
        lay.addLayout(row_s)
        lay.addWidget(hint_s)

        lay.addStretch()
        return w

    def _platforms_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # ── Epic ──────────────────────────────────────────────────────────────
        # No login button: the OAuth code Epic issues grants full account
        # access (purchases, wallet, friends, cloud saves) and Epic's own API
        # response says not to share it with any 3rd-party app — which this
        # would be. Epic relies on local manifest detection + manual list only.
        self._epic_check = self._check("Epic Games Store", "epic_enabled")
        lay.addWidget(self._epic_check)
        epic_hint = QLabel(
            "Auto-reads manifests from %ProgramData%\\Epic\\...\\Manifests\\. "
            "Paste a manual library list below as fallback (one game per line).")
        epic_hint.setStyleSheet(_LH)
        epic_hint.setWordWrap(True)
        self._epic_manual = QTextEdit(self._cfg.get("epic_manual", ""))
        self._epic_manual.setStyleSheet(_TE)
        self._epic_manual.setFixedHeight(55)
        lay.addWidget(epic_hint)
        lay.addWidget(self._epic_manual)
        lay.addWidget(_sep())

        # ── GOG ───────────────────────────────────────────────────────────────
        self._gog_check = self._check("GOG Galaxy", "gog_enabled")
        lay.addWidget(self._gog_check)
        gog_hint = QLabel(
            "Auto-reads galaxy-2.0.db if found. Or paste your GOG profile URL / username below.")
        gog_hint.setStyleSheet(_LH)
        gog_hint.setWordWrap(True)
        self._gog_profile = QLineEdit(self._cfg.get("gog_profile", ""))
        self._gog_profile.setStyleSheet(_ENTRY)
        self._gog_profile.setPlaceholderText("https://www.gog.com/u/username  or  username")
        lay.addWidget(gog_hint)
        lay.addWidget(self._gog_profile)
        lay.addWidget(_sep())

        # ── Ubisoft ───────────────────────────────────────────────────────────
        # No login button: Ubisoft has no cookie-based library API, and its
        # own login API only accepts a Basic-auth ticket, which 2FA blocks.
        # Manual entry only.
        self._ubi_check = self._check("Ubisoft Connect", "ubisoft_enabled")
        lay.addWidget(self._ubi_check)
        ubi_hint = QLabel(
            "No auto-detection available. Paste game names below (one per line).")
        ubi_hint.setStyleSheet(_LH)
        ubi_hint.setWordWrap(True)
        self._ubi_games = QTextEdit(self._cfg.get("ubisoft_games", ""))
        self._ubi_games.setStyleSheet(_TE)
        self._ubi_games.setFixedHeight(55)
        lay.addWidget(ubi_hint)
        lay.addWidget(self._ubi_games)
        lay.addWidget(_sep())

        # ── EA ────────────────────────────────────────────────────────────────
        # No login button: EA retired the old Origin cookie-auth API when it
        # moved everyone to the EA app. Registry auto-detect + manual entry only.
        self._ea_check = self._check("EA App / Origin", "ea_enabled")
        lay.addWidget(self._ea_check)
        ea_hint = QLabel(
            "Auto-reads installed games from the registry (Windows only). "
            "Paste a manual list below as fallback (one per line).")
        ea_hint.setStyleSheet(_LH)
        ea_hint.setWordWrap(True)
        self._ea_games = QTextEdit(self._cfg.get("ea_games", ""))
        self._ea_games.setStyleSheet(_TE)
        self._ea_games.setFixedHeight(55)
        lay.addWidget(ea_hint)
        lay.addWidget(self._ea_games)
        lay.addWidget(_sep())

        # ── Xbox ──────────────────────────────────────────────────────────────
        # No login button: getting a usable session means asking you to paste
        # a login.live.com redirect URL back into this app — Microsoft shows
        # an explicit anti-phishing warning on that exact page for a reason.
        self._xbox_check = self._check("Xbox / PC Game Pass", "xbox_enabled")
        lay.addWidget(self._xbox_check)
        xbox_hint = QLabel(
            "Auto-reads via PowerShell (Windows only). "
            "Paste a manual list below as fallback (one per line).")
        xbox_hint.setStyleSheet(_LH)
        xbox_hint.setWordWrap(True)
        self._xbox_manual = QTextEdit(self._cfg.get("xbox_manual", ""))
        self._xbox_manual.setStyleSheet(_TE)
        self._xbox_manual.setFixedHeight(55)
        lay.addWidget(xbox_hint)
        lay.addWidget(self._xbox_manual)

        lay.addStretch()
        return w

    # ── helpers ───────────────────────────────────────────────────────────────

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(_L)
        return l

    def _check(self, text: str, key: str) -> QCheckBox:
        cb = QCheckBox(text)
        cb.setStyleSheet(_CHECK)
        cb.setChecked(bool(self._cfg.get(key, False)))
        return cb

    # ── save ──────────────────────────────────────────────────────────────────

    def _save(self):
        self._cfg["steam_api_key"]       = self._steam_key.text().strip()
        self._cfg["twitch_client_id"]    = self._twitch_id.text().strip()
        self._cfg["twitch_client_secret"] = self._twitch_secret.text().strip()
        self._cfg["epic_enabled"]    = self._epic_check.isChecked()
        self._cfg["epic_manual"]     = self._epic_manual.toPlainText()
        self._cfg["gog_enabled"]     = self._gog_check.isChecked()
        self._cfg["gog_profile"]     = self._gog_profile.text().strip()
        self._cfg["ubisoft_enabled"] = self._ubi_check.isChecked()
        self._cfg["ubisoft_games"]   = self._ubi_games.toPlainText()
        self._cfg["ea_enabled"]      = self._ea_check.isChecked()
        self._cfg["ea_games"]        = self._ea_games.toPlainText()
        self._cfg.pop("ea_session", None)  # stale key from the old login flow
        self._cfg["xbox_enabled"]    = self._xbox_check.isChecked()
        self._cfg["xbox_manual"]     = self._xbox_manual.toPlainText()

        # Write sessions to config only if user opted in
        for key in ("epic", "xbox"):
            save_cb = getattr(self, f"_{key}_save_cb", None)
            if save_cb and save_cb.isChecked() and self._sessions.get(key):
                self._cfg[f"{key}_session"] = self._sessions[key]
            else:
                # Remove from config if unchecked (don't persist)
                self._cfg.pop(f"{key}_session", None)

        self.accept()

    def get_config(self) -> dict:
        return self._cfg

    def get_sessions(self) -> dict:
        return self._sessions

# Version 0.0.2
