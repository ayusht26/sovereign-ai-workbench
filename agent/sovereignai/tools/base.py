"""
base.py — Tool ABC, ToolResult, JSON-schema validation, and ToolRegistry.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any


class ToolResult:
    """Standardised result from any tool call."""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str | None = None,
        file_path: str | None = None,
    ) -> None:
        self.success = success
        self.data = data
        self.error = error
        self.file_path = file_path  # if a file was produced, its path

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"success": self.success}
        if self.data is not None:
            d["data"] = self.data
        if self.error:
            d["error"] = self.error
        if self.file_path:
            d["file_path"] = self.file_path
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    @classmethod
    def ok(cls, data: Any = None, file_path: str | None = None) -> "ToolResult":
        return cls(success=True, data=data, file_path=file_path)

    @classmethod
    def fail(cls, error: str) -> "ToolResult":
        return cls(success=False, error=error)


class Tool(ABC):
    """Base class for all SovereignAI tools."""

    name: str = ""
    description: str = ""
    # OpenAI-style function schema — used for Ollama's tool-calling protocol
    json_schema: dict[str, Any] = {}

    # Which task categories can use this tool
    categories: list[str] = ["general", "coding", "vision", "spreadsheet", "document_qa", "planning"]

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        ...

    def as_ollama_tool(self) -> dict[str, Any]:
        """Return the Ollama-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.json_schema,
            },
        }


class ToolRegistry:
    """Registry of available tools, filtered by category."""

    _all_tools: list[Tool] = []

    def __init__(self, tools: list[Tool]) -> None:
        self.tools = tools

    @classmethod
    def register_defaults(cls) -> None:
        """Import and register all built-in tools."""
        from sovereignai.tools.fs_tools import FsRead, FsWrite, FsList, FsGlob
        from sovereignai.tools.sandbox_tool import SandboxExec
        from sovereignai.tools.shell_tool import ShellTool
        from sovereignai.tools.sheet_tool import SheetRead, SheetWrite, SheetCreate
        from sovereignai.tools.docgen_tool import GenDocx, GenPptx, GenXlsx
        from sovereignai.tools.vision_tool import VisionTool
        from sovereignai.tools.rag_tool import RagSearch

        cls._all_tools = [
            FsRead(), FsWrite(), FsList(), FsGlob(),
            SandboxExec(),
            ShellTool(),
            SheetRead(), SheetWrite(), SheetCreate(),
            GenDocx(), GenPptx(), GenXlsx(),
            VisionTool(),
            RagSearch(),
        ]

    @classmethod
    def for_category(cls, category: str) -> "ToolRegistry":
        """Return a registry filtered to tools available for this category."""
        if not cls._all_tools:
            cls.register_defaults()
        tools = [t for t in cls._all_tools if category in t.categories]
        return cls(tools)

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [t.as_ollama_tool() for t in self.tools]

    def dispatch(self, name: str, args: dict[str, Any]) -> ToolResult:
        for tool in self.tools:
            if tool.name == name:
                try:
                    return tool.run(**args)
                except Exception as e:
                    return ToolResult.fail(f"Tool {name} raised: {e}")
        return ToolResult.fail(f"Unknown tool: {name}")

