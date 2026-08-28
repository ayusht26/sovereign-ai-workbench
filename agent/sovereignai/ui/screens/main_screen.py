"""
main_screen.py — Primary SovereignAI screen.

Architecture:

    Textual UI thread
        │
        ├── input / rendering
        ├── cached GPU information
        └── asyncio.Queue consumer
                │
                ▼
        Agent worker thread
                │
                ├── router
                ├── tools
                └── Ollama

Streaming output is batched so the UI is never forced to render
for every single LLM token.

GPU monitoring also runs outside the UI thread.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static, Label, Footer

from sovereignai.ui.widgets.chat_thread import ChatThread
from sovereignai.ui.widgets.status_bar import StatusBar


# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────


_BANNER = """\
[bold #5FA8D3]███████╗ ██████╗ ██╗   ██╗ █████╗ ██╗[/]
[bold #4a90b8]██╔════╝██╔═══██╗██║   ██║██╔══██╗██║[/]
[bold #3d7da0]███████╗██║   ██║██║   ██║███████║██║[/]
[bold #306988]╚════██║██║   ██║╚██╗ ██╔╝██╔══██║██║[/]
[bold #2E5A7A]███████║╚██████╔╝ ╚████╔╝ ██║  ██║██║[/]
[bold #2E5A7A]╚══════╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝╚═╝[/]

[dim]        S O V E R E I G N   A I[/]
[bold #D9A441]   Local models. Local data. Zero external calls.   🔒 OFFLINE[/]"""


# ─────────────────────────────────────────────────────────────────────────────
# GPU information
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class GPUInfo:
    name: str
    used_mb: float
    total_mb: float
    vram_pct: int
    gpu_util: float


def query_gpu() -> GPUInfo | None:
    """
    Query primary GPU metrics via nvidia-smi.

    IMPORTANT:
    This function can block and MUST NOT be called from Textual's
    UI/event-loop thread.

    MainScreen runs it from a dedicated monitoring thread.
    """
    if not shutil.which("nvidia-smi"):
        return None

    try:
        flags = (
            0x08000000
            if hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0
        )

        res = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=1,
            creationflags=flags,
        )

        if res.returncode != 0:
            return None

        if not res.stdout.strip():
            return None

        line = res.stdout.strip().splitlines()[0]

        parts = [
            p.strip()
            for p in line.split(",")
        ]

        if len(parts) < 4:
            return None

        raw_name = (
            parts[0]
            .replace("NVIDIA GeForce ", "")
            .replace("NVIDIA ", "")
        )

        used_mb = float(parts[1])
        total_mb = float(parts[2])
        gpu_util = float(parts[3])

        vram_pct = (
            int(used_mb / total_mb * 100)
            if total_mb > 0
            else 0
        )

        return GPUInfo(
            name=raw_name,
            used_mb=used_mb,
            total_mb=total_mb,
            vram_pct=vram_pct,
            gpu_util=gpu_util,
        )

    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# GPU monitor
# ─────────────────────────────────────────────────────────────────────────────


class GPUMonitor:
    """
    Background GPU monitor.

    nvidia-smi is blocking, so it never runs from the Textual event loop.

    The UI simply reads the latest cached value.
    """

    def __init__(self, interval: float = 1.0) -> None:
        self.interval = interval

        self._latest: GPUInfo | None = None

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="sovereignai-gpu-monitor",
            daemon=True,
        )

        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def get_latest(self) -> GPUInfo | None:
        with self._lock:
            return self._latest

    def _run(self) -> None:
        while not self._stop_event.is_set():
            info = query_gpu()

            with self._lock:
                self._latest = info

            self._stop_event.wait(self.interval)


# ─────────────────────────────────────────────────────────────────────────────
# Info panel
# ─────────────────────────────────────────────────────────────────────────────


class InfoPanel(Static):
    """Right-hand session/context/GPU panel."""

    DEFAULT_CSS = """
    InfoPanel {
        width: 30;
        background: #111318;
        border-left: solid #1e2128;
        padding: 1 2;
        color: #667788;
        height: 100%;
    }

    InfoPanel .ph {
        color: #5FA8D3;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }

    InfoPanel .pv {
        color: #99aabb;
        margin-bottom: 0;
        padding-left: 1;
    }

    InfoPanel .net-ok {
        color: #44bb88;
        text-style: bold;
    }

    InfoPanel .net-alert {
        color: #cc4444;
        text-style: bold;
    }

    InfoPanel .dim-val {
        color: #445566;
        padding-left: 1;
    }

    InfoPanel .gpu-active {
        color: #44bb88;
        text-style: bold;
        padding-left: 1;
    }

    InfoPanel .gpu-high {
        color: #D9A441;
        text-style: bold;
        padding-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Session", classes="ph")
        yield Static(
            "—",
            id="si-session-id",
            classes="pv",
        )

        yield Static("Context", classes="ph")
        yield Static(
            "0 tokens · 0% used",
            id="si-tokens",
            classes="pv",
        )

        yield Static(
            "$0.00 spent (fully local)",
            classes="dim-val",
        )

        yield Static("Model", classes="ph")
        yield Static(
            "AUTO",
            id="si-model",
            classes="pv",
        )

        yield Static("GPU", classes="ph")
        yield Static(
            "Detecting…",
            id="si-gpu-name",
            classes="pv",
        )

        yield Static(
            "0% util · 0.0/0.0 GB",
            id="si-gpu-stat",
            classes="gpu-active",
        )

        yield Static("Network", classes="ph")
        yield Static(
            "🔒 0 external calls",
            id="si-net",
            classes="net-ok",
        )

        yield Static(
            "(0 tool calls, 0 egress)",
            id="si-net-detail",
            classes="dim-val",
        )

    def refresh_all(
        self,
        session_id: str,
        tokens: int,
        tool_calls: int,
        model: str,
        external: int,
        gpu_info: GPUInfo | None = None,
    ) -> None:
        self._set(
            "#si-session-id",
            session_id[:20]
            + ("…" if len(session_id) > 20 else ""),
        )

        pct = min(
            int(tokens / 8192 * 100),
            100,
        )

        self._set(
            "#si-tokens",
            f"{tokens:,} tokens · {pct}% used",
        )

        self._set(
            "#si-model",
            model,
        )

        self._set(
            "#si-net-detail",
            f"({tool_calls} tool calls, 0 egress)",
        )

        net_w = self.query_one(
            "#si-net",
            Static,
        )

        if external == 0:
            net_w.set_classes("net-ok")
            net_w.update("🔒 0 external calls")
        else:
            net_w.set_classes("net-alert")
            net_w.update(
                f"⚠ {external} EXTERNAL CALL"
                f"{'S' if external != 1 else ''}"
            )

        # GPU information comes from the background monitor.
        if gpu_info:
            self._set(
                "#si-gpu-name",
                gpu_info.name[:24],
            )

            used_gb = gpu_info.used_mb / 1024.0
            total_gb = gpu_info.total_mb / 1024.0

            gpu_stat = self.query_one(
                "#si-gpu-stat",
                Static,
            )

            if gpu_info.vram_pct > 85:
                gpu_stat.set_classes("gpu-high")
            else:
                gpu_stat.set_classes("gpu-active")

            gpu_stat.update(
                f"{int(gpu_info.gpu_util)}% util · "
                f"{used_gb:.1f}/{total_gb:.1f} GB "
                f"({gpu_info.vram_pct}%)"
            )

        else:
            self._set(
                "#si-gpu-name",
                "CPU / Integrated",
            )

            self._set(
                "#si-gpu-stat",
                "Local inference",
            )

    def _set(
        self,
        selector: str,
        text: str,
    ) -> None:
        try:
            self.query_one(
                selector,
                Static,
            ).update(text)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Main screen
# ─────────────────────────────────────────────────────────────────────────────


class MainScreen(Screen):
    """Primary SovereignAI screen."""

    BINDINGS = [
        ("ctrl+p", "command_palette", "Commands"),
        ("escape", "interrupt", "Interrupt"),
        ("ctrl+n", "new_session", "New"),
    ]

    DEFAULT_CSS = """
    MainScreen {
        background: #0d0f12;
        layout: vertical;
    }

    /* ── Main body (chat + sidebar) ── */

    #body {
        layout: horizontal;
        height: 1fr;
    }

    #chat-column {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }

    /* ── Input area ── */

    #input-zone {
        height: auto;
        background: #111318;
        border-top: solid #1e2128;
        padding: 1 2 0 2;
    }

    #input-box {
        background: #0d0f12;
        border: solid #2e3440;
        border-left: thick #5FA8D3;
        color: #cdd6f4;
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    #input-box:focus {
        border: solid #5FA8D3;
        border-left: thick #7bbde0;
    }

    #meta-bar {
        height: 1;
        color: #3a4555;
        padding: 0 1;
        margin-top: 0;
        margin-bottom: 1;
    }

    #thinking-bar {
        height: 1;
        color: #D9A441;
        text-style: italic;
        padding: 0 1;
        margin-bottom: 0;
    }
    """

    # Streaming configuration.
    #
    # Ollama can generate a large number of small chunks.
    # Sending every chunk separately to the Textual event loop is unnecessary.
    STREAM_BATCH_INTERVAL = 0.03

    def __init__(
        self,
        session,
        workspace: Path,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self._session = session
        self._workspace = workspace

        os.environ["SOVAI_WORKSPACE"] = str(workspace)

        self._model_override: str | None = None
        self._is_generating = False

        # Background GPU monitor.
        self._gpu_monitor = GPUMonitor(
            interval=1.0,
        )

        # Keep a reference to the current worker so interrupt/new session
        # logic can coexist safely with the background operation.
        self._agent_thread: threading.Thread | None = None

    def compose(self) -> ComposeResult:
        with Container(id="body"):
            with Vertical(id="chat-column"):
                yield ChatThread(id="chat-thread")

                with Vertical(id="input-zone"):
                    yield Static(
                        "",
                        id="thinking-bar",
                    )

                    yield Input(
                        placeholder=(
                            "Ask anything… or type /help for commands"
                        ),
                        id="input-box",
                    )

                    yield Static(
                        f"AUTO  ·  📁 {self._workspace}",
                        id="meta-bar",
                    )

            yield InfoPanel(id="info-panel")

        yield StatusBar(id="status-bar")

    async def on_mount(self) -> None:
        # Show ASCII banner.
        chat = self.query_one(
            "#chat-thread",
            ChatThread,
        )

        await chat.add_system_message(
            _BANNER
        )

        # Start network guard.
        from sovereignai.net_guard.monitor import get_monitor

        mon = get_monitor()

        # The network monitor may call its callback from a background
        # thread, so _on_net_alert safely marshals the notification
        # back onto Textual's UI thread.
        mon.add_alert_callback(
            self._on_net_alert
        )

        mon.start()

        # Start GPU monitor OUTSIDE Textual's UI thread.
        self._gpu_monitor.start()

        # Periodic UI refresh now only reads cached GPU information.
        self.set_interval(
            1.0,
            self._periodic_refresh,
        )

        # Initial info panel.
        info = self.query_one(
            "#info-panel",
            InfoPanel,
        )

        info.refresh_all(
            session_id=self._session.id,
            tokens=0,
            tool_calls=0,
            model=self._mode_badge(),
            external=0,
            gpu_info=self._gpu_monitor.get_latest(),
        )

        # Focus input.
        self.query_one(
            "#input-box",
            Input,
        ).focus()

    def on_unmount(self) -> None:
        """
        Stop background monitoring when the screen is removed.
        """
        try:
            self._gpu_monitor.stop()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Network alerts
    # ─────────────────────────────────────────────────────────────────────

    def _on_net_alert(self, count: int) -> None:
        """
        Network monitor callbacks may arrive from a non-UI thread.

        Never directly modify Textual UI from that thread.
        """
        try:
            self.app.call_from_thread(
                self._show_net_alert,
                count,
            )
        except Exception:
            # If the app is shutting down or the callback already happens
            # on the UI thread, simply ignore the notification.
            pass

    def _show_net_alert(self, count: int) -> None:
        self.app.notify(
            f"⚠ Network: {count} external connection(s) detected!",
            severity="error",
            timeout=8,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Periodic UI refresh
    # ─────────────────────────────────────────────────────────────────────

    def _periodic_refresh(self) -> None:
        """
        Refresh sidebar information.

        IMPORTANT:
        No blocking subprocesses happen here anymore.
        """
        from sovereignai.net_guard.monitor import get_monitor

        state = get_monitor().get_state()

        # This is just a cached read.
        gpu_info = self._gpu_monitor.get_latest()

        try:
            info = self.query_one(
                "#info-panel",
                InfoPanel,
            )

            info.refresh_all(
                session_id=self._session.id,
                tokens=self._session.total_tokens,
                tool_calls=self._session.tool_calls_made,
                model=self._mode_badge(),
                external=state.external_attempts,
                gpu_info=gpu_info,
            )

        except Exception:
            pass

    def _mode_badge(self) -> str:
        if (
            self._model_override
            and self._model_override != "AUTO"
        ):
            return self._model_override

        return "AUTO"

    # ─────────────────────────────────────────────────────────────────────
    # Input handling
    # ─────────────────────────────────────────────────────────────────────

    async def on_input_submitted(
        self,
        event: Input.Submitted,
    ) -> None:
        text = event.value.strip()

        if not text:
            return

        if self._is_generating:
            self.notify(
                "Generation in progress — press ESC to interrupt."
            )
            return

        event.input.clear()

        if text.startswith("/"):
            await self._handle_slash(text)
        else:
            await self._run_turn(text)

    async def _handle_slash(
        self,
        cmd: str,
    ) -> None:
        parts = cmd.split()

        head = parts[0].lower()

        chat = self.query_one(
            "#chat-thread",
            ChatThread,
        )

        if head == "/models":
            await self._open_model_palette()

        elif head == "/auto":
            self._model_override = None

            self._update_meta()

            await chat.add_system_message(
                "Switched to AUTO model selection.",
                "info",
            )

        elif head == "/net":
            from sovereignai.ui.screens.net_monitor_screen import (
                NetMonitorScreen,
            )

            self.app.push_screen(
                NetMonitorScreen()
            )

        elif head in ("/new",):
            await self.app.action_new_session()

        elif head == "/sessions":
            from sovereignai.ui.screens.session_browser import (
                SessionBrowser,
            )

            self.app.push_screen(
                SessionBrowser()
            )

        elif head == "/kb":
            await self._handle_kb(parts)

        elif head == "/cwd" and len(parts) > 1:
            p = (
                Path(
                    " ".join(parts[1:])
                )
                .expanduser()
                .resolve()
            )

            if p.is_dir():
                self._workspace = p

                os.environ["SOVAI_WORKSPACE"] = str(p)

                self._update_meta()

                await chat.add_system_message(
                    f"Workspace → {p}",
                    "info",
                )

            else:
                await chat.add_system_message(
                    f"Not a directory: {p}",
                    "error",
                )

        elif head == "/help":
            await chat.add_system_message(
                "Commands: /models /auto /net /new /sessions /kb /cwd /help\n"
                "Keys: ctrl+p (palette)   esc (interrupt)   "
                "ctrl+n (new session)",
                "info",
            )

        else:
            await chat.add_system_message(
                f"Unknown: {cmd}  →  type /help",
                "warning",
            )

    async def _handle_kb(
        self,
        parts: list[str],
    ) -> None:
        chat = self.query_one(
            "#chat-thread",
            ChatThread,
        )

        sub = (
            parts[1]
            if len(parts) > 1
            else "status"
        )

        if sub == "status":
            try:
                from sovereignai.knowledge_base.store import (
                    get_store,
                )

                s = get_store().stats()

                await chat.add_system_message(
                    f"📚 KB: {s['documents']} docs · "
                    f"{s['chunks']} chunks · "
                    f"{s['disk_mb']:.1f} MB",
                    "info",
                )

            except Exception as e:
                await chat.add_system_message(
                    f"KB error: {e}",
                    "error",
                )

        elif sub == "add" and len(parts) > 2:
            p = (
                Path(
                    " ".join(parts[2:])
                )
                .expanduser()
                .resolve()
            )

            await chat.add_system_message(
                f"Ingesting {p} …",
                "info",
            )

            try:
                from sovereignai.knowledge_base.ingest import (
                    ingest_path,
                )

                stats = ingest_path(
                    p,
                    verbose=False,
                )

                await chat.add_system_message(
                    f"✅ {stats['docs']} docs, "
                    f"{stats['chunks']} chunks ingested.",
                    "info",
                )

            except Exception as e:
                await chat.add_system_message(
                    f"KB error: {e}",
                    "error",
                )

        else:
            await chat.add_system_message(
                "Usage: /kb status | /kb add <path>",
                "info",
            )

    # ─────────────────────────────────────────────────────────────────────
    # Model palette
    # ─────────────────────────────────────────────────────────────────────

    async def _open_model_palette(self) -> None:
        from sovereignai.ui.screens.model_palette import (
            ModelPalette,
        )

        async def on_select(
            model: str | None,
        ) -> None:
            if model is None:
                return

            if model.startswith("/"):
                self.app.call_later(
                    self._handle_slash,
                    model,
                )
                return

            self._model_override = (
                None
                if model == "AUTO"
                else model
            )

            self._update_meta()

            chat = self.query_one(
                "#chat-thread",
                ChatThread,
            )

            if model == "AUTO":
                await chat.add_system_message(
                    "Switched to AUTO model selection.",
                    "info",
                )
            else:
                await chat.add_system_message(
                    f"Active model switched to "
                    f"[bold]{model}[/].",
                    "info",
                )

        await self.app.push_screen(
            ModelPalette(
                current_model=self._mode_badge()
            ),
            on_select,
        )

    def _update_meta(self) -> None:
        badge = self._mode_badge()

        try:
            self.query_one(
                "#meta-bar",
                Static,
            ).update(
                f"{badge}  ·  📁 {self._workspace}"
            )

            self.query_one(
                "#status-bar",
                StatusBar,
            ).set_model(
                badge,
                badge,
            )

        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Agent loop
    # ─────────────────────────────────────────────────────────────────────

    async def _run_turn(
        self,
        user_text: str,
    ) -> None:
        from sovereignai.orchestrator.agent_loop import (
            run_agent_turn,
        )

        chat = self.query_one(
            "#chat-thread",
            ChatThread,
        )

        status = self.query_one(
            "#status-bar",
            StatusBar,
        )

        thinking = self.query_one(
            "#thinking-bar",
            Static,
        )

        self._is_generating = True

        self._session.cancelled = False

        start_time = time.time()

        await chat.add_user_message(
            user_text
        )

        chat.reset_turn_state()

        await chat.show_loading(
            "Loading your answer…"
        )

        thinking.update(
            "⏳ Routing…"
        )

        # ───────────────────────────────────────────────────────────────
        # Thread → asyncio communication
        # ───────────────────────────────────────────────────────────────

        queue: asyncio.Queue = asyncio.Queue()

        loop = asyncio.get_running_loop()

        # The worker batches stream chunks before sending them to the UI.
        #
        # Example:
        #
        #   token token token token
        #
        # becomes:
        #
        #   one stream_chunk event
        #
        # approximately every 30ms.
        def _producer() -> None:
            """
            Runs the blocking agent loop in a background thread.
            """

            pending_text = ""

            last_flush = time.monotonic()

            def emit(event: dict) -> None:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    event,
                )

            def flush_stream() -> None:
                nonlocal pending_text
                nonlocal last_flush

                if not pending_text:
                    return

                emit(
                    {
                        "kind": "stream_chunk",
                        "chunk": pending_text,
                    }
                )

                pending_text = ""
                last_flush = time.monotonic()

            try:
                for evt in run_agent_turn(
                    self._session,
                    user_text,
                    model_override=self._model_override,
                ):
                    # Check cancellation frequently.
                    if getattr(
                        self._session,
                        "cancelled",
                        False,
                    ):
                        flush_stream()
                        break

                    kind = evt.get(
                        "kind",
                        "",
                    )

                    # ────────────────────────────────────────────────
                    # Batch streaming chunks.
                    # ────────────────────────────────────────────────
                    if kind == "stream_chunk":
                        chunk = evt.get(
                            "chunk",
                            "",
                        )

                        if chunk:
                            pending_text += chunk

                        now = time.monotonic()

                        if (
                            now - last_flush
                            >= self.STREAM_BATCH_INTERVAL
                        ):
                            flush_stream()

                        continue

                    # ────────────────────────────────────────────────
                    # Before sending a non-stream event, make sure all
                    # previously buffered model text is delivered first.
                    # This preserves event ordering.
                    # ────────────────────────────────────────────────
                    flush_stream()

                    emit(evt)

                # Flush any remaining text.
                flush_stream()

            except Exception as e:
                flush_stream()

                emit(
                    {
                        "kind": "error",
                        "message": str(e),
                    }
                )

            finally:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    None,
                )

        self._agent_thread = threading.Thread(
            target=_producer,
            name="sovereignai-agent-worker",
            daemon=True,
        )

        self._agent_thread.start()

        # ───────────────────────────────────────────────────────────────
        # UI event consumer
        # ───────────────────────────────────────────────────────────────

        try:
            while True:
                evt = await queue.get()

                if evt is None:
                    break

                await self._handle_event(
                    evt,
                    chat,
                    status,
                    thinking,
                    start_time,
                )

                # Explicitly yield control to Textual.
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            self._session.cancelled = True
            raise

        except Exception as e:
            await chat.add_system_message(
                f"Error: {e}",
                "error",
            )

        finally:
            self._is_generating = False

            thinking.update("")

            self.query_one(
                "#input-box",
                Input,
            ).focus()

            elapsed = (
                time.time()
                - start_time
            )

            status.set_elapsed(
                elapsed
            )

            self._agent_thread = None

    async def _handle_event(
        self,
        evt: dict,
        chat: ChatThread,
        status: StatusBar,
        thinking: Static,
        start_time: float,
    ) -> None:
        kind = evt.get(
            "kind",
            "",
        )

        # ─────────────────────────────────────────────────────────────
        # Routing
        # ─────────────────────────────────────────────────────────────

        if kind == "routing_decision":
            thinking.update(
                f"→ routing to "
                f"{evt['category']} "
                f"({evt['model_name']})…"
            )

            await chat.add_routing_line(
                category=evt["category"],
                model=evt["model_name"],
                confidence=evt["confidence"],
                reason=evt.get(
                    "reason",
                    "",
                ),
                uncertain=evt.get(
                    "uncertain",
                    False,
                ),
            )

            chat.set_loading_status(
                f"Thinking with "
                f"{evt['model_name']}…"
            )

            model_str = (
                f"AUTO → "
                f"{evt['model_name']}"
            )

            status.set_model(
                "AUTO",
                model_str,
            )

        # ─────────────────────────────────────────────────────────────
        # Stream
        # ─────────────────────────────────────────────────────────────

        elif kind == "stream_chunk":
            # stream_chunk() now only appends to the buffer.
            # The ChatThread timer performs the actual rendering.
            await chat.stream_chunk(
                evt["chunk"]
            )

        # ─────────────────────────────────────────────────────────────
        # Tool start
        # ─────────────────────────────────────────────────────────────

        elif kind == "tool_call_start":
            await chat.finalize_stream_as_thought()

            name = evt["name"]

            thinking.update(
                f"🔧 {name}…"
            )

            call_id = (
                f"{name}_"
                f"{evt.get('step', 0)}"
            )

            await chat.add_tool_call_block(
                call_id,
                name,
                evt.get("args", {}),
            )

            await chat.show_loading(
                f"Running {name}…"
            )

        # ─────────────────────────────────────────────────────────────
        # Tool result
        # ─────────────────────────────────────────────────────────────

        elif kind == "tool_call_result":
            name = evt["name"]

            call_id = (
                f"{name}_"
                f"{evt.get('step', 0)}"
            )

            chat.finish_tool_call(
                call_id,
                evt["result"],
            )

            thinking.update(
                "💭 Thinking…"
            )

            await chat.show_loading(
                "Processing tool result…"
            )

        # ─────────────────────────────────────────────────────────────
        # Done
        # ─────────────────────────────────────────────────────────────

        elif kind == "done":
            await chat.remove_loading()

            await chat.finalize_stream_as_answer()

            thinking.update("")

            status.set_elapsed(
                time.time()
                - start_time
            )

        # ─────────────────────────────────────────────────────────────
        # Error
        # ─────────────────────────────────────────────────────────────

        elif kind == "error":
            await chat.remove_loading()

            await chat.add_system_message(
                f"❌ {evt.get('message', '?')}",
                "error",
            )

        # ─────────────────────────────────────────────────────────────
        # Max iterations
        # ─────────────────────────────────────────────────────────────

        elif kind == "max_iterations_reached":
            await chat.remove_loading()

            await chat.finalize_stream_as_answer()

            await chat.add_system_message(
                "⚠ Reached max iterations.",
                "warning",
            )

        # ─────────────────────────────────────────────────────────────
        # Interrupted
        # ─────────────────────────────────────────────────────────────

        elif kind == "interrupted":
            await chat.remove_loading()

            await chat.add_system_message(
                "⛔ Interrupted.",
                "warning",
            )

    # ─────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────

    def action_command_palette(self) -> None:
        from sovereignai.ui.screens.command_palette import (
            CommandPalette,
        )

        def on_cmd(
            cmd: str | None,
        ) -> None:
            if cmd:
                self.app.call_later(
                    self._handle_slash,
                    cmd,
                )

        self.app.push_screen(
            CommandPalette(),
            on_cmd,
        )

    def action_interrupt(self) -> None:
        if self._is_generating:
            self._session.cancelled = True

            try:
                self.query_one(
                    "#thinking-bar",
                    Static,
                ).update(
                    "⛔ Interrupting…"
                )
            except Exception:
                pass

        else:
            self.app.bell()

    async def action_new_session(self) -> None:
        await self.app.action_new_session()

