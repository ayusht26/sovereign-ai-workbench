"""
command_palette.py — ctrl+p command palette.
Fixed: ListView is populated in on_mount (after it's attached), not in compose.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Label, Static
from textual.containers import Vertical

_COMMANDS = [
    ("/models",         "Switch or select the active model"),
    ("/auto",           "Switch back to AUTO model selection"),
    ("/new",            "Start a new session"),
    ("/sessions",       "Browse past sessions"),
    ("/kb add",         "Add a path to the knowledge base"),
    ("/kb status",      "Show knowledge base statistics"),
    ("/kb watch",       "Watch a directory for changes"),
    ("/net",            "Open the network monitor"),
    ("/cwd",            "Change the workspace directory"),
    ("/sandbox status", "Check Docker sandbox status"),
    ("/help",           "Show help"),
]


class CommandPalette(ModalScreen):
    """Fuzzy-searchable command palette (ctrl+p)."""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
        ("enter",  "select",        "Execute"),
    ]

    DEFAULT_CSS = """
    CommandPalette {
        align: center middle;
        background: rgba(0,0,0,0.7);
    }
    CommandPalette > Vertical {
        width: 68;
        height: auto;
        max-height: 26;
        background: #1a1d22;
        border: solid #5FA8D3;
        padding: 1 2;
    }
    CommandPalette Input {
        background: #0d0f12;
        border: solid #2e3440;
        color: #cdd6f4;
        width: 100%;
        margin-bottom: 1;
    }
    CommandPalette ListView {
        background: transparent;
        border: none;
        height: auto;
        max-height: 16;
    }
    CommandPalette ListItem {
        color: #cdd6f4;
        padding: 0 1;
        height: 1;
        background: transparent;
    }
    CommandPalette ListItem.--highlight {
        background: #2e3a4a;
        color: #5FA8D3;
    }
    CommandPalette #hint {
        color: #445566;
        text-style: italic;
        height: 1;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(placeholder="Type a command…", id="search")
            yield ListView(id="cmd-list")
            yield Static("  ↑↓ navigate   enter execute   esc cancel", id="hint")

    def on_mount(self) -> None:
        self._populate("")
        self.query_one("#search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._populate(event.value)

    def _populate(self, query: str) -> None:
        lv = self.query_one("#cmd-list", ListView)
        lv.clear()
        q = query.lower().strip()

        items = []
        for cmd, desc in _COMMANDS:
            if not q or q in cmd.lower() or q in desc.lower():
                safe_id = "cmd" + cmd.replace("/", "_").replace(" ", "_")
                items.append(ListItem(
                    Label(f"  {cmd:<22}  {desc}"),
                    id=safe_id,
                ))
        # Extend accepts a list of items (doesn't need await in event handlers)
        for item in items:
            lv.mount(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        # Reverse-map id → command
        for cmd, _ in _COMMANDS:
            safe_id = "cmd" + cmd.replace("/", "_").replace(" ", "_")
            if item_id == safe_id:
                self.dismiss(cmd)
                return
        self.dismiss(None)

    def action_select(self) -> None:
        lv = self.query_one("#cmd-list", ListView)
        if lv.highlighted_child:
            self.on_list_view_selected(ListView.Selected(lv, lv.highlighted_child))
        else:
            self.dismiss(None)
