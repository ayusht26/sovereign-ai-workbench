"""
config.py — Loads, validates, and exposes SovereignAI configuration.

Priority (highest first):
  1. ~/.sovereignai/config.yaml  (user override)
  2. <package>/models.yaml       (shipped defaults)

`sovai config edit` opens the user config in $EDITOR.
`sovai doctor`      calls validate() and reports any missing pieces.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


# ── Paths ──────────────────────────────────────────────────────────────────

_PACKAGE_DIR = Path(__file__).parent
_SHIPPED_DEFAULTS = _PACKAGE_DIR.parent / "models.yaml"
_USER_CONFIG_DIR = Path.home() / ".sovereignai"
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
    def router_keep_alive(self) -> str:
        return self._raw.get("router", {}).get("keep_alive", "-1")
    @property
    def provider_mode(self) -> str:
        """'local' (Ollama, air-gapped) or 'api' (OpenRouter / OpenAI-compatible)."""
        return self._raw.get("provider", {}).get("mode", "local")

    @property
    def provider_base_url(self) -> str:
        return self._raw.get("provider", {}).get("base_url", "https://openrouter.ai/api/v1")

    @property
    def provider_api_key_env(self) -> str:
        """Name of the environment variable holding the API key — never the key itself."""
        return self._raw.get("provider", {}).get("api_key_env", "OPENROUTER_API_KEY")

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
        return self._raw.get("models", {}).get("embedding", {}).get("model", "nomic-embed-text")

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
    Check that all required dependencies are present.
    Returns True if everything is OK, False if anything is missing.
    Prints a fix command for each missing item.
    """
    import importlib

    cfg = get_config()
    ok = True

    def _check(label: str, result: bool, fix: str) -> None:
        nonlocal ok
        if result:
            if verbose:
                print(f"  ✅  {label}")
        else:
            ok = False
            if verbose:
                print(f"  ❌  {label}")
                print(f"       Fix: {fix}")

    if verbose:
        print("\n🔍 SovereignAI doctor\n")

    # Python version
    _check(
        f"Python ≥ 3.11 (found {sys.version.split()[0]})",
        sys.version_info >= (3, 11),
        "Install Python 3.11+ from python.org",
    )

    # Ollama running
    try:
        import ollama as _ollama_mod
        _ollama_mod.Client(host=cfg.ollama_host).list()
        ollama_ok = True
    except Exception:
        ollama_ok = False
    _check(
        f"Ollama running at {cfg.ollama_host}",
        ollama_ok,
        "Start Ollama: `ollama serve`  (or install from https://ollama.com/download)",
    )

        # Required models — only check what actually needs to be local.
    # In "api" mode, general/coding/vision run on OpenRouter, so their
    # presence in `ollama list` is irrelevant; only the router (always
    # local) and the embedding model (kept local for RAG consistency) matter.
        # Required models — only check what actually needs to be local.
    # In "api" mode, general/coding/vision run on OpenRouter, so their
    # presence in `ollama list` is irrelevant; only the router (always
    # local) and the embedding model (kept local for RAG consistency) matter.
    if ollama_ok:
        try:
            import ollama as _ollama_mod
            pulled = {m.model for m in _ollama_mod.Client(host=cfg.ollama_host).list().models}

            roles_to_check = ["router", "embedding"]
            if cfg.provider_mode == "local":
                roles_to_check += ["general", "coding", "vision"]

            for role in roles_to_check:
                tag = cfg.router_model if role == "router" else (
                    cfg.embedding_model if role == "embedding" else cfg.model_for(role)
                )
                present = any(tag in p for p in pulled)
                _check(f"Model [{role}] {tag}", present, f"ollama pull {tag}")
        except Exception:
            pass

    if cfg.provider_mode == "api":
        api_key_present = bool(os.environ.get(cfg.provider_api_key_env, ""))
        _check(
            f"OpenRouter API key (${cfg.provider_api_key_env}) set",
            api_key_present,
            f"export {cfg.provider_api_key_env}=sk-...",
        )

    # Docker
    docker_ok = shutil.which("docker") is not None
    _check(
        "Docker installed",
        docker_ok,
        "Install Docker Desktop from https://www.docker.com/products/docker-desktop",
    )
    if docker_ok:
        try:
            subprocess.run(
                ["docker", "info"], capture_output=True, timeout=5, check=True
            )
            docker_running = True
        except Exception:
            docker_running = False
        _check(
            "Docker daemon running",
            docker_running,
            "Start Docker Desktop",
        )

    # User config dir
    _check(
        f"Config dir {_USER_CONFIG_DIR}",
        _USER_CONFIG_DIR.exists(),
        f"mkdir -p {_USER_CONFIG_DIR}",
    )

    if verbose:
        if ok:
            print("\n✅  All checks passed. Type `sovai` to launch.\n")
        else:
            print("\n❌  Some checks failed. Fix the items above, then run `sovai doctor` again.\n")

    return ok


def open_config_in_editor() -> None:
    """Copy shipped defaults to user config (if not present), then open in $EDITOR."""
    _ensure_dirs()
    if not _USER_CONFIG.exists():
        shutil.copy(_SHIPPED_DEFAULTS, _USER_CONFIG)
    editor = os.environ.get("EDITOR", "notepad" if sys.platform == "win32" else "nano")
    subprocess.run([editor, str(_USER_CONFIG)])

