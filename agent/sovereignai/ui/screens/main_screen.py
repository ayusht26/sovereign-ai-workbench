"""
main_screen.py — Primary SovereignAI screen.

Key fixes:
  1. Agent loop runs in a background THREAD via asyncio.Queue so the UI never freezes.
  2. Banner renders correctly.
  3. Network monitor no longer false-alerts.
  4. Cleaner visual layout matching Claude Code / OpenCode aesthetic.
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

from textual import events, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static, Label, Footer

from sovereignai.orchestrator.agent_loop import run_agent_turn
from sovereignai.ui.widgets.chat_thread import ChatThread
from sovereignai.ui.widgets.status_bar import StatusBar
from sovereignai.ui.widgets.suggestion_box import SuggestionBox, CommandItem
def _build_banner(mode: str = "local") -> str:
    lines = [
        r"[bold #5FA8D3]██████╗  █████╗ ███████╗████████╗██╗ ██████╗  ███╗   ██╗[/]",
        r"[bold #4a90b8]██╔══██╗██╔══██╗██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║[/]",
        r"[bold #3d7da0]██████╔╝███████║███████╗   ██║   ██║██║   ██║██╔██╗ ██║[/]",
        r"[bold #306988]██╔══██╗██╔══██║╚════██║   ██║   ██║██║   ██║██║╚██╗██║[/]",
        r"[bold #2E5A7A]██████╔╝██║  ██║███████║   ██║   ██║╚██████╔╝██║ ╚████║[/]",
        r"[bold #2E5A7A]╚═════╝ ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝[/]",
        "",
        "[dim]            B A S T I O N   A I[/]",
    ]
    return "\n".join(lines)

@dataclass
class GPUInfo:
    name: str
    used_mb: float
    total_mb: float
    vram_pct: int
    gpu_util: float


def query_gpu() -> GPUInfo | None:
    """Query primary GPU metrics via nvidia-smi with CREATE_NO_WINDOW."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        flags = 0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
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
        if res.returncode == 0 and res.stdout.strip():
            line = res.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                raw_name = parts[0].replace("NVIDIA GeForce ", "").replace("NVIDIA ", "")
                used_mb = float(parts[1])
                total_mb = float(parts[2])
                gpu_util = float(parts[3])
                vram_pct = int(used_mb / total_mb * 100) if total_mb > 0 else 0
                return GPUInfo(
                    name=raw_name,
                    used_mb=used_mb,
                    total_mb=total_mb,
                    vram_pct=vram_pct,
                    gpu_util=gpu_util,
                )
    except Exception:
        pass
    return None


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
    InfoPanel .dim-val    { color: #445566; padding-left: 1; }
    InfoPanel .gpu-active { color: #44bb88; text-style: bold; padding-left: 1; }
    InfoPanel .gpu-high   { color: #D9A441; text-style: bold; padding-left: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Static("Session", classes="ph")
        yield Static("—", id="si-session-id", classes="pv")
        yield Static("Context", classes="ph")
        yield Static("0 tokens · 0% used", id="si-tokens", classes="pv")
        yield Static("$0.00 spent (fully local)", classes="dim-val")
        yield Static("Model", classes="ph")
        yield Static("AUTO", id="si-model", classes="pv")
        yield Static("GPU", classes="ph")
        yield Static("Detecting…", id="si-gpu-name", classes="pv")
        yield Static("0% util · 0.0/0.0 GB", id="si-gpu-stat", classes="gpu-active")

    def refresh_all(self, session_id: str, tokens: int, tool_calls: int,
                    model: str, external: int = 0, gpu_info: GPUInfo | None = None) -> None:
        self._set("#si-session-id", session_id[:20] + ("…" if len(session_id) > 20 else ""))
        pct = min(int(tokens / 8192 * 100), 100)
        self._set("#si-tokens", f"{tokens:,} tokens · {pct}% used")
        self._set("#si-model", model)

        # Real-time GPU stats
        if gpu_info:
            self._set("#si-gpu-name", gpu_info.name[:24])
            used_gb = gpu_info.used_mb / 1024.0
            total_gb = gpu_info.total_mb / 1024.0
            gpu_stat = self.query_one("#si-gpu-stat", Static)
            if gpu_info.vram_pct > 85:
                gpu_stat.set_classes("gpu-high")
            else:
                gpu_stat.set_classes("gpu-active")
            gpu_stat.update(f"{int(gpu_info.gpu_util)}% util · {used_gb:.1f}/{total_gb:.1f} GB ({gpu_info.vram_pct}%)")
        else:
            self._set("#si-gpu-name", "CPU / Integrated")
            self._set("#si-gpu-stat", "Local inference")

    def _set(self, selector: str, text: str) -> None:
        try:
            self.query_one(selector, Static).update(text)
        except Exception:
            pass


class ChatInput(Input):
    """
    Input box that routes navigation keys (up, down, tab, escape) to the
    OpenCode-style suggestion popup when active.
    """
    _skip_next_change: bool = False

    def on_key(self, event: events.Key) -> None:
        try:
            sugg = self.screen.query_one("#suggestion-box", SuggestionBox)
        except Exception:
            return

        if sugg.is_active:
            if event.key == "up":
                sugg.select_prev()
                event.prevent_default()
                event.stop()
                return
            elif event.key == "down":
                sugg.select_next()
                event.prevent_default()
                event.stop()
                return
            elif event.key == "escape":
                sugg.hide()
                event.prevent_default()
                event.stop()
                return
            elif event.key == "tab":
                selected = sugg.get_selected()
                if selected:
                    cmd_to_insert = selected.alias_of or selected.cmd
                    self._skip_next_change = True
                    if selected.takes_args:
                        self.value = f"{cmd_to_insert} "
                    else:
                        self.value = cmd_to_insert
                    self.cursor_position = len(self.value)
                    sugg.hide()
                event.prevent_default()
                event.stop()
                return


class MainScreen(Screen):
    """Primary SovereignAI screen."""

    BINDINGS = [
        ("ctrl+p",  "command_palette", "Commands"),
        ("escape",  "interrupt",       "Interrupt"),
        ("ctrl+n",  "new_session",     "New"),
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

    def __init__(self, session, workspace: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._session = session
        self._workspace = workspace
        os.environ["SOVAI_WORKSPACE"] = str(workspace)
        self._model_override: str | None = None
        self._is_generating = False

    def compose(self) -> ComposeResult:
        with Container(id="body"):
            with Vertical(id="chat-column"):
                yield ChatThread(id="chat-thread")
                with Vertical(id="input-zone"):
                    yield Static("", id="thinking-bar")
                    yield SuggestionBox(id="suggestion-box")
                    yield ChatInput(
                        placeholder='Ask anything… or type / for suggestions',
                        id="input-box",
                    )
                    yield Static(
                        f"AUTO  ·  📁 {self._workspace}",
                        id="meta-bar",
                    )
            yield InfoPanel(id="info-panel")
        yield StatusBar(id="status-bar")

    async def on_mount(self) -> None:
        chat = self.query_one("#chat-thread", ChatThread)
        await chat.add_system_message(_build_banner())

        # Periodic UI refresh (GPU, session, tokens)
        self.set_interval(1.0, self._periodic_refresh)

        # Update info panel
        info = self.query_one("#info-panel", InfoPanel)
        info.refresh_all(
            session_id=self._session.id,
            tokens=0, tool_calls=0,
            model=self._mode_badge(),
            gpu_info=query_gpu(),
        )

        # Focus input
        self.query_one("#input-box", Input).focus()

    @work(thread=True)
    def _periodic_refresh(self) -> None:
        gpu_info = query_gpu()
        self.app.call_from_thread(self._update_info_panel, gpu_info)

    def _update_info_panel(self, gpu_info: GPUInfo | None) -> None:
        try:
            info = self.query_one("#info-panel", InfoPanel)
            info.refresh_all(
                session_id=self._session.id,
                tokens=self._session.total_tokens,
                tool_calls=self._session.tool_calls_made,
                model=self._mode_badge(),
                gpu_info=gpu_info,
            )
        except Exception:
            pass

    def _mode_badge(self) -> str:
        if self._model_override and self._model_override != "AUTO":
            return self._model_override
        return "AUTO"

    # ── Input handling ─────────────────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "input-box":
            return
        if getattr(event.input, "_skip_next_change", False):
            event.input._skip_next_change = False
            return
        val = event.value
        try:
            sugg = self.query_one("#suggestion-box", SuggestionBox)
            if val.startswith("/"):
                sugg.update_query(val)
            else:
                sugg.hide()
        except Exception:
            pass

    def on_suggestion_box_selected(self, event: SuggestionBox.Selected) -> None:
        input_box = self.query_one("#input-box", Input)
        cmd = event.item.alias_of or event.item.cmd
        if event.auto_run:
            input_box.clear()
            self.run_worker(self._handle_slash(cmd))
        else:
            input_box.value = f"{cmd} "
            input_box.cursor_position = len(input_box.value)
            input_box.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()

        # If suggestion box is active and user pressed Enter, process highlighted suggestion
        try:
            sugg = self.query_one("#suggestion-box", SuggestionBox)
            if sugg.is_active:
                selected = sugg.get_selected()
                sugg.hide()
                if selected:
                    cmd = selected.alias_of or selected.cmd
                    if selected.takes_args and text == selected.cmd:
                        event.input.value = f"{cmd} "
                        event.input.cursor_position = len(event.input.value)
                        return
                    elif not selected.takes_args and text == selected.cmd:
                        event.input.clear()
                        self.run_worker(self._handle_slash(cmd))
                        return
        except Exception:
            pass

        if not text:
            return
        if text.lower() in ("/exit", "/quit"):
            self.app.exit()
            return
        if self._is_generating:
            self.notify("Generation in progress — press ESC to interrupt.")
            return
        event.input.clear()

        if text.startswith("/"):
            self.run_worker(self._handle_slash(text))
        else:
            self._run_turn(text)

    async def _handle_slash(self, cmd: str) -> None:
        parts = cmd.split()
        head = parts[0].lower()
        chat = self.query_one("#chat-thread", ChatThread)

        if head in ("/exit", "/quit"):
            self.app.exit()
            return
        elif head == "/models":
            await self._open_model_palette()
        elif head == "/auto":
            self._model_override = None
            self._update_meta()
            await chat.add_system_message("Switched to AUTO model selection.", "info")
        elif head in ("/agents", "/role"):
            if len(parts) > 1:
                target_role = parts[1].lower()
                if target_role in ("admin", "tech", "finance", "support", "guest"):
                    self._session.user_role = target_role
                    self.app.user_role = target_role
                    os.environ["SOVAI_ROLE"] = target_role
                    await chat.add_system_message(f"Active role switched to [bold]{target_role}[/].", "info")
                else:
                    await chat.add_system_message(f"Invalid role: {target_role}. Options: admin | tech | finance | support", "warning")
            else:
                cur_role = getattr(self._session, "user_role", "admin")
                await chat.add_system_message(
                    f"Current role: [bold]{cur_role}[/]\nUsage: /agents <admin | tech | finance | support>",
                    "info",
                )
        elif head == "/diff":
            try:
                import subprocess
                flags = 0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                res = subprocess.run(
                    ["git", "diff", "--stat"],
                    cwd=str(self._workspace),
                    capture_output=True,
                    text=True,
                    timeout=3,
                    creationflags=flags,
                )
                st = subprocess.run(
                    ["git", "status", "--short"],
                    cwd=str(self._workspace),
                    capture_output=True,
                    text=True,
                    timeout=3,
                    creationflags=flags,
                )
                status_out = st.stdout.strip()
                diff_out = res.stdout.strip()
                if not status_out and not diff_out:
                    await chat.add_system_message("Working tree clean — no uncommitted changes.", "info")
                else:
                    msg_lines = ["[bold]Git Status & Diff:[/bold]"]
                    if status_out:
                        msg_lines.append(f"[yellow]{status_out}[/yellow]")
                    if diff_out:
                        msg_lines.append(f"\n{diff_out}")
                    await chat.add_system_message("\n".join(msg_lines), "info")
            except Exception as e:
                await chat.add_system_message(f"Error checking git diff: {e}", "error")
        elif head == "/editor":
            editor = os.environ.get("EDITOR") or "code"
            try:
                import subprocess
                flags = 0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                subprocess.Popen([editor, str(self._workspace)], creationflags=flags)
                await chat.add_system_message(f"Opened workspace in {editor}.", "info")
            except Exception as e:
                await chat.add_system_message(f"Could not open editor ({editor}): {e}", "warning")
        elif head == "/init":
            agents_md = self._workspace / "AGENTS.md"
            if agents_md.exists():
                await chat.add_system_message(f"AGENTS.md is already configured in {self._workspace}.", "info")
            else:
                template = (
                    "# AGENTS.md — Project Instructions for Bastion\n\n"
                    "## Project Context\n"
                    f"- Workspace: {self._workspace.name}\n"
                    "- Goal: Enterprise Sovereign AI development and document synthesis\n\n"
                    "## Development Guidelines\n"
                    "- Keep all operations local and audited.\n"
                    "- Follow least-privilege role boundaries.\n"
                )
                agents_md.write_text(template, encoding="utf-8")
                await chat.add_system_message(f"Created guided AGENTS.md in {self._workspace}.", "info")
        elif head == "/net":
            from sovereignai.ui.screens.net_monitor_screen import NetMonitorScreen
            self.app.push_screen(NetMonitorScreen())
        elif head in ("/new",):
            await self.app.action_new_session()
        elif head == "/sessions":
            from sovereignai.ui.screens.session_browser import SessionBrowser
            self.app.push_screen(SessionBrowser())
        elif head in ("/cwd", "/move") and len(parts) > 1:
            p = Path(" ".join(parts[1:])).expanduser().resolve()
            if p.is_dir():
                self._workspace = p
                os.environ["SOVAI_WORKSPACE"] = str(p)
                self._update_meta()
                await chat.add_system_message(f"Workspace → {p}", "info")
            else:
                await chat.add_system_message(f"Not a directory: {p}", "error")
        elif head == "/attach" and len(parts) > 1:
            src = Path(" ".join(parts[1:])).expanduser().resolve()
            if not src.exists():
                await chat.add_system_message(f"File not found: {src}", "error")
            else:
                import shutil as _shutil
                dest = self._workspace / src.name
                _shutil.copy2(src, dest)
                await chat.add_system_message(f"📎 Attached {src.name} — reference it in your next message.", "info")
        elif head == "/kb":
            await self._handle_kb(parts)
        elif head == "/help":
            await chat.add_system_message(
                "[bold #5FA8D3]Bastion Sovereign AI Commands:[/bold #5FA8D3]\n"
                "  /models       Switch active model (Auto / Qwen / Coder / Vision)\n"
                "  /auto         Switch to AUTO router\n"
                "  /agents       Switch role (admin | tech | finance | support)\n"
                "  /diff         View git diff & file changes\n"
                "  /editor       Open workspace in editor\n"
                "  /net          Toggle live network security monitor\n"
                "  /kb           Knowledge base (status | add <path>)\n"
                "  /cwd, /move   Change workspace directory\n"
                "  /attach       Attach file to workspace\n"
                "  /init         Initialize AGENTS.md configuration\n"
                "  /new          Start a new session\n"
                "  /sessions     Browse past sessions\n"
                "  /exit         Exit the app\n"
                "\n[dim]Keys: tab (complete) · esc (close/interrupt) · ctrl+p (palette) · ctrl+n (new)[/dim]",
                "info",
            )
        else:
            await chat.add_system_message(f"Unknown: {cmd}  →  type /help for suggestions", "warning")

    async def _handle_kb(self, parts: list[str]) -> None:
        chat = self.query_one("#chat-thread", ChatThread)
        sub = parts[1] if len(parts) > 1 else "status"
        if sub == "status":
            try:
                from sovereignai.knowledge_base.store import get_store
                s = get_store().stats()
                await chat.add_system_message(
                    f"📚 KB: {s['documents']} docs · {s['chunks']} chunks · {s['disk_mb']:.1f} MB",
                    "info",
                )
            except Exception as e:
                await chat.add_system_message(f"KB error: {e}", "error")
        elif sub == "add" and len(parts) > 2:
            p = Path(" ".join(parts[2:])).expanduser().resolve()
            await chat.add_system_message(f"Ingesting {p} …", "info")
            try:
                from sovereignai.knowledge_base.ingest import ingest_path
                stats = ingest_path(p, verbose=False)
                await chat.add_system_message(
                    f"✅ {stats['docs']} docs, {stats['chunks']} chunks ingested.", "info"
                )
            except Exception as e:
                await chat.add_system_message(f"KB error: {e}", "error")
        else:
            await chat.add_system_message("Usage: /kb status | /kb add <path>", "info")

    async def _open_model_palette(self) -> None:
        from sovereignai.ui.screens.model_palette import ModelPalette

        async def on_select(model: str | None) -> None:
            if model is None:
                return
            if model.startswith("/"):
                # Command shortcut from palette
                self.app.call_later(self._handle_slash, model)
                return
            self._model_override = None if model == "AUTO" else model
            self._update_meta()
            chat = self.query_one("#chat-thread", ChatThread)
            if model == "AUTO":
                await chat.add_system_message("Switched to AUTO model selection.", "info")
            else:
                await chat.add_system_message(f"Active model switched to [bold]{model}[/].", "info")

        await self.app.push_screen(ModelPalette(current_model=self._mode_badge()), on_select)

    def _update_meta(self) -> None:
        badge = self._mode_badge()
        try:
            self.query_one("#meta-bar", Static).update(
                f"{badge}  ·  📁 {self._workspace}"
            )
            self.query_one("#status-bar", StatusBar).set_model(badge, badge)
        except Exception:
            pass

    # ── Agent loop (threaded) ──────────────────────────────────────────────

    @work(exclusive=True)
    async def _run_turn(self, user_text: str) -> None:
        chat = self.query_one("#chat-thread", ChatThread)
        status = self.query_one("#status-bar", StatusBar)
        thinking = self.query_one("#thinking-bar", Static)
        input_box = self.query_one("#input-box", Input)

        self._is_generating = True
        self._session.cancelled = False
        start_time = time.time()

        input_box.placeholder = "Generating… press Esc to interrupt"

        await chat.add_user_message(user_text)
        chat.reset_turn_state()
        await chat.show_loading("Thinking…")
        thinking.update("⏳ Routing task…")

        # Queue for thread → async event communication
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _producer() -> None:
            """Runs in background thread — calls blocking Ollama API."""
            try:
                for evt in run_agent_turn(
                    self._session, user_text,
                    model_override=self._model_override,
                ):
                    if getattr(self._session, "cancelled", False):
                        break
                    loop.call_soon_threadsafe(queue.put_nowait, evt)
            except Exception as e:
                loop.call_soon_threadsafe(
                    queue.put_nowait, {"kind": "error", "message": str(e)}
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=_producer, daemon=True).start()

        # Consume events as they arrive — UI stays responsive
        try:
            while True:
                evt = await queue.get()
                if evt is None:
                    break
                await self._handle_event(evt, chat, status, thinking, start_time)
                await asyncio.sleep(0)  # yield to UI
        except Exception as e:
            await chat.add_system_message(f"Error: {e}", "error")
        finally:
            self._is_generating = False
            thinking.update("")
            await chat.remove_loading()
            input_box.placeholder = "Ask anything… or type /help for commands"
            input_box.focus()
            elapsed = time.time() - start_time
            status.set_elapsed(elapsed)

    async def _handle_event(
        self, evt: dict,
        chat: ChatThread,
        status: StatusBar,
        thinking: Static,
        start_time: float,
    ) -> None:
        kind = evt.get("kind", "")

        if kind == "routing_decision":
            thinking.update(f"→ routing to {evt['category']} ({evt['model_name']})…")
            await chat.add_routing_line(
                category=evt["category"],
                model=evt["model_name"],
                confidence=evt["confidence"],
                reason=evt.get("reason", ""),
                uncertain=evt.get("uncertain", False),
            )
            chat.set_loading_status(f"Thinking with {evt['model_name']}…")
            model_str = f"AUTO → {evt['model_name']}"
            status.set_model("AUTO", model_str)

        elif kind == "stream_chunk":
            await chat.stream_chunk(evt["chunk"])

        elif kind == "tool_call_start":
            # Collapse current live text into a thought block
            await chat.finalize_stream_as_thought()
            name = evt["name"]
            thinking.update(f"🔧 {name}…")
            call_id = f"{name}_{evt.get('step', 0)}"
            await chat.add_tool_call_block(call_id, name, evt.get("args", {}))
            await chat.show_loading(f"Running {name}…")

        elif kind == "tool_call_result":
            name = evt["name"]
            call_id = f"{name}_{evt.get('step', 0)}"
            chat.finish_tool_call(call_id, evt["result"])
            thinking.update("💭 Thinking…")
            await chat.show_loading("Processing tool result…")

        elif kind == "done":
            await chat.remove_loading()
            # Finalize the last stream as the answer
            await chat.finalize_stream_as_answer(fallback_text=evt.get("text", ""))
            thinking.update("")
            status.set_elapsed(time.time() - start_time)

        elif kind == "error":
            await chat.remove_loading()
            await chat.add_system_message(f"❌ {evt.get('message', '?')}", "error")

        elif kind == "max_iterations_reached":
            await chat.remove_loading()
            await chat.finalize_stream_as_answer(fallback_text=evt.get("text", ""))
            await chat.add_system_message("⚠ Reached max iterations.", "warning")

        elif kind == "interrupted":
            await chat.remove_loading()
            await chat.add_system_message("⛔ Interrupted.", "warning")

    # ── Actions ────────────────────────────────────────────────────────────

    def action_command_palette(self) -> None:
        from sovereignai.ui.screens.command_palette import CommandPalette

        def on_cmd(cmd: str | None) -> None:
            if cmd:
                self.app.call_later(self._handle_slash, cmd)

        self.app.push_screen(CommandPalette(), on_cmd)

    def action_interrupt(self) -> None:
        if self._is_generating:
            self._session.cancelled = True
            try:
                self.query_one("#thinking-bar", Static).update("⛔ Interrupting…")
            except Exception:
                pass
        else:
            self.app.bell()

    async def action_new_session(self) -> None:
        await self.app.action_new_session()
