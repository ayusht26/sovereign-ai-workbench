"""
widgets/status_bar.py — Footer status bar.
"""
from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Widget):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: #111318;
        border-top: solid #1e2128;
        layout: horizontal;
    }
    StatusBar #sb-left {
        width: 1fr;
        content-align: left middle;
        color: #445566;
        padding: 0 2;
    }
    StatusBar #sb-right {
        width: auto;
        content-align: right middle;
        color: #2e3a4a;
        padding: 0 2;
    }
    """

    _mode:    str = "AUTO"
    _model:   str = "AUTO"
    _elapsed: str = ""

    def compose(self) -> ComposeResult:
        yield Static("", id="sb-left")
        yield Static("tab agents   ctrl+p commands   esc interrupt   ctrl+n new", id="sb-right")

    def _refresh(self) -> None:
        try:
            parts = [self._mode, self._model]
            if self._elapsed:
                parts.append(self._elapsed)
            self.query_one("#sb-left", Static).update("  ·  ".join(parts))
        except Exception:
            pass

    def set_model(self, mode: str, model: str) -> None:
        self._mode = mode
        self._model = model
        self._refresh()

    def set_elapsed(self, seconds: float) -> None:
        if seconds < 60:
            self._elapsed = f"{seconds:.1f}s"
        else:
            self._elapsed = f"{int(seconds // 60)}m {int(seconds % 60)}s"
        self._refresh()
