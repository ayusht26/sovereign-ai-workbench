"""
session.py — Session state, conversation history, token accounting.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Message:
    role: str          # "user" | "assistant" | "tool" | "system"
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    timestamp: float = field(default_factory=time.time)
    token_count: int = 0


@dataclass
class UIEvent:
    kind: str          # "routing_decision" | "tool_call_start" | "tool_call_result"
                       # "stream_chunk" | "max_iterations_reached" | "error"
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class Session:
    """Holds the full state of one user conversation."""

    def __init__(self, session_id: str | None = None, workspace: str = ".") -> None:
        self.id: str = session_id or str(uuid.uuid4())
        self.workspace: str = workspace
        self.messages: list[Message] = []
        self.total_tokens: int = 0
        self.started_at: float = time.time()
        self._ui_callbacks: list[Callable[[UIEvent], None]] = []

        # Statistics
        self.tool_calls_made: int = 0
        self.egress_attempts: int = 0  # should always be 0

    # ── Message management ─────────────────────────────────────────────────

    def append(
        self,
        role: str,
        content: str,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
        token_count: int = 0,
    ) -> None:
        msg = Message(
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            token_count=token_count,
        )
        self.messages.append(msg)
        self.total_tokens += token_count

    def messages_for_model(self) -> list[dict[str, Any]]:
        """Convert session messages to Ollama-compatible format."""
        result = []
        for m in self.messages:
            d: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.tool_call_id:
                d["tool_call_id"] = m.tool_call_id
            if m.tool_name:
                d["name"] = m.tool_name
            result.append(d)
        return result

    def get_context_summary(self) -> dict[str, Any]:
        """Summary for the right-hand panel."""
        elapsed = time.time() - self.started_at
        return {
            "session_id": self.id,
            "total_tokens": self.total_tokens,
            "message_count": len(self.messages),
            "elapsed_s": elapsed,
            "tool_calls_made": self.tool_calls_made,
            "egress_attempts": self.egress_attempts,
            "workspace": self.workspace,
        }

    # ── UI event bus ───────────────────────────────────────────────────────

    def add_ui_listener(self, callback: Callable[[UIEvent], None]) -> None:
        self._ui_callbacks.append(callback)

    def emit_ui_event(self, kind: str, **data: Any) -> None:
        event = UIEvent(kind=kind, data=data)
        for cb in self._ui_callbacks:
            try:
                cb(event)
            except Exception:
                pass  # UI callbacks must never crash the agent loop

    def stream_to_ui(self, chunk: str) -> None:
        self.emit_ui_event("stream_chunk", chunk=chunk)

