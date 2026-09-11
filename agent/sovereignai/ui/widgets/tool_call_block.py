"""
widgets/tool_call_block.py — Tool call bordered block widget.

Shows tool name, arguments, and result — collapsible after completion,
auto-expanded with a spinner while running.
Produces a file card when a file_path is returned.
"""
from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Collapsible, Label, Static, LoadingIndicator


_TOOL_ICONS = {
    "fs_read":         "📄",
    "fs_write":        "✏️ ",
    "fs_list":         "📁",
    "fs_glob":         "🔍",
    "sandbox_exec":    "🐳",
    "shell_tool":      "💻",
    "sheet_read":      "📊",
    "sheet_write":     "📊",
    "sheet_create":    "📊",
    "generate_docx":   "📝",
    "generate_pptx":   "📽️ ",
    "generate_xlsx":   "📊",
    "vision_analyze":  "👁️ ",
    "rag_search":      "🗂️ ",
}


class ToolCallBlock(Widget):
    """
    Displays a single tool call: header + args + result + optional file card.
    """

    DEFAULT_CSS = """
    ToolCallBlock {
        margin: 0 0 1 0;
        padding: 0;
        height: auto;
    }
    ToolCallBlock Collapsible {
        padding: 0 1;
        margin: 0;
        background: transparent;
        border-top: none;
    }
    ToolCallBlock .tool-header {
        color: #5FA8D3;
        text-style: bold;
        padding: 0 1;
    }
    ToolCallBlock .tool-args {
        color: #667788;
        padding: 0 2;
        margin: 0;
    }
    ToolCallBlock .tool-result {
        color: #aabbcc;
        padding: 0 2;
        margin: 0;
    }
    ToolCallBlock .tool-error {
        color: #cc4444;
        padding: 0 2;
    }
    ToolCallBlock .file-card {
        background: #1e3040;
        border: solid #5FA8D3;
        color: #5FA8D3;
        padding: 0 2;
        margin: 1 0;
        text-style: bold;
    }
    ToolCallBlock .running-label {
        color: #D9A441;
        text-style: italic;
        padding: 0 2;
    }
    """

    def __init__(self, tool_name: str, args: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tool_name = tool_name
        self._args = args
        self._result: dict | None = None
        self._running = True

    def compose(self) -> ComposeResult:
        icon = _TOOL_ICONS.get(self._tool_name, "🔧")
        args_str = json.dumps(self._args, indent=2) if self._args else "{}"
        # Keep args short
        if len(args_str) > 300:
            args_str = args_str[:300] + "\n  …"

        with Collapsible(title=f"{icon} Tool: {self._tool_name}", collapsed=False):
            yield Static(f"Arguments:\n{args_str}", classes="tool-args")
            yield Static("⏳ Running…", classes="running-label", id="result-area")

    def set_result(self, result: dict) -> None:
        """Called when the tool finishes. Updates the result area and collapses."""
        self._result = result
        self._running = False

        try:
            collapsible = self.query_one(Collapsible)
            result_area = self.query_one("#result-area", Static)
        except Exception:
            return

        icon = _TOOL_ICONS.get(self._tool_name, "🔧")

        if result.get("success"):
            data = result.get("data", {})
            file_path = result.get("file_path")

            result_summary = "✓ Success"
            result_text = "✅ Success"
            if isinstance(data, dict):
                count = data.get("count")
                if count is not None:
                    result_summary = f"✓ Success: {count} result{'s' if count != 1 else ''}"
                elif data.get("results") and isinstance(data["results"], list):
                    c = len(data["results"])
                    result_summary = f"✓ Success: {c} result{'s' if c != 1 else ''}"

                show_keys = ["message", "stdout", "stderr", "content", "entries", "matches", "results", "summary"]
                for k in show_keys:
                    if k in data and data[k]:
                        val = str(data[k])
                        if len(val) > 500:
                            val = val[:500] + "\n…"
                        result_text += f"\n\n{k}:\n{val}"
                        break

            result_area.update(result_text)
            try:
                result_area.remove_class("running-label")
            except Exception:
                pass
            result_area.add_class("tool-result")

            collapsible.title = f"{icon} Tool: {self._tool_name} ({result_summary})"
            collapsible.collapsed = True

            if file_path:
                file_card = Static(
                    f"📎 File produced: {file_path}  (open in file manager)",
                    classes="file-card",
                )
                self.mount(file_card)

        else:
            error = result.get("error", "Unknown error")
            result_area.update(f"❌ Error: {error}")
            try:
                result_area.remove_class("running-label")
            except Exception:
                pass
            result_area.add_class("tool-error")
            collapsible.title = f"{icon} Tool: {self._tool_name} (❌ Error)"

