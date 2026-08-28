"""
agent_loop.py — Hand-rolled ReAct-style plan → act → observe → iterate loop.

This is what makes SovereignAI behave like Claude Code instead of a chatbot.
Streaming to UI at every step; tool calls logged before being shown to model;
hard stop at MAX_ITERATIONS; user can interrupt via session.cancelled flag.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Generator

import ollama

from sovereignai.config import get_config
from sovereignai.orchestrator import audit_log
from sovereignai.orchestrator.router import get_router, RoutingDecision
from sovereignai.orchestrator.session import Session

# System prompt injected into every agent turn
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


def _extract_tool_calls_from_text(raw_text: str, valid_tool_names: set[str]) -> list[tuple[str, dict]]:
    """Extract tool calls if the model printed JSON tool calls into text instead of using native API."""
    calls: list[tuple[str, dict]] = []
    
    # 1. Check for ```json ... ``` blocks
    code_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_text)
    for block in code_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and "name" in data and data["name"] in valid_tool_names:
                args = data.get("arguments") or data.get("parameters") or {k: v for k, v in data.items() if k != "name"}
                calls.append((data["name"], args if isinstance(args, dict) else {}))
        except Exception:
            pass

    # 2. Check for inline JSON objects with {"name": "..."}
    for match in re.finditer(r'\{[^{}]*"name"\s*:\s*"([a-zA-Z0-9_-]+)"[^{}]*\}', raw_text):
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict) and data.get("name") in valid_tool_names:
                args = data.get("arguments") or data.get("parameters") or {k: v for k, v in data.items() if k != "name"}
                calls.append((data["name"], args if isinstance(args, dict) else {}))
        except Exception:
            pass

    # 3. Handle nested JSON objects (e.g. arguments with content containing HTML)
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
                        calls.append((data["name"], args if isinstance(args, dict) else {}))
                except Exception:
                    pass
                pos = end_idx
            else:
                pos = idx + 7

    return calls


class _ExtractedToolFunc:
    def __init__(self, name: str, args: dict) -> None:
        self.name = name
        self.arguments = args


class _ExtractedToolCall:
    def __init__(self, name: str, args: dict) -> None:
        self.function = _ExtractedToolFunc(name, args)


def run_agent_turn(
    session: Session,
    user_message: str,
    model_override: str | None = None,
) -> Generator[dict[str, Any], None, str]:
    """
    Generator-based agent loop. Yields UI events as dicts; returns final text.

    Usage:
        for event in run_agent_turn(session, "Do X"):
            handle(event)   # kind: routing_decision | thought | tool_call_start |
                            #        tool_call_result | stream_chunk | done | error
    """
    cfg = get_config()
    start_time = time.time()

    # ── 1. Append user message ─────────────────────────────────────────────
    session.append("user", user_message)

    # ── 2. Route the request ───────────────────────────────────────────────
    if model_override:
        # Manual model pin — skip the router
        decision = RoutingDecision(
            category="general",
            model_name=model_override,
            confidence=1.0,
            reason="manually pinned",
            uncertain=False,
        )
    else:
        router = get_router()
        decision = router.classify(user_message)

    yield {
        "kind": "routing_decision",
        "category": decision.category,
        "model_name": decision.model_name,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "uncertain": decision.uncertain,
    }

    # ── 3. Build tool registry for this category ───────────────────────────
    from sovereignai.tools.base import ToolRegistry
    registry = ToolRegistry.for_category(decision.category)

    # ── 4. Build system prompt with tool hints ─────────────────────────────
    hint = _TOOL_HINT.get(decision.category, "")
    system_content = f"{_AGENT_SYSTEM}\n\n{hint}"

    # Inject system message once at the start of the session
    messages_for_model = []
    if not any(m["role"] == "system" for m in session.messages_for_model()):
        messages_for_model.append({"role": "system", "content": system_content})
    messages_for_model.extend(session.messages_for_model())

    client = ollama.Client(host=cfg.ollama_host)
    tool_calls_made: list[dict] = []
    response_text = ""

    # ── 5. ReAct loop ──────────────────────────────────────────────────────
    for step in range(cfg.max_iterations):
        if getattr(session, "cancelled", False):
            yield {"kind": "interrupted", "step": step}
            break

        # Stream the model response
        thought_chunks: list[str] = []
        current_tool_calls: list[Any] = []

        try:
            stream = client.chat(
                model=decision.model_name,
                messages=messages_for_model,
                tools=registry.tool_schemas() if registry.tools else None,
                stream=True,
                options={"num_ctx": 8192},
            )
        except ollama.ResponseError as e:
            # Model not pulled — try fallback
            fallback = cfg.fallback_for(decision.category)
            yield {"kind": "error", "message": f"Model {decision.model_name} unavailable, trying {fallback}: {e}"}
            try:
                stream = client.chat(
                    model=fallback,
                    messages=messages_for_model,
                    tools=registry.tool_schemas() if registry.tools else None,
                    stream=True,
                )
                decision = decision._replace(model_name=fallback)
            except Exception as e2:
                yield {"kind": "error", "message": str(e2)}
                return ""

        # Collect streamed chunks
        for chunk in stream:
            if getattr(session, "cancelled", False):
                break

            msg = chunk.message if hasattr(chunk, "message") else (chunk.get("message", {}) if isinstance(chunk, dict) else None)
            if msg is None:
                continue

            content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
            thinking = getattr(msg, "thinking", "") if not isinstance(msg, dict) else msg.get("thinking", "")
            tool_calls = getattr(msg, "tool_calls", None) if not isinstance(msg, dict) else msg.get("tool_calls")

            chunk_text = content or thinking or ""
            if chunk_text:
                thought_chunks.append(chunk_text)
                yield {"kind": "stream_chunk", "chunk": chunk_text, "step": step}

            if tool_calls:
                current_tool_calls.extend(tool_calls)

        # Reconstruct full thought text
        thought_text = "".join(thought_chunks)
        messages_for_model.append({"role": "assistant", "content": thought_text})

        # If no native tool calls were returned by Ollama, extract any tool calls printed in thought_text
        if not current_tool_calls and registry.tools:
            known_tool_names = {t.name for t in registry.tools}
            extracted = _extract_tool_calls_from_text(thought_text, known_tool_names)
            for tool_name, tool_args in extracted:
                current_tool_calls.append(_ExtractedToolCall(tool_name, tool_args))

        # ── 5a. Handle tool calls ─────────────────────────────────────────
        if current_tool_calls:
            tool_results = []
            for call in current_tool_calls:
                tool_name = call.function.name
                tool_args = call.function.arguments or {}

                yield {"kind": "tool_call_start", "name": tool_name, "args": tool_args, "step": step}

                # Dispatch
                result = registry.dispatch(tool_name, tool_args)
                session.tool_calls_made += 1

                yield {
                    "kind": "tool_call_result",
                    "name": tool_name,
                    "args": tool_args,
                    "result": result.to_dict(),
                    "step": step,
                }

                tool_calls_made.append({
                    "name": tool_name,
                    "args": tool_args,
                    "result": result.to_dict(),
                    "step": step,
                })

                tool_results.append({
                    "role": "tool",
                    "content": result.to_json(),
                    "name": tool_name,
                })

            messages_for_model.extend(tool_results)
            continue  # Feed results back to model

        # ── 5b. No tool calls → final response ────────────────────────────
        response_text = thought_text
        session.append("assistant", response_text)

        duration = time.time() - start_time

        # Write audit record
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

    # ── Max iterations hit ─────────────────────────────────────────────────
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

