"""
screens/net_monitor_screen.py — Live network connections display (/net).

Shows all active connections, external attempt count, and last-checked time.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class NetMonitorScreen(Screen):
    """Full-screen network monitor. Press q or esc to go back."""

    BINDINGS = [
        ("escape,q", "app.pop_screen", "Back"),
    ]

    DEFAULT_CSS = """
    NetMonitorScreen {
        background: #0d0f12;
    }
    NetMonitorScreen #banner {
        color: #5FA8D3;
        text-style: bold;
        text-align: center;
        height: 3;
        padding: 1;
    }
    NetMonitorScreen #summary {
        color: #cdd6f4;
        padding: 0 2;
        height: 3;
    }
    NetMonitorScreen #summary.alert {
        color: #cc4444;
        text-style: bold;
    }
    NetMonitorScreen DataTable {
        margin: 0 2;
    }
    NetMonitorScreen #last-checked {
        color: #445566;
        text-style: italic;
        padding: 0 2;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("── Network Monitor ──", id="banner")
        yield Static("", id="summary")
        yield DataTable(id="conn-table")
        yield Static("", id="last-checked")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#conn-table", DataTable)
        table.add_columns("Scope", "Process", "Local", "Remote", "State")
        self._update()
        self.set_interval(0.5, self._update)

    def _update(self) -> None:
        from sovereignai.net_guard.monitor import get_monitor
        import datetime

        monitor = get_monitor()
        state = monitor.get_state()

        # Summary
        summary = self.query_one("#summary", Static)
        if state.alert or state.external_attempts > 0:
            summary.set_classes("alert")
            summary.update(
                f"⚠  ALERT: {state.external_attempts} external connection attempt(s) by SovereignAI detected!"
            )
        else:
            summary.set_classes("")
            summary.update(
                f"🔒  SovereignAI Egress: 0 external calls (100% Local)\n"
                f"    OS Background: {state.system_external_count} active sockets from other apps (Chrome/system/etc.)"
            )

        # Table
        table = self.query_one("#conn-table", DataTable)
        table.clear()
        for conn in state.connections[:60]:
            scope_badge = "● SovAI" if conn.is_sovai else "  System"
            proc_display = f"{conn.process_name} ({conn.pid})" if conn.pid else (conn.process_name or "?")
            table.add_row(
                scope_badge,
                proc_display,
                conn.laddr,
                conn.raddr,
                conn.status,
            )

        # Last checked
        ts = datetime.datetime.fromtimestamp(state.last_checked).strftime("%H:%M:%S")
        self.query_one("#last-checked", Static).update(f"  Last checked: {ts}")

