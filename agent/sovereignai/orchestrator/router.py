"""
router.py — Task classifier and model selector for Bastion.

Classifies every user request into one of six categories using
gpt-4o-mini (fast and cheap). The routing decision is always shown
in the TUI above the response, using sovereign display names.
"""
from __future__ import annotations

import json
import re
from typing import NamedTuple

from sovereignai.config import get_config
from sovereignai.providers import get_llm_client
from sovereignai.providers.llm_client import display_name_for, display_name_for_category


CATEGORIES = frozenset(["general", "coding", "vision", "spreadsheet", "document_qa", "planning"])

_ROUTER_SYSTEM = """\
You are a task router. Classify the user's request into exactly one category:
general | coding | vision | spreadsheet | document_qa | planning

Rules:
- If the request asks to create, write, fix, review, or save a plain TEXT or CODE file (.py, .js, .ts, .txt, .sh, etc.), choose "coding".
- If the request asks to RUN or EXECUTE code, choose "coding" — always, even for trivial one-liners like "print(2+2)".
- If the request involves writing, running, fixing, or reviewing code, choose "coding".
- If the request asks to generate a Word, PowerPoint, Excel, or PDF deliverable, choose "general" — these use generate_docx, generate_pptx, generate_xlsx, or generate_pdf rather than raw code/file-writing tools.
- "document_qa" is ONLY for asking what an EXISTING document, SOP, manual, correspondence, or other existing document already says.
- Creating a new Word, PowerPoint, Excel, PDF, report, or other document from scratch — when nothing existing is being queried — is "general", never "document_qa".
- If an image is attached or a scanned document is attached/referenced, choose "vision" when the task primarily requires OCR, transcription, extraction, or a plain description of its contents.
- If an image is attached but the request needs actual reasoning about code, logic, data structures, or SOP compliance, choose "coding" or "general" instead. vision_tool is available to those categories too, so the model can extract the image's content first and then reason about it.
- If a request references an existing image or scanned document and primarily asks to understand its visual contents, choose "vision".
- If the request involves a spreadsheet, financial table, or asks for a calculation involving rows/columns, choose "spreadsheet".
- If it asks what an existing manual, SOP, correspondence, or past document says, choose "document_qa".
- If it is a multi-step task with more than one deliverable or clearly needs iteration, choose "planning".
- Otherwise choose "general".

Respond with ONLY this JSON, nothing else:
{"category": "<one of the six>", "confidence": <0.0-1.0>, "reason": "<max 12 words>"}"""


class RoutingDecision(NamedTuple):
    category: str
    model_name: str          # real API model ID
    display_name: str        # sovereign label shown in TUI (Qwen3.5-9B, Qwen3-Coder-Next, etc.)
    confidence: float
    reason: str
    uncertain: bool
    provider: str            # "local"


class Router:
    """Classifies requests and resolves the appropriate model tag."""

    def __init__(self) -> None:
        self._cfg = get_config()

    def classify(self, user_message: str, context_hint: str = "") -> RoutingDecision:
        """
        Classify the user's request and return a RoutingDecision.
        Falls back to 'general' if the router model fails or confidence is low.
        """
        cfg = self._cfg
        client = get_llm_client()
        messages = [
            {"role": "system", "content": _ROUTER_SYSTEM},
            {"role": "user", "content": user_message},
        ]

        try:
            result = client.chat(
                model=cfg.router_model,
                messages=messages,
                temperature=0,
                max_tokens=60,
            )
            parsed = _parse_router_output(result.content)
        except Exception as e:
            try:
                result = client.chat(
                    model=cfg.router_fallback,
                    messages=messages,
                    temperature=0,
                    max_tokens=60,
                )
                parsed = _parse_router_output(result.content)
            except Exception:
                parsed = {"category": "general", "confidence": 0.0, "reason": f"Router unavailable: {e}"}

        category = parsed.get("category", "general")
        confidence = float(parsed.get("confidence", 0.0))
        reason = parsed.get("reason", "")

        if category not in CATEGORIES:
            category = "general"
            confidence = 0.0

        uncertain = confidence < 0.55
        if uncertain:
            category = "general"

        model_name = _resolve_model(cfg, category)
        display_name = display_name_for_category(category)

        return RoutingDecision(
            category=category,
            model_name=model_name,
            display_name=display_name,
            confidence=confidence,
            reason=reason,
            uncertain=uncertain,
            provider="local",
        )

    def resolve_model(self, category: str) -> str:
        return _resolve_model(self._cfg, category)


def _parse_router_output(raw: str) -> dict:
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"category": "general", "confidence": 0.0, "reason": "Parse failed"}


def _resolve_model(cfg, category: str) -> str:
    if category in ("general", "planning", "document_qa", "spreadsheet"):
        return cfg.model_for("general")
    elif category == "coding":
        return cfg.model_for("coding")
    elif category == "vision":
        return cfg.model_for("vision")
    else:
        return cfg.model_for("general")


_router: Router | None = None


def get_router() -> Router:
    global _router
    if _router is None:
        _router = Router()
    return _router