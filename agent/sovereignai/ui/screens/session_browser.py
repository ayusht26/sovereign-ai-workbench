"""
screens/session_browser.py — Browse and reopen past sessions (/sessions).
"""
from __future__ import annotations

import datetime

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class SessionBrowser(Screen):
    """Browse past sessions from the audit log. Press enter to reopen."""

    BINDINGS = [
        ("escape,q", "app.pop_screen", "Back"),
        ("enter",    "open_session",   "Open"),
    ]

    DEFAULT_CSS = """
    SessionBrowser {
        background: #0d0f12;
    }
    SessionBrowser #title {
        color: #5FA8D3;
        text-style: bold;
        text-align: center;
        height: 2;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("── Past Sessions ──", id="title")
        yield DataTable(id="session-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#session-table", DataTable)
        table.add_columns("Session ID", "Started", "Last Active", "Turns")
        self._load()

    def _load(self) -> None:
        from sovereignai.orchestrator.audit_log import get_audit
        table = self.query_one("#session-table", DataTable)
        table.clear()

        try:
            sessions = get_audit().list_sessions()
            for s in sessions:
                started = datetime.datetime.fromtimestamp(s["started_at"]).strftime("%Y-%m-%d %H:%M")
                last = datetime.datetime.fromtimestamp(s["last_at"]).strftime("%Y-%m-%d %H:%M")
                table.add_row(
                    s["session_id"][:16] + "…",
                    started,
                    last,
                    str(s["turns"]),
                    key=s["session_id"],
                )
        except Exception as e:
            table.add_row(f"Error: {e}", "", "", "")

    def action_open_session(self) -> None:
        # In a future iteration, this would restore the session state
        self.app.notify("Session restore coming in a future update.", severity="information")
        self.app.pop_screen()

