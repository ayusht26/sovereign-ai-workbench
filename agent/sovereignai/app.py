"""
app.py — The Textual App root.
"""
from __future__ import annotations

import os
from pathlib import Path

from textual.app import App


class SovereignApp(App):
    TITLE = "SovereignAI"
    SUB_TITLE = "Local models. Local data. Zero external calls."

    # Disable the built-in command palette so our ctrl+p binding works
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Screen {
        background: #0d0f12;
    }
    """

    def __init__(
        self,
        workspace: Path | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self._workspace = workspace or Path.cwd()

        os.environ["SOVAI_WORKSPACE"] = str(self._workspace)

        # Check for cached authenticated user session
        from sovereignai.auth import get_current_user
        self.current_user = get_current_user()
        if self.current_user:
            self.user_role = self.current_user.get("role", "admin")
        else:
            self.user_role = os.getenv("SOVAI_ROLE", "admin")

        os.environ["SOVAI_ROLE"] = self.user_role
        self._session = self._new_session()

    def _new_session(self):
        from sovereignai.orchestrator.session import Session

        session = Session(
            workspace=str(self._workspace)
        )

        session.user_role = self.user_role
        if self.current_user:
            session.user_id = self.current_user.get("id")
            session.username = self.current_user.get("username")
            session.user_name = self.current_user.get("full_name")
            session.company_id = self.current_user.get("company_id")
            session.company_name = self.current_user.get("company_name")

        return session

    def on_mount(self) -> None:
        from sovereignai.ui.screens.login_screen import LoginScreen
        from sovereignai.ui.screens.main_screen import MainScreen

        if self.current_user:
            self.push_screen(
                MainScreen(
                    session=self._session,
                    workspace=self._workspace,
                )
            )
        else:
            self.push_screen(LoginScreen())

    def on_login_completed(self, user_info: dict) -> None:
        from sovereignai.ui.screens.main_screen import MainScreen

        self.current_user = user_info
        self.user_role = user_info.get("role", "admin")
        os.environ["SOVAI_ROLE"] = self.user_role
        self._session = self._new_session()

        self.switch_screen(
            MainScreen(
                session=self._session,
                workspace=self._workspace,
            )
        )
        self.notify(
            f"Signed in as {user_info.get('full_name')} ({self.user_role.upper()})",
            timeout=3,
        )

    async def action_logout(self) -> None:
        from sovereignai.auth import logout
        from sovereignai.ui.screens.login_screen import LoginScreen

        logout()
        self.current_user = None

        self.switch_screen(LoginScreen())
        self.notify("Signed out from Bastion.", timeout=2)


    async def action_new_session(self) -> None:
        from sovereignai.ui.screens.main_screen import MainScreen

        self._session = self._new_session()

        while len(self.screen_stack) > 1:
            self.pop_screen()

        self.push_screen(
            MainScreen(
                session=self._session,
                workspace=self._workspace,
            )
        )

        self.notify(
            "New session started.",
            timeout=2,
        )