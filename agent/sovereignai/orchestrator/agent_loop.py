"""
agent_loop.py — Hand-rolled ReAct-style plan → act → observe → iterate loop.

Provider-agnostic:

- local mode: native tool calling
- API mode: prompt-based JSON tool calling

Flow:

    User
      ↓
    Local Router
      ↓
    Category
      ↓
    LLM
      ↓
    Tool call
      ↓
    Tool execution
      ↓
    Tool result
      ↓
    LLM gets result
      ↓
    Final answer
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Generator

from sovereignai.orchestrator.session_context import current_user_role
from sovereignai.config import get_config
from sovereignai.orchestrator import audit_log
from sovereignai.orchestrator.router import get_router, RoutingDecision
from sovereignai.orchestrator.session import Session
from sovereignai.providers import get_llm_client


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

_AGENT_SYSTEM = """
You are SovereignAI, an expert autonomous AI assistant running on this machine.

You have access to tools for:

- filesystem access
- code execution
- document creation
- spreadsheet operations
- vision
- local knowledge-base search

CRITICAL INSTRUCTIONS:

1. Always take direct action when the user asks you to create, edit,
   write, modify, execute, or inspect something.

2. For document or knowledge-base questions, use the knowledge-base
   search tool when relevant.

3. When a tool result is provided to you, treat that result as authoritative
   for the current task.

4. Do NOT invent information that is not present in the supplied tool result
   when the question requires information from a document.

5. If the user explicitly asks for information "from the book",
   "from the document", "exactly from the document", or "word for word",
   use the retrieved document content as the source.

6. After receiving a tool result, DO NOT call the same tool again unless
   another search is genuinely necessary.

7. After receiving sufficient tool results, produce the FINAL ANSWER.

8. Do not output tool-call JSON in the final answer.

9. For exact or word-for-word requests, clearly distinguish quoted
   document text from your own explanation.

10. When citing retrieved information, include the source filename and
    page/chunk information when available.

11. For an exact-document request, never answer from general knowledge
    if the retrieved document contains the requested information.

12. If the tool result contains the requested text, directly answer from
    that result instead of saying that the document could not be found.
