"""
widgets/thought_block.py — Collapsible thought/reasoning block.

Shown above each assistant response: "+ Thought: 409ms" (expandable).
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Collapsible, Static


class ThoughtBlock(Widget):
    """
    Collapsible block showing the model's reasoning text.
    Starts collapsed after completion; auto-expands while streaming.
    """

    DEFAULT_CSS = """
    ThoughtBlock {
        margin: 0 0 0 2;
        padding: 0;
    }
    ThoughtBlock Collapsible {
        border: none;
        padding: 0;
    }
    ThoughtBlock .thought-text {
        color: #667788;
        text-style: italic;
        padding: 0 2;
        margin: 0;
    }
    ThoughtBlock .thought-title {
        color: #445566;
    }
    """

    def __init__(self, duration_ms: int = 0, text: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._duration_ms = duration_ms
        self._text = text

    def compose(self) -> ComposeResult:
        title = f"+ Thought: {self._duration_ms}ms" if self._duration_ms else "+ Thought"
        with Collapsible(title=title, collapsed=True):
            yield Static(self._text or "(no reasoning text)", classes="thought-text")

    def append_text(self, chunk: str) -> None:
        self._text += chunk
        try:
            static = self.query_one(".thought-text", Static)
            static.update(self._text)
        except Exception:
            pass

