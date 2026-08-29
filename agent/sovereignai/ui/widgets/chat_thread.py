"""
chat_thread.py — Chat display area (VerticalScroll container).

Uses VerticalScroll (not ScrollView) so multiple children can be mounted freely.
"""
from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown, Static

from sovereignai.ui.widgets.thought_block import ThoughtBlock
from sovereignai.ui.widgets.tool_call_block import ToolCallBlock


# ── Message widgets ────────────────────────────────────────────────────────

class UserMessage(Widget):
    DEFAULT_CSS = """
    UserMessage {
        background: #161920;
        border-left: thick #5FA8D3;
        margin: 1 0 0 0;
        padding: 0 1 0 2;
        height: auto;
        color: #cdd6f4;
    }
    """
    def __init__(self, text: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = text

    def compose(self) -> ComposeResult:
        yield Static(self._text)


class RoutingLine(Widget):
    DEFAULT_CSS = """
    RoutingLine {
        color: #445566;
        text-style: italic dim;
        margin: 0 0 0 3;
        padding: 0;
        height: 1;
    }
    RoutingLine.uncertain {
        color: #D9A441;
    }
    """
    def __init__(self, text: str, uncertain: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = text
        self._uncertain = uncertain

    def compose(self) -> ComposeResult:
        yield Static(self._text)

    def on_mount(self) -> None:
        if self._uncertain:
            self.add_class("uncertain")


class LiveText(Static):
    """A live-updating static widget for direct token streaming with zero latency."""
    DEFAULT_CSS = """
    LiveText {
        margin: 0 0 0 2;
        padding: 0 1;
        color: #cdd6f4;
        height: auto;
    }
    """
    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._text = ""

    def append(self, chunk: str) -> None:
        self._text += chunk
        self.update(self._text)

    def get_text(self) -> str:
        return self._text


class LoadingIndicator(Widget):
    """
    Animated loading/thinking indicator with cycling pulsing dots.
    Rendered directly in the chat thread while waiting for responses.
    """
    DEFAULT_CSS = """
    LoadingIndicator {
        margin: 0 0 0 2;
        padding: 0 1;
        height: auto;
        color: #D9A441;
    }
    LoadingIndicator Static {
        color: #D9A441;
        text-style: italic;
    }
    """

    DOT_FRAMES = [
        "● ○ ○ ○",
        "○ ● ○ ○",
        "○ ○ ● ○",
        "○ ○ ○ ●",
        "○ ○ ● ○",
        "○ ● ○ ○",
    ]

    def __init__(self, text: str = "Loading your answer…", **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = text
        self._frame = 0
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Static(f"⏳ {self._text}  {self.DOT_FRAMES[0]}", id="loading-label")

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.2, self._tick)

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % len(self.DOT_FRAMES)
        dots = self.DOT_FRAMES[self._frame]
        try:
            self.query_one("#loading-label", Static).update(f"⏳ {self._text}  {dots}")
        except Exception:
            pass

    def set_status(self, text: str) -> None:
        self._text = text
        dots = self.DOT_FRAMES[self._frame]
        try:
            self.query_one("#loading-label", Static).update(f"⏳ {self._text}  {dots}")
        except Exception:
            pass


class AssistantMessage(Widget):
    DEFAULT_CSS = """
    AssistantMessage {
        margin: 0 0 1 2;
        padding: 0 1;
        height: auto;
        color: #cdd6f4;
    }
    AssistantMessage Markdown {
        color: #cdd6f4;
        background: transparent;
        padding: 0;
        margin: 0;
    }
    """
    def __init__(self, text: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = text

    def compose(self) -> ComposeResult:
        yield Markdown(self._text or "")

    def update(self, text: str) -> None:
        self._text = text
        try:
            self.query_one(Markdown).update(text)
        except Exception:
            pass


class SystemMessage(Widget):
    DEFAULT_CSS = """
    SystemMessage {
        margin: 1 0 0 2;
        padding: 0 1;
        height: auto;
        color: #5FA8D3;
    }
    SystemMessage.warning { color: #D9A441; text-style: italic; }
    SystemMessage.error   { color: #cc4444; text-style: italic; }
    """
    def __init__(self, text: str, style: str = "info", **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = text
        self._style = style

    def compose(self) -> ComposeResult:
        # Use markup=True so Rich markup in the banner renders with colours
        yield Static(self._text, markup=True)

    def on_mount(self) -> None:
        if self._style in ("warning", "error"):
            self.add_class(self._style)


# ── Main chat container ────────────────────────────────────────────────────

class ChatThread(VerticalScroll):
    """
    Scrollable chat thread. Supports mounting user messages, routing lines,
    loading indicators, thought blocks, tool calls, and assistant responses.
    """

    DEFAULT_CSS = """
    ChatThread {
        background: #0d0f12;
        padding: 1 2 2 2;
        scrollbar-color: #2e3440 #0d0f12;
        scrollbar-size: 1 1;
        height: 1fr;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # State tracking for current agent turn
        self._live: LiveText | None = None
        self._loading: LoadingIndicator | None = None
        self._thought: ThoughtBlock | None = None
        self._step_start: float = 0.0
        self._current_tool_blocks: dict[str, ToolCallBlock] = {}

    def reset_turn_state(self) -> None:
        """Call this at the start of each new user turn."""
        self._live = None
        self._loading = None
        self._thought = None
        self._step_start = time.time()
        self._current_tool_blocks = {}

    # ── Public API ─────────────────────────────────────────────────────────

    async def add_user_message(self, text: str) -> None:
        await self.mount(UserMessage(text))
        self.scroll_end(animate=False)

    async def show_loading(self, text: str = "Loading your answer…") -> None:
        """Show or update the animated loading dots indicator."""
        if self._loading is not None:
            self._loading.set_status(text)
            return
        self._loading = LoadingIndicator(text=text)
        await self.mount(self._loading)
        self.scroll_end(animate=False)

    def set_loading_status(self, text: str) -> None:
        """Update status text of existing loading indicator."""
        if self._loading is not None:
            self._loading.set_status(text)

    async def remove_loading(self) -> None:
        """Remove the animated loading indicator."""
        if self._loading is not None:
            try:
                await self._loading.remove()
            except Exception:
                pass
            self._loading = None

    async def add_routing_line(self, category: str, model: str, confidence: float,
                                reason: str, uncertain: bool) -> None:
        if uncertain:
            text = f"⚠ auto-routing uncertain → general model  (override: /models)"
        else:
            text = f"→ {category} ({model}) · {confidence:.2f} conf · {reason}"
        
        # If loading indicator is visible, mount routing line right before/around it
        await self.mount(RoutingLine(text, uncertain=uncertain))
        self.scroll_end(animate=False)

    async def stream_chunk(self, chunk: str) -> None:
        """Add a streaming chunk to the live text area with instant rendering."""
        if self._loading is not None:
            await self.remove_loading()
        if self._live is None:
            self._live = LiveText()
            self._step_start = time.time()
            await self.mount(self._live)
        self._live.append(chunk)
        self.scroll_end(animate=False)

    async def finalize_stream_as_thought(self) -> None:
        """Convert the current live text into a collapsed thought block."""
        await self.remove_loading()
        if self._live is None:
            return
        text = self._live.get_text()
        duration_ms = int((time.time() - self._step_start) * 1000)
        thought = ThoughtBlock(duration_ms=duration_ms, text=text)
        await self._live.remove()
        self._live = None
        await self.mount(thought)
        self._thought = thought
        self.scroll_end(animate=False)

    async def finalize_stream_as_answer(self) -> None:
        """Convert the current live text into a rendered markdown assistant answer."""
        await self.remove_loading()
        if self._live is None:
            return
        text = self._live.get_text()
        await self._live.remove()
        self._live = None
        msg = AssistantMessage(text)
        await self.mount(msg)
        self.scroll_end(animate=False)

    async def add_tool_call_block(self, call_id: str, name: str, args: dict) -> ToolCallBlock:
        await self.remove_loading()
        block = ToolCallBlock(tool_name=name, args=args)
        self._current_tool_blocks[call_id] = block
        await self.mount(block)
        self.scroll_end(animate=False)
        return block

    def finish_tool_call(self, call_id: str, result: dict) -> None:
        block = self._current_tool_blocks.get(call_id)
        if block:
            block.set_result(result)
            self.scroll_end(animate=False)

    async def add_system_message(self, text: str, style: str = "info") -> None:
        await self.remove_loading()
        await self.mount(SystemMessage(text, style=style))
        self.scroll_end(animate=False)

    async def add_divider(self) -> None:
        await self.mount(Static("─" * 60, classes="divider"))
        self.scroll_end(animate=False)
