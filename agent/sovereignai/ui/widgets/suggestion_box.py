"""
widgets/suggestion_box.py — OpenCode-style autocomplete / suggestions box.

Renders directly above the input box when the user types '/'.
Matches the OpenCode signature peach/salmon highlight for active selection.
"""
from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual import events
from textual.message import Message
from textual.widget import Widget


@dataclass(frozen=True)
class CommandItem:
    cmd: str
    desc: str
    takes_args: bool = False
    alias_of: str | None = None


# Command registry matching OpenCode / Claude Code / Bastion sovereign agent
COMMANDS: list[CommandItem] = [
    CommandItem("/agents", "Switch agent role (admin | tech | finance | support)", takes_args=True),
    CommandItem("/models", "Switch model", takes_args=False),
    CommandItem("/auto", "Switch to AUTO router", takes_args=False),
    CommandItem("/diff", "Open diff viewer (git diff)", takes_args=False),
    CommandItem("/editor", "Open editor ($EDITOR / code)", takes_args=False),
    CommandItem("/exit", "Exit the app", takes_args=False),
    CommandItem("/quit", "Exit the app", takes_args=False, alias_of="/exit"),
    CommandItem("/help", "Help", takes_args=False),
    CommandItem("/init", "guided AGENTS.md setup", takes_args=False),
    CommandItem("/kb", "Knowledge base (status | add <path>)", takes_args=True),
    CommandItem("/move", "Move to another project dir (/cwd <path>)", takes_args=True, alias_of="/cwd"),
    CommandItem("/cwd", "Change workspace directory (/cwd <path>)", takes_args=True),
    CommandItem("/attach", "Attach file to workspace (/attach <path>)", takes_args=True),
    CommandItem("/net", "Toggle network monitor", takes_args=False),
    CommandItem("/new", "Start new session", takes_args=False),
    CommandItem("/sessions", "Browse past sessions", takes_args=False),
    CommandItem("/logout", "Sign out and return to login screen", takes_args=False),
]




class SuggestionBox(Widget):
    """
    Floating suggestion box situated directly above the chat input box.
    OpenCode styling: dark container (#111318), peach/salmon highlight (#FF9D76)
    with black bold text for the currently selected command.
    """

    DEFAULT_CSS = """
    SuggestionBox {
        display: none;
        height: auto;
        max-height: 11;
        background: #111318;
        border: solid #2e3440;
        margin-bottom: 0;
        padding: 0;
    }
    SuggestionBox.visible {
        display: block;
    }
    """

    class Selected(Message):
        """Emitted when a suggestion is selected."""
        def __init__(self, item: CommandItem, auto_run: bool = False) -> None:
            super().__init__()
            self.item = item
            self.auto_run = auto_run

    class Dismissed(Message):
        """Emitted when suggestions are dismissed."""
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._filtered: list[CommandItem] = []
        self.selected_index: int = 0
        self._is_active: bool = False

    @property
    def is_active(self) -> bool:
        return self._is_active

    def update_query(self, text: str) -> bool:
        """
        Update visible suggestions based on user input text.
        Returns True if suggestions are visible, False otherwise.
        """
        if not text.startswith("/"):
            self.hide()
            return False

        # If user has already typed a complete command followed by a space,
        # we check for sub-commands (e.g. /kb status, /kb add) or close.
        parts = text.split(maxsplit=1)
        head = parts[0].lower()

        if head == "/kb" and len(parts) > 1:
            sub = parts[1].lower()
            sub_commands = [
                CommandItem("/kb status", "Show knowledge base stats", False),
                CommandItem("/kb add", "Add a file/directory to KB (/kb add <path>)", True),
            ]
            self._filtered = [
                c for c in sub_commands
                if not sub or c.cmd.lower().startswith(f"/kb {sub}") or sub in c.desc.lower()
            ]
        else:
            q = head
            # Primary matches: command begins with typed query (e.g. /m -> /models, /move)
            primary = [c for c in COMMANDS if c.cmd.lower().startswith(q)]
            if primary:
                self._filtered = primary
            else:
                # Fallback: query in command or description
                needle = q[1:] if q.startswith("/") else q
                self._filtered = [
                    c for c in COMMANDS
                    if needle in c.cmd.lower() or needle in c.desc.lower()
                ]

        if not self._filtered:
            self.hide()
            return False

        # Keep or clamp selected index
        self.selected_index = max(0, min(self.selected_index, len(self._filtered) - 1))
        self._is_active = True
        self.add_class("visible")
        self.styles.height = len(self._filtered)
        self.refresh()
        return True

    def select_next(self) -> None:
        """Move active selection to the next item."""
        if not self._filtered:
            return
        self.selected_index = (self.selected_index + 1) % len(self._filtered)
        self.refresh()

    def select_prev(self) -> None:
        """Move active selection to the previous item."""
        if not self._filtered:
            return
        self.selected_index = (self.selected_index - 1) % len(self._filtered)
        self.refresh()

    def get_selected(self) -> CommandItem | None:
        """Return currently selected item."""
        if 0 <= self.selected_index < len(self._filtered):
            return self._filtered[self.selected_index]
        return None

    def hide(self) -> None:
        """Hide the suggestion box."""
        self._is_active = False
        self._filtered = []
        self.selected_index = 0
        self.remove_class("visible")
        self.refresh()

    def on_click(self, event: events.Click) -> None:
        """Handle mouse click on a suggestion row."""
        if 0 <= event.y < len(self._filtered):
            self.selected_index = event.y
            item = self._filtered[event.y]
            # Auto-run if command doesn't require extra arguments
            self.post_message(self.Selected(item, auto_run=not item.takes_args))

    def render(self) -> Text:
        """Render suggestions with OpenCode peach/salmon active highlight."""
        if not self._filtered:
            return Text()

        total_width = max(self.size.width, 60)
        cmd_col_width = 14

        text = Text()
        for idx, item in enumerate(self._filtered):
            is_selected = (idx == self.selected_index)
            cmd_display = item.cmd
            desc_display = item.desc

            if is_selected:
                # OpenCode signature styling: Peach/salmon background with black bold text
                raw_line = f"  {cmd_display:<{cmd_col_width}} {desc_display} "
                padded = raw_line.ljust(total_width)
                if idx < len(self._filtered) - 1:
                    padded += "\n"
                text.append(padded, style="bold #0d0f12 on #FF9D76")
            else:
                # Inactive item: bold white command, muted gray description
                cmd_part = f"  {cmd_display:<{cmd_col_width}} "
                desc_part = desc_display.ljust(total_width - len(cmd_part))
                if idx < len(self._filtered) - 1:
                    desc_part += "\n"
                text.append(cmd_part, style="bold #cdd6f4")
                text.append(desc_part, style="#7a889b")

        return text
