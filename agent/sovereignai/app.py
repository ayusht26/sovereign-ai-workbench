"""
app.py — The Textual App root.
"""
from __future__ import annotations

import os
from pathlib import Path

from textual.app import App, ComposeResult


class SovereignApp(App):
    TITLE = "SovereignAI"
    SUB_TITLE = "Local models. Local data. Zero external calls."
    # Disable the built-in command palette so our ctrl+p binding works
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Screen { background: #0d0f12; }
    """

    def __init__(self, workspace: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._workspace = workspace or Path.cwd()
        os.environ["SOVAI_WORKSPACE"] = str(self._workspace)
        self._session = self._new_session()

    def _new_session(self):
        from sovereignai.orchestrator.session import Session
        return Session(workspace=str(self._workspace))

    def on_mount(self) -> None:
        from sovereignai.ui.screens.main_screen import MainScreen
        self.push_screen(MainScreen(session=self._session, workspace=self._workspace))

    async def action_new_session(self) -> None:
        from sovereignai.ui.screens.main_screen import MainScreen
        self._session = self._new_session()
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(MainScreen(session=self._session, workspace=self._workspace))
        self.notify("New session started.", timeout=2)
