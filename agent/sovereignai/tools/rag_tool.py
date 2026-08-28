"""
rag_tool.py — Local knowledge base search via ChromaDB.

Returns top-k chunks with source filenames and scores.
The model is instructed to cite source files in its responses.
"""
from __future__ import annotations

from typing import Any

from sovereignai.tools.base import Tool, ToolResult


class RagSearch(Tool):
    name = "rag_search"
    description = (
        "Search the local knowledge base (SOPs, manuals, past correspondence) "
        "for information relevant to a query. "
        "Returns the most relevant chunks with source filenames and sections. "
        "Always cite sources in your response using the returned filenames."
    )
    categories = ["general", "document_qa", "planning", "vision"]
    json_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
            },
            "doc_type": {
                "type": "string",
                "description": "Filter by document type: sop | manual | correspondence | any",
            },
        },
        "required": ["query"],
    }

    def run(self, query: str, top_k: int = 5, doc_type: str | None = None) -> ToolResult:
        try:
            from sovereignai.knowledge_base.store import get_store
            store = get_store()
            results = store.search(query, top_k=top_k, doc_type=doc_type)
            if not results:
                return ToolResult.ok({
                    "query": query,
                    "results": [],
                    "message": "No documents found in the knowledge base. Add documents with: sovai kb add <path>",
                })
            return ToolResult.ok({
                "query": query,
                "results": results,
                "count": len(results),
            })
        except Exception as e:
            return ToolResult.fail(f"RAG search failed: {e}")

