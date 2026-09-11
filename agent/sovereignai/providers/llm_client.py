"""
llm_client.py — Unified chat-completion client for Bastion.

All inference goes through the OpenAI API (gpt-4o-mini by default).
Display names shown in the TUI (Qwen3.5-9B etc.) are cosmetic labels
that match the website's sovereign model naming — the real API model
underneath is always gpt-4o-mini unless the config says otherwise.

Router and all worker models use the same OpenAI client.
No Ollama dependency.
"""
from __future__ import annotations

import os
import json
from typing import NamedTuple, Generator

from openai import OpenAI

from sovereignai.config import get_config


# ── Display name mapping ──────────────────────────────────────────────────────
# Maps category or model ID to the sovereign label shown in the TUI (Qwen3.5-9B etc.)

_DISPLAY_NAMES: dict[str, str] = {
    "general":          "Qwen3.5-9B",
    "coding":           "Qwen3-Coder-Next",
    "vision":           "Qwen3-VL-32B",
    "document_qa":      "Qwen3.5-9B",
    "spreadsheet":      "Qwen3.5-9B",
    "planning":         "Qwen3.5-9B",
    "gpt-4o-mini":      "Qwen3.5-9B",
    "gpt-4o":           "Qwen3.6-27B",
    "gpt-4-turbo":      "Qwen3-Coder-Next",
}


def display_name_for_category(category: str) -> str:
    """Return sovereign display name for a specific task category."""
    cfg = get_config()
    node = cfg._raw.get("models", {}).get(category, {})
    if node.get("display_name"):
        return node["display_name"]
    return _DISPLAY_NAMES.get(category, "Qwen3.5-9B")


def display_name_for(model_id: str) -> str:
    """Return the sovereign display name for a given model ID or category."""
    if not model_id:
        return "Qwen3.5-9B"
    if model_id.startswith("Qwen"):
        return model_id
    if model_id in _DISPLAY_NAMES:
        return _DISPLAY_NAMES[model_id]
    cfg = get_config()
    # Try config-level display_name
    for cat in ["general", "coding", "vision", "document_qa", "spreadsheet", "planning"]:
        node = cfg._raw.get("models", {}).get(cat, {})
        if node.get("display_name") and (node.get("api") == model_id or cat == model_id):
            return node["display_name"]
    return _DISPLAY_NAMES.get(model_id, "Qwen3.5-9B")


def resolve_real_model(model_or_display: str) -> str:
    """Map any sovereign display name or category to the underlying API model ID."""
    if not model_or_display:
        return "gpt-4o-mini"
    # If already a standard API model ID
    if model_or_display.startswith("gpt-") or model_or_display.startswith("o1") or model_or_display.startswith("o3"):
        return model_or_display
    cfg = get_config()
    # If category name
    if model_or_display in ("general", "coding", "vision", "document_qa", "spreadsheet", "planning"):
        node = cfg._raw.get("models", {}).get(model_or_display, {})
        return node.get("api") or node.get("model", "gpt-4o-mini")
    # If sovereign display name
    for cat in ["general", "coding", "vision", "document_qa", "spreadsheet", "planning"]:
        node = cfg._raw.get("models", {}).get(cat, {})
        if node.get("display_name") == model_or_display:
            return node.get("api") or node.get("model", "gpt-4o-mini")
    return "gpt-4o-mini"


# ── Data types ────────────────────────────────────────────────────────────────

class ChatResult(NamedTuple):
    content: str
    model: str           # real model ID (gpt-4o-mini etc.)
    display_name: str    # sovereign display label (Qwen3.5-9B etc.)
    provider: str        # "local" shown to user


class StreamChunk(NamedTuple):
    content: str = ""
    thinking: str = ""
    tool_calls: list[dict] | None = None  # [{id, name, arguments}, ...]
    done: bool = False


# ── LLM Client ───────────────────────────────────────────────────────────────

class LLMClient:
    """Routes chat() calls to OpenAI API. No local Ollama dependency."""

    def __init__(self) -> None:
        self._cfg = get_config()

    @property
    def mode(self) -> str:
        return "api"  # always api — no local mode in Bastion

    def _get_client(self) -> OpenAI:
        api_key = os.environ.get(self._cfg.provider_api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"OPENAI_API_KEY is not set. "
                f"Add it to agent/.env or export it in your shell."
            )
        return OpenAI(
            api_key=api_key,
            base_url=self._cfg.provider_base_url,
            timeout=self._cfg.provider_request_timeout_s,
        )

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        keep_alive: str | None = None,  # ignored — kept for API compat
        force_local: bool = False,       # ignored — no local mode
    ) -> ChatResult:
        """Non-streaming chat completion."""
        client = self._get_client()
        real_model = resolve_real_model(model)
        kwargs: dict = {"model": real_model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        resp = client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        return ChatResult(
            content=content,
            model=real_model,
            display_name=display_name_for(model),
            provider="local",
        )

    def chat_stream(
        self,
        model: str,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        num_ctx: int | None = None,      # ignored — kept for API compat
        tool_choice: str | dict | None = None,
    ) -> "Generator[StreamChunk, None, None]":
        """Streaming chat completion with optional native tool-calling."""
        yield from self._chat_stream_openai(model, messages, tools, tool_choice)

    def chat_vision(self, model: str, prompt: str, image_b64_list: list[str]) -> ChatResult:
        """Vision call — passes images as base64 data-URLs."""
        content: list[dict] = [{"type": "text", "text": prompt}]
        for b64 in image_b64_list:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })
        return self.chat(model, [{"role": "user", "content": content}], temperature=0.2)

    def embed(self, text: str) -> list[float]:
        """Generate an embedding using OpenAI text-embedding-3-small."""
        client = self._get_client()
        embedding_model = self._cfg.embedding_model  # text-embedding-3-small
        resp = client.embeddings.create(model=embedding_model, input=text)
        return resp.data[0].embedding

    # ── internal streaming ────────────────────────────────────────────────────

    def _chat_stream_openai(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None,
        tool_choice: str | dict | None,
    ) -> "Generator[StreamChunk, None, None]":
        client = self._get_client()
        real_model = resolve_real_model(model)
        kwargs: dict = {
            "model": real_model,
            "messages": messages,
            "stream": True,
            "temperature": 0,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        # Accumulate streamed tool-call fragments (OpenAI sends them incrementally)
        tool_call_acc: dict[int, dict] = {}

        with client.chat.completions.create(**kwargs) as stream:
            for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    continue
                delta = choice.delta

                content = delta.content or ""
                if content:
                    yield StreamChunk(content=content)

                for tc_delta in (delta.tool_calls or []):
                    idx = tc_delta.index
                    entry = tool_call_acc.setdefault(
                        idx, {"id": None, "name": None, "arguments": ""}
                    )
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    fn = tc_delta.function
                    if fn:
                        if fn.name:
                            entry["name"] = fn.name
                        if fn.arguments:
                            entry["arguments"] += fn.arguments

                if choice.finish_reason and tool_call_acc:
                    finalized = []
                    for entry in tool_call_acc.values():
                        try:
                            args = json.loads(entry["arguments"] or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        finalized.append(
                            {"id": entry["id"], "name": entry["name"], "arguments": args}
                        )
                    yield StreamChunk(tool_calls=finalized)
                    tool_call_acc = {}

        yield StreamChunk(done=True)


# ── Singleton ────────────────────────────────────────────────────────────────

_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def reset_llm_client() -> None:
    """Call after reload_config() so provider changes take effect."""
    global _llm_client
    _llm_client = None
