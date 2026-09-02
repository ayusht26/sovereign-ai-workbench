"""
fs_tools.py — Filesystem tools: fs_read, fs_write, fs_list, fs_glob.

All paths are validated against the workspace root before any operation.
fs_write shows a diff preview in the session's UI before overwriting.
"""
from __future__ import annotations

import difflib
import fnmatch
import os
from pathlib import Path
from typing import Any

from sovereignai.tools.base import Tool, ToolResult


def _workspace() -> Path:
    """Current workspace root — set via the session, defaulting to cwd."""
    # Pulled from env so the TUI can override it at startup
    return Path(os.environ.get("SOVAI_WORKSPACE", ".")).resolve()


def _validate_path(raw: str) -> Path | None:
    """Return resolved path if within workspace, else None."""
    workspace = _workspace()
    try:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (workspace / p).resolve()
        else:
            p = p.resolve()
        p.relative_to(workspace)  # raises ValueError if outside
        return p
    except (ValueError, Exception):
        return None


class FsRead(Tool):
    name = "fs_read"
    description = "Read the text contents of a file within the workspace."
    categories = [
        "general",
        "coding",
        "vision",
        "spreadsheet",
        "document_qa",
        "planning",
    ]
    json_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path (relative to workspace or absolute within workspace)",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional: first line to read (1-indexed)",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional: last line to read (inclusive)",
            },
        },
        "required": ["path"],
    }

    def run(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> ToolResult:
        p = _validate_path(path)
        if p is None:
            return ToolResult.fail(
                f"Path '{path}' is outside the workspace root. Access denied."
            )
        if not p.exists():
            return ToolResult.fail(f"File not found: {path}")
        if not p.is_file():
            return ToolResult.fail(f"Not a file: {path}")

        try:
            lines = p.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines(keepends=True)

            if start_line or end_line:
                s = (start_line or 1) - 1
                e = end_line or len(lines)
                lines = lines[s:e]

            content = "".join(lines)

            return ToolResult.ok({
                "content": content,
                "lines": len(lines),
                "path": str(p),
            })
        except Exception as e:
            return ToolResult.fail(str(e))


class FsWrite(Tool):
    name = "fs_write"
    description = (
        "Write or overwrite a file within the workspace. "
        "Creates parent directories as needed."
    )
    categories = ["coding", "planning", "general"]
    json_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write",
            },
            "content": {
                "type": "string",
                "description": "Text content to write",
            },
            "append": {
                "type": "boolean",
                "description": "If true, append instead of overwrite",
            },
        },
        "required": ["path", "content"],
    }

    def run(
        self,
        path: str,
        content: str,
        append: bool = False,
    ) -> ToolResult:
        p = _validate_path(path)

        if p is None:
            return ToolResult.fail(
                f"Path '{path}' is outside the workspace root. Access denied."
            )

        # Show diff if overwriting
        diff_preview = None

        if p.exists() and not append:
            existing = p.read_text(
                encoding="utf-8",
                errors="replace",
            )

            diff = list(
                difflib.unified_diff(
                    existing.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{p.name}",
                    tofile=f"b/{p.name}",
                    lineterm="",
                )
            )

            if diff:
                diff_preview = "".join(diff[:100])  # cap for UI

        try:
            p.parent.mkdir(parents=True, exist_ok=True)

            # Use a context manager for append mode so the file
            # handle is always closed properly.
            if append:
                with open(p, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                p.write_text(content, encoding="utf-8")

            return ToolResult.ok({
                "written": len(content),
                "path": str(p),
                "diff_preview": diff_preview,
                "appended": append,
            }, file_path=str(p))

        except Exception as e:
            return ToolResult.fail(str(e))


class FsList(Tool):
    name = "fs_list"
    description = "List files and directories in a path within the workspace."
    categories = [
        "general",
        "coding",
        "vision",
        "spreadsheet",
        "document_qa",
        "planning",
    ]
    json_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory to list (default: workspace root)",
            },
            "recursive": {
                "type": "boolean",
                "description": "Recurse into subdirectories",
            },
        },
        "required": [],
    }

    def run(
        self,
        path: str = ".",
        recursive: bool = False,
    ) -> ToolResult:
        p = _validate_path(path)

        if p is None:
            return ToolResult.fail(
                f"Path '{path}' is outside the workspace root."
            )

        if not p.exists():
            return ToolResult.fail(f"Path not found: {path}")

        entries = []

        if recursive:
            for item in sorted(p.rglob("*")):
                try:
                    item.relative_to(_workspace())

                    entries.append({
                        "path": str(item.relative_to(_workspace())),
                        "type": "dir" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                    })

                except ValueError:
                    continue

        else:
            for item in sorted(p.iterdir()):
                entries.append({
                    "path": str(item.relative_to(_workspace())),
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })

        return ToolResult.ok({
            "entries": entries,
            "count": len(entries),
            "directory": str(p),
        })


class FsGlob(Tool):
    name = "fs_glob"
    description = "Find files matching a glob pattern within the workspace."
    categories = ["general", "coding", "planning"]
    json_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern e.g. '**/*.py', '*.txt'",
            },
            "base": {
                "type": "string",
                "description": "Base directory (default: workspace root)",
            },
        },
        "required": ["pattern"],
    }

    def run(
        self,
        pattern: str,
        base: str = ".",
    ) -> ToolResult:
        base_path = _validate_path(base)

        if base_path is None:
            return ToolResult.fail(
                f"Base path '{base}' outside workspace."
            )

        matches = []

        try:
            for match in sorted(base_path.glob(pattern)):
                try:
                    match.relative_to(_workspace())

                    matches.append({
                        "path": str(match.relative_to(_workspace())),
                        "type": "dir" if match.is_dir() else "file",
                        "size": match.stat().st_size if match.is_file() else None,
                    })

                except ValueError:
                    continue

        except Exception as e:
            return ToolResult.fail(str(e))

        return ToolResult.ok({
            "matches": matches,
            "count": len(matches),
            "pattern": pattern,
        })