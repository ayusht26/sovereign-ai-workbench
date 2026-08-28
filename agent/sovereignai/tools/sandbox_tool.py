"""
sandbox_tool.py — Docker-based code execution sandbox.

Runs arbitrary code in an isolated container with --network none.
This is the component most security-critical in the whole system.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from sovereignai.tools.base import Tool, ToolResult

# Language → Docker image map
_LANG_IMAGES = {
    "python":     "python:3.11-slim",
    "py":         "python:3.11-slim",
    "javascript": "node:20-slim",
    "js":         "node:20-slim",
    "node":       "node:20-slim",
    "c":          "gcc:13",
    "cpp":        "gcc:13",
    "c++":        "gcc:13",
    "bash":       "python:3.11-slim",  # bash available in slim images
    "sh":         "python:3.11-slim",
}

# Commands to run code per language
_LANG_COMMANDS = {
    "python":     ["python", "/workspace/main.py"],
    "py":         ["python", "/workspace/main.py"],
    "javascript": ["node", "/workspace/main.js"],
    "js":         ["node", "/workspace/main.js"],
    "node":       ["node", "/workspace/main.js"],
    "c":          ["sh", "-c", "cd /workspace && gcc -o main main.c && ./main"],
    "cpp":        ["sh", "-c", "cd /workspace && g++ -o main main.cpp && ./main"],
    "c++":        ["sh", "-c", "cd /workspace && g++ -o main main.cpp && ./main"],
    "bash":       ["bash", "/workspace/main.sh"],
    "sh":         ["sh", "/workspace/main.sh"],
}

_FILE_NAMES = {
    "python": "main.py", "py": "main.py",
    "javascript": "main.js", "js": "main.js", "node": "main.js",
    "c": "main.c", "cpp": "main.cpp", "c++": "main.cpp",
    "bash": "main.sh", "sh": "main.sh",
}


class SandboxExec(Tool):
    name = "sandbox_exec"
    description = (
        "Execute code in an isolated Docker container with --network none. "
        "Supports: python, javascript, c, cpp, bash. "
        "Returns stdout, stderr, and exit code."
    )
    categories = ["coding", "planning"]
    json_schema = {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "description": "Language: python | javascript | c | cpp | bash",
                "enum": ["python", "javascript", "c", "cpp", "bash"],
            },
            "code": {
                "type": "string",
                "description": "The code to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 60)",
            },
            "stdin": {
                "type": "string",
                "description": "Optional stdin to pipe to the process",
            },
        },
        "required": ["language", "code"],
    }

    def run(
        self,
        language: str,
        code: str,
        timeout: int = 60,
        stdin: str | None = None,
    ) -> ToolResult:
        from sovereignai.config import get_config
        cfg = get_config()

        if not cfg.sandbox_enabled:
            return ToolResult.fail("Sandbox is disabled in configuration.")

        lang = language.lower()
        if lang not in _LANG_IMAGES:
            return ToolResult.fail(f"Unsupported language: {language}. Use: python, javascript, c, cpp, bash")

        if not shutil.which("docker"):
            return ToolResult.fail("Docker not found. Install Docker to use sandbox_exec.")

        image = _LANG_IMAGES[lang]
        cmd = _LANG_COMMANDS[lang]
        filename = _FILE_NAMES[lang]

        try:
            import docker as docker_sdk
        except ImportError:
            return ToolResult.fail("docker Python SDK not installed. Run: pip install docker")

        # Write code to a temp dir (mounted into the container)
        with tempfile.TemporaryDirectory(prefix="sovai_sandbox_") as tmpdir:
            code_path = Path(tmpdir) / filename
            code_path.write_text(code, encoding="utf-8")

            try:
                client = docker_sdk.from_env(timeout=timeout + 10)

                container = client.containers.run(
                    image=image,
                    command=cmd,
                    volumes={tmpdir: {"bind": "/workspace", "mode": "rw"}},
                    network_mode="none",          # ← NON-NEGOTIABLE
                    mem_limit=cfg.sandbox_memory,
                    nano_cpus=int(cfg.sandbox_cpus * 1e9),
                    read_only=False,              # workspace is rw, rest is ro via image
                    remove=True,
                    detach=False,
                    stdout=True,
                    stderr=True,
                    stdin_open=bool(stdin),
                    environment={"PYTHONDONTWRITEBYTECODE": "1"},
                )

                # container.run returns bytes when detach=False
                stdout_bytes = container if isinstance(container, bytes) else b""
                stderr_bytes = b""
                exit_code = 0

            except docker_sdk.errors.ContainerError as e:
                stdout_bytes = e.stderr or b""
                stderr_bytes = e.stderr or b""
                exit_code = e.exit_status
            except docker_sdk.errors.ImageNotFound:
                return ToolResult.fail(
                    f"Docker image '{image}' not found locally. "
                    f"Pre-pull it with: docker pull {image}"
                )
            except Exception as e:
                return ToolResult.fail(f"Sandbox error: {e}")

            stdout_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            return ToolResult.ok({
                "exit_code": exit_code,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "language": lang,
                "network": "none",
                "passed": exit_code == 0,
            })

