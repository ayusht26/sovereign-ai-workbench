"""
shell_tool.py — Allow-listed, logged host-level shell commands.

NOT sandboxed — runs on the host directly. Use only for cheap introspection.
Anything that could write, network, or install must use sandbox_exec instead.
"""
from __future__ import annotations

import shlex
import subprocess
from typing import Any

from sovereignai.tools.base import Tool, ToolResult

# Explicit allow-list — checked BEFORE dispatching
_ALLOWED_COMMANDS = frozenset([
    "ls", "dir", "cat", "head", "tail", "grep", "find",
    "pwd", "echo", "wc", "sort", "uniq",
    "git",   # read-only operations only (enforced below)
    "python", "python3",   # only for --version queries
])

# Subcommand allow-list for git (read-only operations only)
_GIT_ALLOWED_SUBCOMMANDS = frozenset([
    "status", "diff", "log", "show", "branch", "remote",
    "rev-parse", "describe", "ls-files", "shortlog",
])

# Explicit deny-list — checked in addition to the allow-list
_DENIED_FRAGMENTS = frozenset([
    "curl", "wget", "ssh", "scp", "ftp", "sftp",
    "git push", "git clone", "git fetch", "git pull",
    "pip install", "npm install", "yarn add",
    "rm -rf", "dd ", "> /dev/", "chmod 777",
])


def _is_allowed(command: str) -> tuple[bool, str]:
    """Returns (allowed, reason)."""
    lowered = command.lower().strip()

    # Check denied fragments first (belt-and-suspenders)
    for denied in _DENIED_FRAGMENTS:
        if denied in lowered:
            return False, f"Command fragment '{denied}' is explicitly denied."

    try:
        parts = shlex.split(command)
    except ValueError as e:
        return False, f"Cannot parse command: {e}"

    if not parts:
        return False, "Empty command."

    binary = parts[0].lower().rstrip(".exe")

    if binary not in _ALLOWED_COMMANDS:
        return False, (
            f"'{binary}' is not in the shell_tool allow-list. "
            f"Use sandbox_exec for arbitrary code execution."
        )

    # Python is restricted to version checks only.
    if binary in ("python", "python3"):
        if len(parts) != 2 or parts[1] not in ("--version", "-V"):
            return False, (
                "python/python3 is only allowed for --version checks. "
                "Use sandbox_exec for anything else."
            )

    # Extra validation for git
    if binary == "git":
        if len(parts) < 2:
            return False, "git requires a subcommand."

        subcommand = parts[1].lower()

        if subcommand not in _GIT_ALLOWED_SUBCOMMANDS:
            return False, (
                f"git {subcommand} is not allowed. "
                f"Allowed git subcommands: "
                f"{', '.join(sorted(_GIT_ALLOWED_SUBCOMMANDS))}"
            )

    return True, ""


class ShellTool(Tool):
    name = "shell_tool"
    description = (
        "Run an allow-listed, read-only shell command on the host for quick introspection. "
        "Allowed: ls, cat, head, tail, grep, find, pwd, wc, sort, git status/diff/log. "
        "NOT allowed: curl, wget, pip install, git push/clone, or any write/network commands. "
        "Use sandbox_exec for arbitrary code execution."
    )
    categories = ["coding", "planning", "general"]
    json_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to run (allow-listed binaries only)",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 15)",
            },
        },
        "required": ["command"],
    }

    def run(self, command: str, timeout: int = 15) -> ToolResult:
        allowed, reason = _is_allowed(command)

        if not allowed:
            return ToolResult.fail(f"Command denied: {reason}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return ToolResult.ok({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "command": command,
            })

        except subprocess.TimeoutExpired:
            return ToolResult.fail(
                f"Command timed out after {timeout}s: {command}"
            )

        except Exception as e:
            return ToolResult.fail(str(e))