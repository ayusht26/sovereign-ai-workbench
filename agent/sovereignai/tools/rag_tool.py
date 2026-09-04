"""
rag_tool.py — Local knowledge base search.

Searches the SovereignAI Qdrant knowledge base using hybrid
dense + BM25 retrieval.

Security:
- The user's role comes from the authenticated session context.
- The LLM never supplies or controls the role.
- RBAC is enforced inside Qdrant by the knowledge store.
"""

from __future__ import annotations

from sovereignai.tools.base import Tool, ToolResult
from sovereignai.orchestrator.session_context import current_user_role


class RagSearch(Tool):
    name = "rag_search"

    description = (
        "Search the local knowledge base containing SOPs, manuals, "
        "technical documents, books, and other authorized documents. "
        "Use this tool when the user asks for information that may "
        "exist in the knowledge base. "
        "Always use the retrieved results as the source of truth "
        "and cite the returned source document."
    )

    categories = [
        "general",
        "document_qa",
        "planning",
        "vision",
    ]

    json_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The question or information to search for "
                    "in the local knowledge base."
                ),
            },
            "top_k": {
                "type": "integer",
                "description": (
                    "Number of relevant chunks to retrieve. "
                    "Default is 5."
                ),
            },
            "doc_type": {
                "type": "string",
                "description": (
                    "Optional document type filter: "
                    "sop | manual | correspondence | any"
                ),
            },
        },
        "required": ["query"],
    }

    def run(
        self,
        query: str,
        top_k: int = 5,
        doc_type: str | None = None,
    ) -> ToolResult:

        try:
            # Import here so the tool does not initialize the
            # knowledge store until the tool is actually used.
            from sovereignai.knowledge_base.store import get_store

            store = get_store()

            # ---------------------------------------------------------
            # SECURITY:
            # The role is obtained from the authenticated session
            # context. It is NOT supplied by the LLM.
            # ---------------------------------------------------------
            role = current_user_role.get()

            # ---------------------------------------------------------
            # Hybrid retrieval + RBAC
            #
            # store.search() applies the role filter inside Qdrant.
            # ---------------------------------------------------------
            results = store.search(
                query=query,
                top_k=top_k,
                doc_type=doc_type,
                role=role,
            )

            # ---------------------------------------------------------
            # No authorized results
            # ---------------------------------------------------------
            if not results:
                return ToolResult.ok(
                    {
                        "query": query,
                        "results": [],
                        "count": 0,
                        "message": (
                            "No authorized documents were found "
                            "for this query."
                        ),
                    }
                )

            # ---------------------------------------------------------
            # Successful retrieval
            # ---------------------------------------------------------
            return ToolResult.ok(
                {
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
            )

        except Exception as e:
            return ToolResult.fail(
                f"RAG search failed: {e}"
            )