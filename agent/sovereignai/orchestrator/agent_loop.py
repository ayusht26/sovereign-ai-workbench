"""
agent_loop.py — Hand-rolled ReAct-style plan → act → observe → iterate loop.

This is what makes SovereignAI behave like Claude Code instead of a chatbot.
Streaming to UI at every step; tool calls logged before being shown to model;
hard stop at MAX_ITERATIONS; user can interrupt via session.cancelled flag.

Provider-agnostic: goes through providers.get_llm_client() so it works
identically whether provider.mode is "local" (Ollama, native tool-calling)
or "api" (OpenRouter, prompt-based JSON tool calls).
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Generator

from sovereignai.config import get_config
from sovereignai.orchestrator import audit_log
from sovereignai.orchestrator.router import get_router, RoutingDecision
from sovereignai.orchestrator.session import Session
from sovereignai.providers import get_llm_client

_AGENT_SYSTEM = """\
You are SovereignAI, an expert autonomous AI assistant running locally on this machine.
You have direct access to tools for filesystem access (fs_write, fs_read, fs_list, fs_glob), code execution, and document creation.

CRITICAL INSTRUCTIONS:
1. Always take direct action. When asked to create, edit, write, or list files or folders, DO NOT just show a code snippet or describe the steps in text. You MUST call the appropriate tool (such as fs_write) to execute the action immediately!
2. To create or update a file, call fs_write with 'path' and 'content'.
3. Every file you write is saved immediately to disk in the workspace.
4. Show brief reasoning before calling tools, then call the tool."""

_TOOL_HINT = {
    "general":      "You may use: rag_tool (to search documents), docgen_tool (to produce Word/PPTX/Excel files), fs_read, fs_list, fs_write.",
    "document_qa":  "You may use: rag_tool (primary), fs_read, docgen_tool.",
    "coding":       "You may use: fs_write, fs_read, fs_list, fs_glob, sandbox_exec (to run code), shell_tool.",
    "vision":       "You may use: vision_tool (to analyze images/PDFs), docgen_tool, rag_tool.",
    "spreadsheet":  "You may use: sheet_tool (to read/write .xlsx), docgen_tool, fs_read.",
    "planning":     "You may use all available tools. Plan step-by-step before acting.",
}


def _api_tool_call_instructions(tool_schemas: list[dict]) -> str:
    """
    API-mode models don't get native tools=; function-calling format varies
    too much across OpenRouter-hosted models to rely on. Describe tools in
    the prompt and ask for a JSON block instead — _extract_tool_calls_from_text
    already knows how to parse this.
    """
    lines = [
        "To call a tool, output a fenced JSON block like this and nothing else in that turn:",
        '```json\n{"name": "<tool_name>", "arguments": {...}}\n```',
        "Available tools:",
    ]
    for schema in tool_schemas:
        fn = schema.get("function", schema)
        lines.append(f"- {fn.get('name')}: {fn.get('description', '')}")
    return "\n".join(lines)


def _extract_tool_calls_from_text(raw_text: str, valid_tool_names: set[str]) -> list[dict]:
    """Extract tool calls if the model printed JSON tool calls into text instead of using native API."""
    calls: list[dict] = []

    code_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_text)
    for block in code_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and data.get("name") in valid_tool_names:
                args = data.get("arguments") or data.get("parameters") or {k: v for k, v in data.items() if k != "name"}
                calls.append({"name": data["name"], "arguments": args if isinstance(args, dict) else {}})
        except Exception:
            pass

    if not calls:
        for match in re.finditer(r'\{[^{}]*"name"\s*:\s*"([a-zA-Z0-9_-]+)"[^{}]*\}', raw_text):
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict) and data.get("name") in valid_tool_names:
                    args = data.get("arguments") or data.get("parameters") or {k: v for k, v in data.items() if k != "name"}
                    calls.append({"name": data["name"], "arguments": args if isinstance(args, dict) else {}})
            except Exception:
                pass

    if not calls:
        pos = 0
        while True:
            idx = raw_text.find('{"name"', pos)
            if idx == -1:
                idx = raw_text.find('{ "name"', pos)
            if idx == -1:
                break
            depth = 0
            end_idx = -1
            for i in range(idx, len(raw_text)):
                if raw_text[i] == '{':
                    depth += 1
                elif raw_text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end_idx = i + 1
                        break
            if end_idx != -1:
                chunk = raw_text[idx:end_idx]
                try:
                    data = json.loads(chunk)
                    if isinstance(data, dict) and data.get("name") in valid_tool_names:
                        args = data.get("arguments") or data.get("parameters") or {k: v for k, v in data.items() if k != "name"}
                        calls.append({"name": data["name"], "arguments": args if isinstance(args, dict) else {}})
                except Exception:
                    pass
                pos = end_idx
            else:
                pos = idx + 7

    return calls


def _run_stream(client, model, messages, tools, session, step) -> Generator[dict[str, Any], None, tuple[str, list[dict]]]:
    """Consumes one streamed turn, yielding UI events, and returns (thought_text, tool_calls)."""
    thought_chunks: list[str] = []
    tool_calls: list[dict] = []
    for stream_chunk in client.chat_stream(model=model, messages=messages, tools=tools, num_ctx=8192):
        if getattr(session, "cancelled", False):
            break
        if stream_chunk.done:
            break
        chunk_text = stream_chunk.content or stream_chunk.thinking or ""
        if chunk_text:
            thought_chunks.append(chunk_text)
            yield {"kind": "stream_chunk", "chunk": chunk_text, "step": step}
        if stream_chunk.tool_calls:
            tool_calls.extend(stream_chunk.tool_calls)
    return "".join(thought_chunks), tool_calls


def run_agent_turn(
    session: Session,
    user_message: str,
    model_override: str | None = None,
) -> Generator[dict[str, Any], None, str]:
    cfg = get_config()
    start_time = time.time()

    session.append("user", user_message)

    if model_override:
        decision = RoutingDecision(
            category="general",
            model_name=model_override,
            confidence=1.0,
            reason="manually pinned",
            uncertain=False,
            provider=cfg.provider_mode,
        )
    else:
        decision = get_router().classify(user_message)

    yield {
        "kind": "routing_decision",
        "category": decision.category,
        "model_name": decision.model_name,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "uncertain": decision.uncertain,
        "provider": decision.provider,
    }

    from sovereignai.tools.base import ToolRegistry
    registry = ToolRegistry.for_category(decision.category)

    hint = _TOOL_HINT.get(decision.category, "")
    system_content = f"{_AGENT_SYSTEM}\n\n{hint}"
    if cfg.provider_mode == "api" and registry.tools:
        system_content += "\n\n" + _api_tool_call_instructions(registry.tool_schemas())

    messages_for_model = []
    if not any(m["role"] == "system" for m in session.messages_for_model()):
        messages_for_model.append({"role": "system", "content": system_content})
    messages_for_model.extend(session.messages_for_model())

    client = get_llm_client()
    # Native tool schemas only make sense in local (Ollama) mode — API mode uses the
    # prompt-based instructions above instead.
    tools_for_call = registry.tool_schemas() if (registry.tools and cfg.provider_mode == "local") else None

    tool_calls_made: list[dict] = []
    response_text = ""

    for step in range(cfg.max_iterations):
        if getattr(session, "cancelled", False):
            yield {"kind": "interrupted", "step": step}
            break

        try:
            thought_text, current_tool_calls = yield from _run_stream(
                client, decision.model_name, messages_for_model, tools_for_call, session, step
            )
        except Exception as e:
            if cfg.provider_mode == "local":
                fallback = cfg.fallback_for(decision.category)
                yield {"kind": "error", "message": f"Model {decision.model_name} unavailable, trying {fallback}: {e}"}
                try:
                    decision = decision._replace(model_name=fallback)
                    thought_text, current_tool_calls = yield from _run_stream(
                        client, fallback, messages_for_model, tools_for_call, session, step
                    )
                except Exception as e2:
                    yield {"kind": "error", "message": str(e2)}
                    return ""
            else:
                yield {"kind": "error", "message": f"API call failed for {decision.model_name}: {e}"}
                return ""

        messages_for_model.append({"role": "assistant", "content": thought_text})

        if not current_tool_calls and registry.tools:
            known_tool_names = {t.name for t in registry.tools}
            current_tool_calls.extend(_extract_tool_calls_from_text(thought_text, known_tool_names))

        if current_tool_calls:
            tool_results = []
            for call in current_tool_calls:
                tool_name = call["name"]
                tool_args = call.get("arguments") or {}

                yield {"kind": "tool_call_start", "name": tool_name, "args": tool_args, "step": step}

                result = registry.dispatch(tool_name, tool_args)
                session.tool_calls_made += 1

                yield {
                    "kind": "tool_call_result",
                    "name": tool_name,
                    "args": tool_args,
                    "result": result.to_dict(),
                    "step": step,
                }
                tool_calls_made.append({"name": tool_name, "args": tool_args, "result": result.to_dict(), "step": step})
                tool_results.append({"role": "tool", "content": result.to_json(), "name": tool_name})

            messages_for_model.extend(tool_results)
            continue

        response_text = thought_text
        session.append("assistant", response_text)
        duration = time.time() - start_time

        audit_log.record(
            session_id=session.id,
            user_text=user_message,
            category=decision.category,
            model_name=decision.model_name,
            confidence=decision.confidence,
            response_text=response_text,
            tool_calls=tool_calls_made,
            duration_s=duration,
        )
        yield {"kind": "done", "text": response_text, "duration_s": duration}
        return response_text

    partial = f"I've reached the step limit ({cfg.max_iterations} iterations). Here's what I've completed so far:\n\n{response_text}"
    session.append("assistant", partial)
    audit_log.record(
        session_id=session.id,
        user_text=user_message,
        category=decision.category,
        model_name=decision.model_name,
        confidence=decision.confidence,
        response_text=partial,
        tool_calls=tool_calls_made,
        duration_s=time.time() - start_time,
    )
    yield {"kind": "max_iterations_reached", "text": partial}
    return partial