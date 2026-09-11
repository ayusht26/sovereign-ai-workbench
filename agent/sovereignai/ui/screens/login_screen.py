"""
login_screen.py — Authentication screen for Bastion Agent TUI.

Authenticates against Supabase via username or email + password,
persisting the session and transitioning directly to MainScreen.
"""
from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from sovereignai.auth import login

_LOGIN_BANNER = r"""[bold #5FA8D3]██████╗  █████╗ ███████╗████████╗██╗ ██████╗  ███╗   ██╗[/]
[bold #4a90b8]██╔══██╗██╔══██╗██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║[/]
[bold #3d7da0]██████╔╝███████║███████╗   ██║   ██║██║   ██║██╔██╗ ██║[/]
[bold #306988]██╔══██╗██╔══██║╚════██║   ██║   ██║██║   ██║██║╚██╗██║[/]
[bold #2E5A7A]██████╔╝██║  ██║███████║   ██║   ██║╚██████╔╝██║ ╚████║[/]
[bold #2E5A7A]╚═════╝ ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝[/]"""


class LoginScreen(Screen):
    """Sign-in screen displayed when no authenticated session is active."""

    BINDINGS = [
        ("escape", "exit_app", "Exit"),
    ]

    DEFAULT_CSS = """
    LoginScreen {
        background: #0d0f12;
        align: center middle;
    }

    #login-container {
        width: 76;
        height: auto;
        max-height: 95%;
        background: #111318;
        border: solid #2e3440;
        border-top: thick #5FA8D3;
        padding: 1 3;
    }

    #login-banner {
        text-align: center;
        margin-bottom: 0;
    }

    #login-subtitle {
        text-align: center;
        color: #5FA8D3;
        text-style: bold;
        margin-top: 0;
        margin-bottom: 0;
    }

    #login-caption {
        text-align: center;
        color: #667788;
        margin-bottom: 1;
    }


    .field-label {
        color: #99aabb;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }

    .login-input {
        background: #0d0f12;
        border: solid #2e3440;
        color: #cdd6f4;
        width: 100%;
        margin-bottom: 0;
    }

    .login-input:focus {
        border: solid #5FA8D3;
    }

    #error-label {
        color: #ff5555;
        text-style: bold;
        margin-top: 1;
        min-height: 1;
        text-align: center;
    }

    #btn-submit {
        background: #5FA8D3;
        color: #0d0f12;
        text-style: bold;
        width: 100%;
        margin-top: 1;
        border: none;
    }

    #btn-submit:hover {
        background: #7bbde0;
    }

    #quick-title {
        color: #D9A441;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
        text-align: center;
    }

    #quick-grid {
        layout: horizontal;
        height: auto;
        margin-top: 0;
        margin-bottom: 1;
    }

    .quick-btn {
        width: 1fr;
        height: auto;
        margin: 0 1;
        background: #181b22;
        border: solid #2e3440;
        color: #8899aa;
        text-style: none;
        padding: 0 1;
        min-width: 14;
    }

    .quick-btn:hover {
        background: #232732;
        color: #cdd6f4;
        border: solid #5FA8D3;
    }

    #status-pill {
        color: #44bb88;
        text-align: center;
        margin-top: 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Center():
            with VerticalScroll(id="login-container"):
                yield Static(_LOGIN_BANNER, id="login-banner")
                yield Static("IDENTITY & ACCESS MANAGEMENT · SOVEREIGN WORKBENCH", id="login-subtitle")
                yield Static("Multi-tenant company boundary · Postgres Row Level Security (RLS)", id="login-caption")

                yield Static("Username or Email", classes="field-label")
                yield Input(
                    placeholder="e.g. admin, tech_lead, or employee@tatamotors-internal.com",
                    id="input-identifier",
                    classes="login-input",
                )

                yield Static("Password", classes="field-label")
                yield Input(
                    placeholder="Enter account password",
                    password=True,
                    id="input-password",
                    classes="login-input",
                )

                yield Static("", id="error-label")
                yield Button("Sign In to Sovereign Workspace", id="btn-submit", variant="primary")

                yield Static("Quick-Fill Test Accounts:", id="quick-title")
                with Horizontal(id="quick-grid"):
                    yield Button("IOCL Admin\nadmin", id="quick-admin", classes="quick-btn")
                    yield Button("Tech Lead\ntech_lead", id="quick-tech", classes="quick-btn")
                    yield Button("Finance Lead\nfinance_lead", id="quick-finance", classes="quick-btn")
                    yield Button("Support Lead\nsupport_lead", id="quick-support", classes="quick-btn")

                yield Static("● Postgres RLS: Active & Enforced · Zero Token Egress", id="status-pill")

    def on_mount(self) -> None:
        self.query_one("#input-identifier", Input).focus()

    def action_exit_app(self) -> None:
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-submit":
            self._do_login()
        elif btn_id == "quick-admin":
            self._fill_and_login("admin", "admin123")
        elif btn_id == "quick-tech":
            self._fill_and_login("tech_lead", "tech123")
        elif btn_id == "quick-finance":
            self._fill_and_login("finance_lead", "finance123")
        elif btn_id == "quick-support":
            self._fill_and_login("support_lead", "support123")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-identifier":
            self.query_one("#input-password", Input).focus()
        elif event.input.id == "input-password":
            self._do_login()

    def _fill_and_login(self, identifier: str, passw: str) -> None:
        self.query_one("#input-identifier", Input).value = identifier
        self.query_one("#input-password", Input).value = passw
        self._do_login()

    def _do_login(self) -> None:
        ident = self.query_one("#input-identifier", Input).value.strip()
        passw = self.query_one("#input-password", Input).value
        err_lbl = self.query_one("#error-label", Static)

        if not ident or not passw:
            err_lbl.update("[#ff5555]Please enter your username/email and password.[/#ff5555]")
            return

        err_lbl.update("[#D9A441]Authenticating with Supabase RLS boundary…[/#D9A441]")
        self.run_worker(self._async_login(ident, passw))

    async def _async_login(self, ident: str, passw: str) -> None:
        err_lbl = self.query_one("#error-label", Static)
        try:
            user_info = login(ident, passw)
            err_lbl.update(f"[#44bb88]Authentication successful: Welcome {user_info.get('full_name')}![/#44bb88]")
            # Delegate transition to app
            self.app.call_after_refresh(self._on_login_success, user_info)
        except Exception as e:
            err_msg = str(e)
            if "Invalid username/email or password" in err_msg or "Invalid login credentials" in err_msg:
                err_lbl.update("[#ff5555]Invalid credentials. Check username or password.[/#ff5555]")
            else:
                err_lbl.update(f"[#ff5555]{err_msg[:65]}[/#ff5555]")

    def _on_login_success(self, user_info: dict) -> None:
        if hasattr(self.app, "on_login_completed"):
            self.app.on_login_completed(user_info)
