"""
auth.py — Supabase-backed authentication and session persistence for Bastion Agent.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sovereignai.config import get_config

logger = logging.getLogger("sovereignai.auth")

_AUTH_CACHE_FILE = Path.home() / ".bastion" / "auth_session.json"


def _get_supabase_client():
    """Return an initialized Supabase client."""
    from supabase import create_client
    cfg = get_config()
    url = cfg.supabase_url
    key = cfg.supabase_anon_key
    if not key:
        raise RuntimeError(
            "Supabase anon key not found. Add SUPABASE_ANON_KEY to agent/.env or config.yaml."
        )
    return create_client(url, key)


def get_current_user() -> dict[str, Any] | None:
    """Load cached auth session from disk if valid."""
    if not _AUTH_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(_AUTH_CACHE_FILE.read_text(encoding="utf-8"))
        if data and data.get("id") and data.get("username"):
            return data
    except Exception as e:
        logger.warning("Failed to read auth cache: %s", e)
    return None


def save_auth_session(user_data: dict[str, Any]) -> None:
    """Save user session to ~/.bastion/auth_session.json."""
    try:
        _AUTH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _AUTH_CACHE_FILE.write_text(json.dumps(user_data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error("Failed to save auth session: %s", e)


def clear_auth_session() -> None:
    """Delete cached auth session."""
    try:
        if _AUTH_CACHE_FILE.exists():
            _AUTH_CACHE_FILE.unlink()
    except Exception as e:
        logger.warning("Failed to delete auth session file: %s", e)


def login(identifier: str, password: str) -> dict[str, Any]:
    """
    Authenticate against Supabase using either username or email.
    Returns user dict with id, username, full_name, role, company_id, ai_requests_count.
    Raises ValueError on invalid credentials or connection error.
    """
    clean_id = identifier.strip()
    if not clean_id or not password:
        raise ValueError("Please provide both identifier and password.")

    sb = _get_supabase_client()
    resolved_email = clean_id

    # If identifier has no @, resolve username to email via RPC
    if "@" not in resolved_email:
        try:
            res = sb.rpc("get_email_for_username", {"uname": resolved_email}).execute()
            if res.data:
                resolved_email = res.data
            else:
                raise ValueError("Username not found.")
        except Exception as e:
            if "Username not found" in str(e):
                raise
            logger.warning("RPC get_email_for_username failed (%s), trying as direct identifier", e)

    # Attempt Supabase sign in
    try:
        auth_res = sb.auth.sign_in_with_password({
            "email": resolved_email,
            "password": password,
        })
        user = auth_res.user
        if not user or not user.id:
            raise ValueError("Authentication failed: No user returned.")
    except Exception as e:
        err_msg = str(e)
        if "Invalid login credentials" in err_msg or "Invalid username" in err_msg:
            raise ValueError("Invalid username/email or password.")
        raise ValueError(f"Login failed: {err_msg}")

    # Fetch profile from profiles table
    user_id = str(user.id)
    profile_data: dict[str, Any] = {}
    try:
        prof_res = sb.table("profiles").select("*").eq("id", user_id).single().execute()
        if prof_res.data:
            profile_data = prof_res.data
    except Exception as e:
        logger.warning("Could not fetch profile record: %s", e)

    # Fetch company name if available
    company_name = "Indian Oil Corporation Limited"
    company_id = profile_data.get("company_id") or "796b5531-d535-42c9-b79b-bf88a3048318"
    if profile_data.get("company_id"):
        try:
            comp_res = sb.table("companies").select("name").eq("id", profile_data["company_id"]).single().execute()
            if comp_res.data and comp_res.data.get("name"):
                company_name = comp_res.data["name"]
        except Exception:
            pass

    # Fetch real-time AI requests count
    ai_requests = get_ai_requests_count(user_id)

    user_info = {
        "id": user_id,
        "email": user.email or resolved_email,
        "username": profile_data.get("username", clean_id),
        "full_name": profile_data.get("full_name") or clean_id,
        "role": profile_data.get("role", "admin"),
        "company_id": company_id,
        "company_name": company_name,
        "ai_requests_count": ai_requests,
        "access_token": getattr(auth_res.session, "access_token", ""),
    }

    save_auth_session(user_info)
    return user_info


def logout() -> None:
    """Log out current user and purge cached session."""
    try:
        sb = _get_supabase_client()
        sb.auth.sign_out()
    except Exception:
        pass
    clear_auth_session()


def get_ai_requests_count(user_id: str) -> int:
    """Fetch latest AI requests count for a user from Supabase."""
    try:
        sb = _get_supabase_client()
        res = sb.rpc("get_user_ai_requests", {"p_user_id": user_id}).execute()
        if res.data is not None:
            return int(res.data)
    except Exception as e:
        logger.debug("Failed to get AI requests count via RPC: %s", e)
    return 0


def record_ai_turn(user_id: str, company_id: str, query_text: str) -> int:
    """
    Log an AI turn to Supabase and return the updated requests count.
    Updates document_access_logs, recent_queries, and profiles.ai_requests_count.
    """
    try:
        sb = _get_supabase_client()
        res = sb.rpc("record_ai_query", {
            "p_user_id": user_id,
            "p_company_id": company_id,
            "p_query_text": query_text[:200],
            "p_model": "Bastion-Agent",
        }).execute()
        if res.data is not None:
            return int(res.data)
    except Exception as e:
        logger.warning("Failed to record AI turn via RPC: %s", e)
    return get_ai_requests_count(user_id)
