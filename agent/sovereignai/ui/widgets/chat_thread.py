"""
chat_thread.py — Chat display area (VerticalScroll container).

Handles:
- User messages
- Routing messages
- Buffered streaming assistant output
- Loading indicators
- Thought blocks
- Tool call blocks
- Final Markdown responses

Streaming is intentionally buffered so Textual does not re-render for
every single token received from the local LLM.
"""

from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown, Static

from sovereignai.ui.widgets.thought_block import ThoughtBlock
from sovereignai.ui.widgets.tool_call_block import ToolCallBlock


# ─────────────────────────────────────────────────────────────────────────────
# Message widgets
# ─────────────────────────────────────────────────────────────────────────────


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

    def __init__(
        self,
        text: str,
        uncertain: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._text = text
        self._uncertain = uncertain

    def compose(self) -> ComposeResult:
        yield Static(self._text)

    def on_mount(self) -> None:
        if self._uncertain:
            self.add_class("uncertain")


# ─────────────────────────────────────────────────────────────────────────────
# Buffered streaming text
# ─────────────────────────────────────────────────────────────────────────────


class LiveText(Static):
    """
    Buffered live-updating text widget.

    IMPORTANT:
    Do not call update() for every token.

    The LLM may produce dozens/hundreds of chunks per second. Updating a
    Textual widget for every chunk causes unnecessary layout/render work.

    Instead:
        append() -> cheap in-memory operation
        flush()  -> actual Textual render

    ChatThread calls flush() approximately every 40ms (~25 FPS).
    """

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
        self._pending = ""

    def append(self, chunk: str) -> None:
        """
        Add streamed text without immediately forcing a render.
        """
        if not chunk:
            return

        self._text += chunk
        self._pending += chunk

    def flush(self) -> bool:
        """
        Render pending text.

        Returns True when a render occurred.
        """
        if not self._pending:
            return False

        self.update(self._text)
        self._pending = ""

        return True

    def get_text(self) -> str:
        return self._text


# ─────────────────────────────────────────────────────────────────────────────
# Loading indicator
# ─────────────────────────────────────────────────────────────────────────────


class LoadingIndicator(Widget):
    """
    Animated loading/thinking indicator with cycling pulsing dots.
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

    def __init__(
        self,
        text: str = "Loading your answer…",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self._text = text
        self._frame = 0
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Static(
            f"⏳ {self._text}  {self.DOT_FRAMES[0]}",
            id="loading-label",
        )

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.2, self._tick)

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % len(self.DOT_FRAMES)
        dots = self.DOT_FRAMES[self._frame]

        try:
            self.query_one("#loading-label", Static).update(
                f"⏳ {self._text}  {dots}"
            )
        except Exception:
            pass

    def set_status(self, text: str) -> None:
        self._text = text
        dots = self.DOT_FRAMES[self._frame]

        try:
            self.query_one("#loading-label", Static).update(
                f"⏳ {self._text}  {dots}"
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Final assistant message
# ─────────────────────────────────────────────────────────────────────────────


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


# ─────────────────────────────────────────────────────────────────────────────
# System messages
# ─────────────────────────────────────────────────────────────────────────────


class SystemMessage(Widget):
    DEFAULT_CSS = """
    SystemMessage {
        margin: 1 0 0 2;
        padding: 0 1;
        height: auto;
        color: #5FA8D3;
    }

    SystemMessage.warning {
        color: #D9A441;
        text-style: italic;
    }

    SystemMessage.error {
        color: #cc4444;
        text-style: italic;
    }
    """

    def __init__(
        self,
        text: str,
        style: str = "info",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self._text = text
        self._style = style

    def compose(self) -> ComposeResult:
        # Rich markup is needed for the ASCII banner.
        yield Static(self._text, markup=True)

    def on_mount(self) -> None:
        if self._style in ("warning", "error"):
            self.add_class(self._style)


# ─────────────────────────────────────────────────────────────────────────────
# Main chat container
# ─────────────────────────────────────────────────────────────────────────────


class ChatThread(VerticalScroll):
    """
    Scrollable chat thread.

    Streaming architecture:

        Agent worker
             ↓
        asyncio.Queue
             ↓
        MainScreen
             ↓
        stream_chunk()
             ↓
        LiveText buffer
             ↓
        25 FPS flush timer
             ↓
        Textual render

    This prevents the UI from being redrawn for every LLM token.
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

    # Render streaming output at ~25 FPS.
    # 0.04 seconds = 25 updates/sec.
    STREAM_FLUSH_INTERVAL = 0.04

    # Do not perform scroll calculations more often than this.
    SCROLL_INTERVAL = 0.08

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Current turn state.
        self._live: LiveText | None = None
        self._loading: LoadingIndicator | None = None
        self._thought: ThoughtBlock | None = None
        self._step_start: float = 0.0
        self._current_tool_blocks: dict[str, ToolCallBlock] = {}

        # Streaming/render state.
        self._stream_timer = None
        self._scroll_timer = None
        self._scroll_pending = False
        self._last_scroll = 0.0

    def on_mount(self) -> None:
        """
        Start the lightweight UI-side streaming renderer.

        The timer itself is cheap. It only performs work when there is
        pending streamed text.
        """
        self._stream_timer = self.set_interval(
            self.STREAM_FLUSH_INTERVAL,
            self._flush_stream,
        )

    def _flush_stream(self) -> None:
        """
        Periodically render buffered streaming text.

        This is the critical performance fix.
        """
        if self._live is None:
            return

        try:
            changed = self._live.flush()

            if changed:
                self._request_scroll()

        except Exception:
            pass

    def _request_scroll(self, force: bool = False) -> None:
        """
        Throttle scroll calculations.

        Calling scroll_end() for every token is unnecessarily expensive.
        """
        now = time.monotonic()

        if force or now - self._last_scroll >= self.SCROLL_INTERVAL:
            self._last_scroll = now

            try:
                self.scroll_end(animate=False)
            except Exception:
                pass

            self._scroll_pending = False
            return

        self._scroll_pending = True

    def _flush_scroll(self) -> None:
        """
        Flush a pending scroll request.
        """
        if not self._scroll_pending:
            return

        now = time.monotonic()

        if now - self._last_scroll < self.SCROLL_INTERVAL:
            return

        self._last_scroll = now
        self._scroll_pending = False

        try:
            self.scroll_end(animate=False)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Turn state
    # ─────────────────────────────────────────────────────────────────────

    def reset_turn_state(self) -> None:
        """
        Call this at the start of each new user turn.
        """
        self._live = None
        self._loading = None
        self._thought = None
        self._step_start = time.time()
        self._current_tool_blocks = {}

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    async def add_user_message(self, text: str) -> None:
        await self.mount(UserMessage(text))
        self._request_scroll(force=True)

    async def show_loading(
        self,
        text: str = "Loading your answer…",
    ) -> None:
        """
        Show or update the animated loading dots indicator.
        """
        if self._loading is not None:
            self._loading.set_status(text)
            return

        self._loading = LoadingIndicator(text=text)

        await self.mount(self._loading)

        self._request_scroll(force=True)

    def set_loading_status(self, text: str) -> None:
        """
        Update status text of existing loading indicator.
        """
        if self._loading is not None:
            self._loading.set_status(text)

    async def remove_loading(self) -> None:
        """
        Remove the animated loading indicator.
        """
        if self._loading is not None:
            try:
                await self._loading.remove()
            except Exception:
                pass

            self._loading = None

    async def add_routing_line(
        self,
        category: str,
        model: str,
        confidence: float,
        reason: str,
        uncertain: bool,
    ) -> None:
        if uncertain:
            text = (
                "⚠ auto-routing uncertain → general model  "
                "(override: /models)"
            )
        else:
            text = (
                f"→ {category} ({model}) · "
                f"{confidence:.2f} conf · {reason}"
            )

        await self.mount(
            RoutingLine(
                text,
                uncertain=uncertain,
            )
        )

        self._request_scroll(force=True)

    async def stream_chunk(self, chunk: str) -> None:
        """
        Add an LLM streaming chunk.

        IMPORTANT:
        This method deliberately does NOT call update() or scroll_end()
        for every token.

        It only appends to the in-memory LiveText buffer.
        The ChatThread timer performs actual rendering at ~25 FPS.
        """
        if not chunk:
            return

        if self._loading is not None:
            await self.remove_loading()

        if self._live is None:
            self._live = LiveText()
            self._step_start = time.time()

            await self.mount(self._live)

        # Cheap operation — no UI render here.
        self._live.append(chunk)

    async def _flush_before_finalize(self) -> str:
        """
        Make sure the final buffered text is rendered before converting
        the LiveText widget into a thought/answer.
        """
        if self._live is None:
            return ""

        try:
            self._live.flush()
        except Exception:
            pass

        return self._live.get_text()

    async def finalize_stream_as_thought(self) -> None:
        """
        Convert current live text into a collapsed thought block.
        """
        await self.remove_loading()

        if self._live is None:
            return

        text = await self._flush_before_finalize()

        duration_ms = int(
            (time.time() - self._step_start) * 1000
        )

        thought = ThoughtBlock(
            duration_ms=duration_ms,
            text=text,
        )

        await self._live.remove()
        self._live = None

        await self.mount(thought)

        self._thought = thought

        self._request_scroll(force=True)

    async def finalize_stream_as_answer(self) -> None:
        """
        Convert current live text into a rendered Markdown assistant answer.
        """
        await self.remove_loading()

        if self._live is None:
            return

        text = await self._flush_before_finalize()

        await self._live.remove()
        self._live = None

        msg = AssistantMessage(text)

        await self.mount(msg)

        self._request_scroll(force=True)

    async def add_tool_call_block(
        self,
        call_id: str,
        name: str,
        args: dict,
    ) -> ToolCallBlock:
        await self.remove_loading()

        block = ToolCallBlock(
            tool_name=name,
            args=args,
        )

        self._current_tool_blocks[call_id] = block

        await self.mount(block)

        self._request_scroll(force=True)

        return block

    def finish_tool_call(
        self,
        call_id: str,
        result: dict,
    ) -> None:
        block = self._current_tool_blocks.get(call_id)

        if block:
            block.set_result(result)
            self._request_scroll(force=True)

    async def add_system_message(
        self,
        text: str,
        style: str = "info",
    ) -> None:
        await self.remove_loading()

        await self.mount(
            SystemMessage(
                text,
                style=style,
            )
        )

        self._request_scroll(force=True)

    async def add_divider(self) -> None:
        await self.mount(
            Static(
                "─" * 60,
                classes="divider",
            )
        )

        self._request_scroll(force=True)
