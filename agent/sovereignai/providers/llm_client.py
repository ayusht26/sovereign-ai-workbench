"""
llm_client.py — Unified chat-completion client.

Router, agent_loop, and any tool that calls a model should go through
get_llm_client().chat(...) instead of touching `ollama` directly. This
is the single seam between "local" (Ollama, air-gapped) and "api"
(OpenRouter or any OpenAI-compatible endpoint) — everything above this
layer is provider-agnostic.

Provider mode is set by the administrator in config (provider.mode),
never hardcoded and never chosen by the agent itself.
"""
from __future__ import annotations

import os
from typing import NamedTuple
import json
import httpx
import ollama

from sovereignai.config import get_config
from typing import Generator

class ChatResult(NamedTuple):
    content: str
    model: str
    provider: str  # "local" | "api"

class StreamChunk(NamedTuple):
    content: str = ""
    thinking: str = ""
    tool_calls: list[dict] | None = None   # [{"name": str, "arguments": dict}, ...]
    done: bool = False

class LLMClient:
    """Routes chat() calls to Ollama (local) or an OpenAI-compatible API (api mode)."""

    def __init__(self) -> None:
        self._cfg = get_config()

    @property
    def mode(self) -> str:
        return self._cfg.provider_mode  # "local" | "api"

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        keep_alive: str | None = None,
        force_local: bool = False,
    ) -> ChatResult:
        """
        force_local=True bypasses provider.mode entirely and always hits
        Ollama — use this for the router model, which should never leave
        the machine even when category models are running via API.
        """
        if not force_local and self.mode == "api":
            return self._chat_api(model, messages, temperature, max_tokens)
        return self._chat_local(model, messages, temperature, max_tokens, keep_alive)
    
    def chat_stream(
        self,
        model: str,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        num_ctx: int | None = None,
    ) -> "Generator[StreamChunk, None, None]":
        if self.mode == "api":
            yield from self._chat_stream_api(model, messages)
        else:
            yield from self._chat_stream_local(model, messages, tools, num_ctx)

    # ── local streaming (Ollama, native tool-calling) ───────────────────
    def _chat_stream_local(self, model, messages, tools, num_ctx):
        client = ollama.Client(host=self._cfg.ollama_host)
        options = {}
        if num_ctx is not None:
            options["num_ctx"] = num_ctx
        stream = client.chat(model=model, messages=messages, tools=tools, stream=True, options=options)
        for chunk in stream:
            msg = chunk.message if hasattr(chunk, "message") else (chunk.get("message", {}) if isinstance(chunk, dict) else {})
            content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
            thinking = getattr(msg, "thinking", "") if not isinstance(msg, dict) else msg.get("thinking", "")
            raw_calls = getattr(msg, "tool_calls", None) if not isinstance(msg, dict) else msg.get("tool_calls")
            tool_calls = []
            for tc in (raw_calls or []):
                fn = tc.function if hasattr(tc, "function") else tc.get("function", {})
                name = getattr(fn, "name", None) if not isinstance(fn, dict) else fn.get("name")
                args = getattr(fn, "arguments", None) if not isinstance(fn, dict) else fn.get("arguments")
                tool_calls.append({"name": name, "arguments": args or {}})
            yield StreamChunk(content=content or "", thinking=thinking or "", tool_calls=tool_calls or None)
        yield StreamChunk(done=True)

    # ── api streaming (OpenRouter SSE, prompt-based tool calls only) ────
    def _chat_stream_api(self, model, messages):
        cfg = self._cfg
        api_key = os.environ.get(cfg.provider_api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"provider.mode is 'api' but ${cfg.provider_api_key_env} is not set."
            )
        payload = {"model": model, "messages": messages, "stream": True}
        with httpx.Client(timeout=self._cfg.ollama_timeout) as client:
            with client.stream(
                "POST",
                f"{cfg.provider_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": cfg.provider_app_url or "https://sovereignai.local",
                    "X-Title": "SovereignAI",
                },
                json=payload,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = (data.get("choices") or [{}])[0].get("delta", {})
                    content = delta.get("content") or ""
                    if content:
                        yield StreamChunk(content=content)
        yield StreamChunk(done=True)

    # ── local (Ollama) ──────────────────────────────────────────────────
    def _chat_local(self, model, messages, temperature, max_tokens, keep_alive) -> ChatResult:
        client = ollama.Client(host=self._cfg.ollama_host)
        options = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        response = client.chat(
            model=model,
            messages=messages,
            options=options,
            keep_alive=keep_alive if keep_alive is not None else "-1",
        )
        return ChatResult(content=response.message.content or "", model=model, provider="local")

    # ── api (OpenRouter / OpenAI-compatible) ────────────────────────────
    def _chat_api(self, model, messages, temperature, max_tokens) -> ChatResult:
        cfg = self._cfg
        api_key = os.environ.get(cfg.provider_api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"provider.mode is 'api' but ${cfg.provider_api_key_env} is not set. "
                f"Export it, or switch provider.mode back to 'local' in "
                f"~/.sovereignai/config.yaml."
            )
        payload: dict = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        with httpx.Client(timeout=self._cfg.ollama_timeout) as client:
            resp = client.post(
                f"{cfg.provider_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": cfg.provider_app_url or "https://sovereignai.local",
                    "X-Title": "SovereignAI",
                },
                json=payload,
            )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"] or ""
        return ChatResult(content=content, model=model, provider="api")


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def reset_llm_client() -> None:
    """Call this after reload_config() so a provider-mode switch takes effect."""
    global _llm_client
    _llm_client = None