"""


# =============================================================================
# TOOL HINTS
# =============================================================================

_TOOL_HINT = {
    "general": (
        "You may use: rag_search, docgen_tool, fs_read, fs_list, fs_write."
    ),

    "document_qa": (
        "IMPORTANT: For questions asking about a book, document, manual, SOP, "
        "or exact document content, use rag_search FIRST. "
        "Do not answer from general model knowledge when the answer should "
        "come from the document. "
        "Available tools: rag_search, fs_read, docgen_tool."
    ),

    "coding": (
        "You may use: fs_write, fs_read, fs_list, fs_glob, "
        "sandbox_exec, shell_tool."
    ),

    "vision": (
        "You may use: vision_tool, docgen_tool, rag_search."
    ),

    "spreadsheet": (
        "You may use: sheet_tool, docgen_tool, fs_read."
    ),

    "planning": (
        "You may use all available tools. Plan step-by-step before acting."
    ),
}


# =============================================================================
# API TOOL-CALL INSTRUCTIONS
# =============================================================================

def _api_tool_call_instructions(tool_schemas: list[dict]) -> str:
    """
    Build instructions for prompt-based tool calling in API mode.
    """

    lines = [
        "TOOL CALLING PROTOCOL:",
        "",
        "When you need to call a tool, output ONLY this JSON block:",
        "",
        '```json',
        '{"name": "<tool_name>", "arguments": {...}}',
        '```',
        "",
        "The arguments object MUST match the tool schema exactly.",
        "",
        "IMPORTANT:",
        "- Do not invent tool names.",
        "- Do not rename argument fields.",
        "- Do not put commentary around the JSON tool call.",
        "- After a tool result is returned, use that result to produce the final answer.",
        "- Do NOT output another tool call unless another tool operation is actually necessary.",
        "- If the tool result already contains the answer, answer directly from it.",
        "",
        "AVAILABLE TOOLS:",
    ]

    for schema in tool_schemas:
        fn = schema.get("function", schema)

        params = json.dumps(
            fn.get("parameters", {}),
            ensure_ascii=False,
        )

        lines.append(
            f"- {fn.get('name')}: "
            f"{fn.get('description', '')}\n"
            f"  parameters schema: {params}"
        )

    return "\n".join(lines)


# =============================================================================
# TOOL CALL EXTRACTION
# =============================================================================

def _extract_tool_calls_from_text(
    raw_text: str,
    valid_tool_names: set[str],
) -> list[dict]:
    """
    Extract prompt-based JSON tool calls from model output.
    """

    calls: list[dict] = []

    if not raw_text:
        return calls

    # -------------------------------------------------------------------------
    # 1. Fenced JSON blocks
    # -------------------------------------------------------------------------

    code_blocks = re.findall(
        r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
        raw_text,
        flags=re.IGNORECASE,
    )

    for block in code_blocks:
        try:
            data = json.loads(block)

            if (
                isinstance(data, dict)
                and data.get("name") in valid_tool_names
            ):
                args = (
                    data.get("arguments")
                    or data.get("parameters")
                    or {
                        k: v
                        for k, v in data.items()
                        if k != "name"
                    }
                )

                calls.append(
                    {
                        "name": data["name"],
                        "arguments": (
                            args
                            if isinstance(args, dict)
                            else {}
                        ),
                    }
                )

        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # -------------------------------------------------------------------------
    # 2. Direct JSON object
    # -------------------------------------------------------------------------

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
            in_string = False
            escape = False

            for i in range(idx, len(raw_text)):
                char = raw_text[i]

                if escape:
                    escape = False
                    continue

                if char == "\\" and in_string:
                    escape = True
                    continue

                if char == '"':
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if char == "{":
                    depth += 1

                elif char == "}":
                    depth -= 1

                    if depth == 0:
                        end_idx = i + 1
                        break

            if end_idx != -1:
                chunk = raw_text[idx:end_idx]

                try:
                    data = json.loads(chunk)

                    if (
                        isinstance(data, dict)
                        and data.get("name") in valid_tool_names
                    ):
                        args = (
                            data.get("arguments")
                            or data.get("parameters")
                            or {
                                k: v
                                for k, v in data.items()
                                if k != "name"
                            }
                        )

                        calls.append(
                            {
                                "name": data["name"],
                                "arguments": (
                                    args
                                    if isinstance(args, dict)
                                    else {}
                                ),
                            }
                        )

                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

                pos = end_idx

            else:
                pos = idx + 7

    # -------------------------------------------------------------------------
    # 3. Hermes/Qwen-style tool calls
    # -------------------------------------------------------------------------

    if not calls:
        calls = _extract_hermes_style_tool_calls(
            raw_text,
            valid_tool_names,
        )

    return calls


def _extract_hermes_style_tool_calls(
    raw_text: str,
    valid_tool_names: set[str],
) -> list[dict]:
    """
    Parse:

        <tool_call>rag_search
        <arg_key>query</arg_key>
        <arg_value>dynamic programming definition</arg_value>
        <arg_key>top_k</arg_key>
        <arg_value>10</arg_value>
        </tool_call>
    """

    calls: list[dict] = []

    if not raw_text:
        return calls

    for block_match in re.finditer(
        r"<tool_call>(.*?)</tool_call>",
        raw_text,
        re.DOTALL | re.IGNORECASE,
    ):
        block = block_match.group(1)

        name_match = re.match(
            r"\s*([a-zA-Z0-9_+-]+)",
            block,
        )

        if not name_match:
            continue

        tool_name = name_match.group(1)

        if tool_name not in valid_tool_names:
            continue

        args: dict[str, Any] = {}

        for key, value in re.findall(
            r"<arg_key>(.*?)</arg_key>\s*"
            r"<arg_value>(.*?)</arg_value>",
            block,
            re.DOTALL | re.IGNORECASE,
        ):
            key = key.strip()
            value = value.strip()

            try:
                args[key] = json.loads(value)
            except json.JSONDecodeError:
                args[key] = value

        calls.append(
            {
                "name": tool_name,
                "arguments": args,
            }
        )

    return calls


# =============================================================================
# STREAM ONE MODEL TURN
# =============================================================================

def _run_stream(
    client,
    model,
    messages,
    tools,
    session,
    step,
) -> Generator[
    dict[str, Any],
    None,
    tuple[str, list[dict]],
]:
    """
    Consume one streamed LLM turn.

    Returns:
        (thought_text, tool_calls)
    """

    thought_chunks: list[str] = []
    tool_calls: list[dict] = []

    for stream_chunk in client.chat_stream(
        model=model,
        messages=messages,
        tools=tools,
        num_ctx=8192,
    ):
        if getattr(session, "cancelled", False):
            break

        chunk_text = (
            getattr(stream_chunk, "content", None)
            or getattr(stream_chunk, "thinking", None)
            or ""
        )

        if chunk_text:
            thought_chunks.append(chunk_text)

            yield {
                "kind": "stream_chunk",
                "chunk": chunk_text,
                "step": step,
            }

        native_tool_calls = getattr(
            stream_chunk,
            "tool_calls",
            None,
        )

        if native_tool_calls:
            tool_calls.extend(native_tool_calls)

        if getattr(stream_chunk, "done", False):
            break

    return (
        "".join(thought_chunks),
        tool_calls,
    )


# =============================================================================
# AGENT TURN
# =============================================================================

def run_agent_turn(
    session: Session,
    user_message: str,
    model_override: str | None = None,
) -> Generator[dict[str, Any], None, str]:

    cfg = get_config()
    start_time = time.time()

    # -------------------------------------------------------------------------
    # Store user message
    # -------------------------------------------------------------------------

    session.append(
        "user",
        user_message,
    )

    # -------------------------------------------------------------------------
    # Resolve authenticated role
    # -------------------------------------------------------------------------

    current_user_role.set(
        getattr(
            session,
            "user_role",
            "viewer",
        )
    )

    # -------------------------------------------------------------------------
    # Route request
    # -------------------------------------------------------------------------

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
        decision = get_router().classify(
            user_message
        )

    yield {
        "kind": "routing_decision",
        "category": decision.category,
        "model_name": decision.model_name,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "uncertain": decision.uncertain,
        "provider": decision.provider,
    }

    # -------------------------------------------------------------------------
    # Load tools
    # -------------------------------------------------------------------------

    from sovereignai.tools.base import ToolRegistry

    registry = ToolRegistry.for_category(
        decision.category
    )

    hint = _TOOL_HINT.get(
        decision.category,
        "",
    )

    system_content = (
        f"{_AGENT_SYSTEM}\n\n"
        f"{hint}"
    )

    # -------------------------------------------------------------------------
    # API-mode tool instructions
    # -------------------------------------------------------------------------

    if (
        cfg.provider_mode == "api"
        and registry.tools
    ):
        system_content += (
            "\n\n"
            + _api_tool_call_instructions(
                registry.tool_schemas()
            )
        )

    # -------------------------------------------------------------------------
    # Build model messages
    # -------------------------------------------------------------------------

    messages_for_model = []

    session_messages = session.messages_for_model()

    if not any(
        m.get("role") == "system"
        for m in session_messages
    ):
        messages_for_model.append(
            {
                "role": "system",
                "content": system_content,
            }
        )

    messages_for_model.extend(
        session_messages
    )

    client = get_llm_client()

    # Native tools ONLY in local mode.
    tools_for_call = (
        registry.tool_schemas()
        if (
            registry.tools
            and cfg.provider_mode == "local"
        )
        else None
    )

    tool_calls_made: list[dict] = []
    response_text = ""

    # =========================================================================
    # REACT LOOP
    # =========================================================================

    for step in range(
        cfg.max_iterations
    ):

        if getattr(
            session,
            "cancelled",
            False,
        ):
            yield {
                "kind": "interrupted",
                "step": step,
            }
            break

        # ---------------------------------------------------------------------
        # Ask model
        # ---------------------------------------------------------------------

        try:
            thought_text, current_tool_calls = (
                yield from _run_stream(
                    client,
                    decision.model_name,
                    messages_for_model,
                    tools_for_call,
                    session,
                    step,
                )
            )

        except Exception as e:

            # -----------------------------------------------------------------
            # Local fallback
            # -----------------------------------------------------------------

            if cfg.provider_mode == "local":

                fallback = cfg.fallback_for(
                    decision.category
                )

                yield {
                    "kind": "error",
                    "message": (
                        f"Model {decision.model_name} unavailable, "
                        f"trying {fallback}: {e}"
                    ),
                }

                try:

                    decision = decision._replace(
                        model_name=fallback
                    )

                    thought_text, current_tool_calls = (
                        yield from _run_stream(
                            client,
                            fallback,
                            messages_for_model,
                            tools_for_call,
                            session,
                            step,
                        )
                    )

                except Exception as e2:

                    yield {
                        "kind": "error",
                        "message": str(e2),
                    }

                    return ""

            # -----------------------------------------------------------------
            # API fallback
            # -----------------------------------------------------------------

            else:

                api_fallback = cfg.api_fallback_for(
                    decision.category
                )

                yield {
                    "kind": "error",
                    "message": (
                        f"API model {decision.model_name} failed, "
                        f"trying free fallback {api_fallback}: {e}"
                    ),
                }

                try:

                    decision = decision._replace(
                        model_name=api_fallback
                    )

                    thought_text, current_tool_calls = (
                        yield from _run_stream(
                            client,
                            api_fallback,
                            messages_for_model,
                            tools_for_call,
                            session,
                            step,
                        )
                    )

                except Exception as e2:

                    yield {
                        "kind": "error",
                        "message": str(e2),
                    }

                    return ""

        # ---------------------------------------------------------------------
        # Extract prompt-based tool calls in API mode
        # ---------------------------------------------------------------------

        if not current_tool_calls and registry.tools:

            known_tool_names = {
                tool.name
                for tool in registry.tools
            }

            current_tool_calls.extend(
                _extract_tool_calls_from_text(
                    thought_text,
                    known_tool_names,
                )
            )

        # ---------------------------------------------------------------------
        # Add assistant response before tool result
        # ---------------------------------------------------------------------

        if thought_text.strip():
            messages_for_model.append(
                {
                    "role": "assistant",
                    "content": thought_text,
                }
            )

        # =========================================================================
        # TOOL EXECUTION
        # =========================================================================

        if current_tool_calls:

            tool_results = []

            for call in current_tool_calls:

                tool_name = call["name"]

                tool_args = (
                    call.get("arguments")
                    or {}
                )

                # -------------------------------------------------------------
                # UI: tool started
                # -------------------------------------------------------------

                yield {
                    "kind": "tool_call_start",
                    "name": tool_name,
                    "args": tool_args,
                    "step": step,
                }

                # -------------------------------------------------------------
                # Execute tool
                # -------------------------------------------------------------

                result = registry.dispatch(
                    tool_name,
                    tool_args,
                )

                session.tool_calls_made += 1

                result_dict = result.to_dict()

                # -------------------------------------------------------------
                # UI: tool result
                # -------------------------------------------------------------

                yield {
                    "kind": "tool_call_result",
                    "name": tool_name,
                    "args": tool_args,
                    "result": result_dict,
                    "step": step,
                }

                tool_calls_made.append(
                    {
                        "name": tool_name,
                        "args": tool_args,
                        "result": result_dict,
                        "step": step,
                    }
                )

                # -------------------------------------------------------------
                # API MODE
                #
                # There is no native tool-call ID.
                # Feed result as a user message.
                # -------------------------------------------------------------

                if cfg.provider_mode == "api":

                    tool_results.append(
                        {
                            "role": "user",
                            "content": (
                                "TOOL RESULT\n\n"
                                f"Tool: {tool_name}\n\n"
                                f"{result.to_json()}\n\n"
                                "IMPORTANT: The tool has finished executing.\n"
                                "Use the tool result above as the source of truth.\n"
                                "Now produce the final answer to the user's "
                                "original question.\n"
                                "Do not output another tool call unless another "
                                "tool operation is genuinely required.\n"
                                "If the result contains the requested document "
                                "text, answer directly from that text."
                            ),
                        }
                    )

                # -------------------------------------------------------------
                # LOCAL MODE
                # -------------------------------------------------------------

                else:

                    tool_results.append(
                        {
                            "role": "tool",
                            "content": result.to_json(),
                            "name": tool_name,
                        }
                    )

            # -----------------------------------------------------------------
            # Feed tool result back into conversation.
            # -----------------------------------------------------------------

            messages_for_model.extend(
                tool_results
            )

            # -----------------------------------------------------------------
            # Continue the loop so the LLM sees the result and generates
            # the final answer.
            # -----------------------------------------------------------------

            continue

        # =========================================================================
        # NO TOOL CALL → FINAL ANSWER
        # =========================================================================

        response_text = thought_text

        session.append(
            "assistant",
            response_text,
        )

        duration = (
            time.time()
            - start_time
        )

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

        yield {
            "kind": "done",
            "text": response_text,
            "duration_s": duration,
        }

        return response_text

    # =========================================================================
    # MAX ITERATIONS
    # =========================================================================

    partial = (
        f"I've reached the step limit "
        f"({cfg.max_iterations} iterations). "
        f"Here's what I've completed so far:\n\n"
        f"{response_text}"
    )

    session.append(
        "assistant",
        partial,
    )

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

    yield {
        "kind": "max_iterations_reached",
        "text": partial,
    }

    return partial