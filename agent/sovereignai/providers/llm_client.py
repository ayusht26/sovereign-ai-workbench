"""
llm_client.py — Unified chat-completion client.

Router, agent_loop, and any tool that calls a model should go through
get_llm_client().chat(...) instead of touching `ollama` directly. This
is the single seam between "local" (Ollama, air-gapped) and "api"
(OpenRouter or any OpenAI-compatible endpoint) — everything above this
layer is provider-agnostic.

API mode uses NATIVE tool-calling (payload["tools"], provider.require_
parameters=True) rather than prompt-based JSON extraction — empirically
confirmed more reliable across OpenRouter's provider fan-out than asking
models to emit JSON in plain text. Text-based extraction in agent_loop.py
is kept as a defensive fallback only, not the primary path.

Provider mode is set by the administrator in config (provider.mode),
never hardcoded and never chosen by the agent itself.
"""
from __future__ import annotations

import os
import json
from typing import NamedTuple, Generator

import httpx
import ollama

from sovereignai.config import get_config


class ChatResult(NamedTuple):
    content: str
    model: str
    provider: str  # "local" | "api"


class StreamChunk(NamedTuple):
    content: str = ""
    thinking: str = ""
    tool_calls: list[dict] | None = None   # [{"id": str|None, "name": str, "arguments": dict}, ...]
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
            yield from self._chat_stream_api(model, messages, tools)
        else:
            yield from self._chat_stream_local(model, messages, tools, num_ctx)

    def chat_vision(self, model: str, prompt: str, image_b64_list: list[str]) -> ChatResult:
        if self.mode == "api":
            content = [{"type": "text", "text": prompt}]
            for b64 in image_b64_list:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
            return self._chat_api(model, [{"role": "user", "content": content}], temperature=0.2, max_tokens=None)
        else:
            return self._chat_local(model, [{"role": "user", "content": prompt, "images": image_b64_list}],
                                     temperature=0.2, max_tokens=None, keep_alive=None)

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
                call_id = getattr(tc, "id", None) if not isinstance(tc, dict) else tc.get("id")
                tool_calls.append({"id": call_id, "name": name, "arguments": args or {}})
            yield StreamChunk(content=content or "", thinking=thinking or "", tool_calls=tool_calls or None)
        yield StreamChunk(done=True)

    # ── api streaming (OpenRouter SSE, NATIVE tool-calling) ─────────────
    def _chat_stream_api(self, model, messages, tools=None):
        cfg = self._cfg
        api_key = os.environ.get(cfg.provider_api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"provider.mode is 'api' but ${cfg.provider_api_key_env} is not set."
            )
        payload = {"model": model, "messages": messages, "stream": True, "temperature": 0}
        if tools:
            payload["tools"] = tools

        # require_parameters=True restricts routing to providers that actually
        # support the requested params (here: native tool-calling) — confirmed
        # empirically far more reliable than letting the model guess a text format.
        provider_prefs = dict(cfg.provider_routing or {})
        if tools:
            provider_prefs.setdefault("require_parameters", True)
        if provider_prefs:
            payload["provider"] = provider_prefs

        # Accumulate streamed tool-call fragments by index — OpenAI-style
        # streaming sends the function name and arguments incrementally
        # across multiple deltas, not as one atomic block like Ollama does.
        tool_call_acc: dict[int, dict] = {}

        with httpx.Client(timeout=cfg.provider_request_timeout_s) as client:
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

                    choice = (data.get("choices") or [{}])[0]
                    delta = choice.get("delta", {})

                    content = delta.get("content") or ""
                    reasoning = delta.get("reasoning") or ""
                    if content:
                        yield StreamChunk(content=content)
                    elif reasoning:
                        yield StreamChunk(thinking=reasoning)

                    for tc_delta in delta.get("tool_calls") or []:
                        idx = tc_delta.get("index", 0)
                        entry = tool_call_acc.setdefault(idx, {"id": None, "name": None, "arguments": ""})
                        if tc_delta.get("id"):
                            entry["id"] = tc_delta["id"]
                        fn = tc_delta.get("function") or {}
                        if fn.get("name"):
                            entry["name"] = fn["name"]
                        if fn.get("arguments"):
                            entry["arguments"] += fn["arguments"]

                    if choice.get("finish_reason") and tool_call_acc:
                        finalized = []
                        for entry in tool_call_acc.values():
                            try:
                                args = json.loads(entry["arguments"] or "{}")
                            except json.JSONDecodeError:
                                args = {}
                            finalized.append({"id": entry["id"], "name": entry["name"], "arguments": args})
                        yield StreamChunk(tool_calls=finalized)
                        tool_call_acc = {}
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
            keep_alive=keep_alive if keep_alive is not None else -1,
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
        if cfg.provider_routing:
            payload["provider"] = cfg.provider_routing

        with httpx.Client(timeout=cfg.provider_request_timeout_s) as client:
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