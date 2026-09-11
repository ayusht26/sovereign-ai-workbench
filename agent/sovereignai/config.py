"""
config.py — Loads, validates, and exposes Bastion configuration.

Priority (highest first):
  1. ~/.bastion/config.yaml  (user override)
  2. <package>/models.yaml   (shipped defaults)

`bastion config edit` opens the user config in $EDITOR.
`bastion doctor`      calls validate() and reports any missing pieces.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import yaml

# Auto-load .env from agent/.env or workspace root
_AGENT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_AGENT_DIR / ".env")
load_dotenv()


# ── Paths ──────────────────────────────────────────────────────────────────

_PACKAGE_DIR = Path(__file__).parent
_SHIPPED_DEFAULTS = _PACKAGE_DIR.parent / "models.yaml"
_USER_CONFIG_DIR = Path.home() / ".bastion"
_USER_CONFIG = _USER_CONFIG_DIR / "config.yaml"
_AUDIT_DIR = _USER_CONFIG_DIR / "audit"
_KB_DIR = _USER_CONFIG_DIR / "kb"


def _ensure_dirs() -> None:
    for d in [_USER_CONFIG_DIR, _AUDIT_DIR, _KB_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (override wins on conflicts)."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Config:
    """Parsed, validated configuration object. Access via `get_config()`."""

    def __init__(self, raw: dict) -> None:
        self._raw = raw

    # ── Convenience accessors ──────────────────────────────────────────────

    @property
    def ollama_host(self) -> str:
        return self._raw.get("ollama", {}).get("host", "http://127.0.0.1:11434")

    @property
    def ollama_timeout(self) -> int:
        return self._raw.get("ollama", {}).get("request_timeout_s", 600)

    @property
    def router_model(self) -> str:
        return self._raw.get("router", {}).get("model", "llama3.2:3b")

    @property
    def router_fallback(self) -> str:
        return self._raw.get("router", {}).get("fallback", "llama3.2:3b")

    @property
    def router_keep_alive(self) -> int | str:
        """
        Ollama wants an int (seconds, or -1 to keep the model loaded
        forever) or a Go duration string like "5m" — never a quoted
        "-1", which Ollama's duration parser rejects with a 400.
        """
        val = self._raw.get("router", {}).get("keep_alive", -1)
        try:
            return int(val)
        except (TypeError, ValueError):
            return val
        
    @property
    def provider_mode(self) -> str:
        """'local' (Ollama, air-gapped) or 'api' (OpenRouter / OpenAI-compatible)."""
        return self._raw.get("provider", {}).get("mode", "local")
    @property
    def provider_request_timeout_s(self) -> int:
        return self._raw.get("provider", {}).get("request_timeout_s", 45)
    @property
    def provider_base_url(self) -> str:
        return self._raw.get("provider", {}).get("base_url", "https://openrouter.ai/api/v1")

    @property
    def provider_api_key_env(self) -> str:
        """Name of the environment variable holding the API key — never the key itself."""
        return self._raw.get("provider", {}).get("api_key_env", "OPENROUTER_API_KEY")
    @property
    def provider_request_timeout_s(self) -> int:
        return self._raw.get("provider", {}).get("request_timeout_s", 45)
    @property
    def provider_app_url(self) -> str | None:
        return self._raw.get("provider", {}).get("app_url")

    def model_for(self, category: str) -> str:
        node = self._raw.get("models", {}).get(category, {})
        key = "api" if self.provider_mode == "api" else "local"
        # falls back to the old flat model key if someone hasn't migrated a category yet
        return node.get(key) or node.get("model", "llama3.1:8b")
    
    def fallback_for(self, category: str) -> str:
        return self._raw.get("models", {}).get(category, {}).get("fallback", "llama3.1:8b")
    
    def api_fallback_for(self, category: str) -> str:
        """Free-tier model to retry with in api mode — e.g. on rate limit or exhausted credits."""
        node = self._raw.get("models", {}).get(category, {})
        return node.get("api_fallback", "openai/gpt-oss-20b:free")
    
    @property
    def embedding_model(self) -> str:
        return self._raw.get("models", {}).get("embedding", {}).get("model", "text-embedding-3-small")

    @property
    def supabase_url(self) -> str:
        env_val = (
            os.environ.get("SUPABASE_URL")
            or os.environ.get("VITE_SUPABASE_URL")
            or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            or ""
        )
        if env_val:
            return env_val
        return self._raw.get("supabase", {}).get("url", "https://tybbzdbglhfnpdvgvrjs.supabase.co")

    @property
    def supabase_anon_key(self) -> str:
        """Returns anon key from env var if set, else falls back to config default."""
        env_key = self._raw.get("supabase", {}).get("anon_key_env", "SUPABASE_ANON_KEY")
        env_val = (
            os.environ.get(env_key)
            or os.environ.get("VITE_SUPABASE_ANON_KEY")
            or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
            or ""
        )
        if env_val:
            return env_val
        return self._raw.get("supabase", {}).get("anon_key", "")

    @property
    def workspace_allow_list(self) -> list[str]:
        return self._raw.get("workspace", {}).get("allow_list", [])

    @property
    def auto_approve_new_files(self) -> bool:
        return self._raw.get("workspace", {}).get("auto_approve_new_files", True)

    @property
    def require_diff_preview(self) -> bool:
        return self._raw.get("workspace", {}).get("require_diff_preview", True)

    @property
    def sandbox_enabled(self) -> bool:
        return self._raw.get("sandbox", {}).get("enabled", True)

    @property
    def sandbox_memory(self) -> str:
        return self._raw.get("sandbox", {}).get("memory_limit", "2g")

    @property
    def sandbox_cpus(self) -> float:
        return self._raw.get("sandbox", {}).get("cpu_limit", 2.0)

    @property
    def sandbox_timeout(self) -> int:
        return self._raw.get("sandbox", {}).get("timeout_s", 60)
    @property
    def provider_routing(self) -> dict | None:
        """Pass-through OpenRouter 'provider' object — pin order/allow_fallbacks
        once you know which upstream host is reliable for your workload."""
        return self._raw.get("provider", {}).get("routing")

    @property
    def provider_request_timeout_s(self) -> int:
        return self._raw.get("provider", {}).get("request_timeout_s", 45)
    @property
    def sandbox_images(self) -> dict[str, str]:
        return self._raw.get("sandbox", {}).get("images", {
            "python": "python:3.11-slim",
            "node": "node:20-slim",
            "gcc": "gcc:13",
        })

    @property
    def kb_path(self) -> Path:
        raw = self._raw.get("knowledge_base", {}).get("path", "~/.sovereignai/kb")
        return Path(raw).expanduser()

    @property
    def kb_chunk_size(self) -> int:
        return self._raw.get("knowledge_base", {}).get("chunk_size_tokens", 500)

    @property
    def kb_chunk_overlap(self) -> int:
        return self._raw.get("knowledge_base", {}).get("chunk_overlap_tokens", 50)

    @property
    def kb_max_results(self) -> int:
        return self._raw.get("knowledge_base", {}).get("max_results", 5)

    @property
    def net_guard_enabled(self) -> bool:
        return self._raw.get("net_guard", {}).get("enabled", True)

    @property
    def net_guard_poll_ms(self) -> int:
        return self._raw.get("net_guard", {}).get("poll_interval_ms", 500)

    @property
    def net_guard_allowed_hosts(self) -> list[str]:
        return self._raw.get("net_guard", {}).get("allowed_hosts", [
            "127.0.0.1", "localhost", "::1",
        ])

    @property
    def audit_path(self) -> Path:
        raw = self._raw.get("audit", {}).get("path", "~/.sovereignai/audit")
        return Path(raw).expanduser()

    @property
    def max_iterations(self) -> int:
        return self._raw.get("agent", {}).get("max_iterations", 25)

    def raw(self) -> dict[str, Any]:
        return self._raw


# ── Global singleton ───────────────────────────────────────────────────────

_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _ensure_dirs()
        defaults = _load_yaml(_SHIPPED_DEFAULTS)
        user = _load_yaml(_USER_CONFIG)
        merged = _deep_merge(defaults, user)
        _config = Config(merged)
    return _config


def reload_config() -> Config:
    global _config
    _config = None
    return get_config()


# ── Doctor ────────────────────────────────────────────────────────────────

def doctor(verbose: bool = True) -> bool:
    """
    Check that all required dependencies are present for Bastion.
    Returns True if everything is OK, False if anything is missing.
    Prints a fix command for each missing item.
    """
    cfg = get_config()
    ok = True

    def _check(label: str, result: bool, fix: str) -> None:
        nonlocal ok
        if result:
            if verbose:
                print(f"  [OK]  {label}")
        else:
            ok = False
            if verbose:
                print(f"  [!!]  {label}")
                print(f"        Fix: {fix}")

    if verbose:
        print("\n[*] Bastion doctor\n")

    # Python version
    _check(
        f"Python >= 3.11 (found {sys.version.split()[0]})",
        sys.version_info >= (3, 11),
        "Install Python 3.11+ from python.org",
    )

    # OpenAI API key
    api_key_present = bool(os.environ.get(cfg.provider_api_key_env, ""))
    _check(
        f"OpenAI API key (${cfg.provider_api_key_env}) set",
        api_key_present,
        f"Add OPENAI_API_KEY=sk-... to agent/.env or export it in your shell",
    )

    # OpenAI API reachable (quick test if key is present)
    if api_key_present:
        try:
            import httpx
            r = httpx.get("https://api.openai.com", timeout=5)
            api_reachable = True
        except Exception:
            api_reachable = False
        _check(
            "OpenAI API reachable (https://api.openai.com)",
            api_reachable,
            "Check your internet connection",
        )

    # Supabase reachable
    try:
        import httpx
        sb_url = cfg.supabase_url.rstrip("/") + "/rest/v1/"
        r = httpx.get(sb_url, timeout=5)
        sb_ok = r.status_code in (200, 401, 400)  # 401 = key required, but reachable
    except Exception:
        sb_ok = False
    _check(
        f"Supabase reachable ({cfg.supabase_url})",
        sb_ok,
        "Check your internet connection or Supabase project status",
    )

    # Docker (optional — only needed for sandbox_exec tool)
    docker_ok = shutil.which("docker") is not None
    if docker_ok:
        try:
            subprocess.run(
                ["docker", "info"], capture_output=True, timeout=5, check=True
            )
            docker_running = True
        except Exception:
            docker_running = False
        if not docker_running and verbose:
            print("  [!!] Docker not running -- sandbox_exec tool disabled. Start Docker Desktop to enable it.")
    elif verbose:
        print("  [!!] Docker not installed -- sandbox_exec tool disabled (optional).")

    # User config dir
    _check(
        f"Config dir {_USER_CONFIG_DIR}",
        _USER_CONFIG_DIR.exists(),
        f"mkdir {_USER_CONFIG_DIR}",
    )

    if verbose:
        if ok:
            print("\n[OK] All checks passed. Type `bastion` to launch.\n")
        else:
            print("\n[!!] Some checks failed. Fix the items above, then run `bastion doctor` again.\n")

    return ok


def open_config_in_editor() -> None:
    """Copy shipped defaults to user config (if not present), then open in $EDITOR."""
    _ensure_dirs()
    if not _USER_CONFIG.exists():
        shutil.copy(_SHIPPED_DEFAULTS, _USER_CONFIG)
    editor = os.environ.get("EDITOR", "notepad" if sys.platform == "win32" else "nano")
    subprocess.run([editor, str(_USER_CONFIG)])


cfg = get_config()