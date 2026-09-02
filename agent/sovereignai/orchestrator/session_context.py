"""
session_context.py — Per-turn context (current user's role) available to
tools without the model ever supplying it as a tool argument. Set once per
turn from the authenticated session; never trust a value the model claims.
"""
from __future__ import annotations
from contextvars import ContextVar

current_user_role: ContextVar[str] = ContextVar("current_user_role", default="viewer")