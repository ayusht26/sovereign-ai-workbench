"""
router.py — Task classifier and model selector.

The router keeps a tiny model (llama3.2:3b) permanently resident and uses it
to classify every request into one of six categories at temperature=0.
The router model always runs locally via Ollama, regardless of provider.mode,
so classification stays instant and never depends on network access.
The routing decision is always shown in the UI above the response.
"""
from __future__ import annotations

import json
import re
from typing import NamedTuple

from sovereignai.config import get_config
from sovereignai.providers import get_llm_client


CATEGORIES = frozenset(["general", "coding", "vision", "spreadsheet", "document_qa", "planning"])

_ROUTER_SYSTEM = """\
You are a task router. Classify the user's request into exactly one category:
general | coding | vision | spreadsheet | document_qa | planning

Rules:
- If an image or scanned document is attached or referenced, always choose "vision".
- If the request involves writing, running, fixing, or reviewing code, choose "coding".
- If it references a spreadsheet, financial table, or asks for a calculation with rows/columns, choose "spreadsheet".
- If it asks what a manual/SOP/correspondence/past document says, choose "document_qa".
- If it is a multi-step task with more than one deliverable or clearly needs iteration, choose "planning".
- Otherwise choose "general".

Respond with ONLY this JSON, nothing else:
{"category": "<one of the six>", "confidence": <0.0-1.0>, "reason": "<max 12 words>"}"""


class RoutingDecision(NamedTuple):
    category: str
    model_name: str
    confidence: float
    reason: str
    uncertain: bool
    provider: str  # "local" | "api" — which provider the resolved model will run on


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
                keep_alive=cfg.router_keep_alive,
                force_local=True,
            )
            parsed = _parse_router_output(result.content)
        except Exception as e:
            try:
                result = client.chat(
                    model=cfg.router_fallback,
                    messages=messages,
                    temperature=0,
                    max_tokens=60,
                    force_local=True,
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

        return RoutingDecision(
            category=category,
            model_name=model_name,
            confidence=confidence,
            reason=reason,
            uncertain=uncertain,
            provider=cfg.provider_mode,
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