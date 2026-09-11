"""
agent/sovereignai/knowledge_base/store.py

Hybrid RAG retrieval backed by Supabase pgvector — the same database
the Bastion web application uses.

Calls the same Supabase RPC functions the website uses:
  1. search_document_chunks_ranked  (PostgreSQL full-text ranked search)
  2. match_document_chunks           (pgvector semantic similarity)
  3. Keyword ilike fallback

Embeddings are generated with OpenAI text-embedding-3-small via the
shared LLM client, keeping everything in one API dependency.

RBAC is enforced by Supabase Row Level Security policies on the server.
The agent connects as the anon user (same as the website frontend) and
only sees rows the RLS policies permit.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from sovereignai.config import cfg

logger = logging.getLogger(__name__)


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

def _get_supabase():
    """Return a Supabase client using the project's anon key."""
    from supabase import create_client
    url = cfg.supabase_url
    key = cfg.supabase_anon_key
    if not key:
        raise RuntimeError(
            "Supabase anon key not found. "
            "Add SUPABASE_ANON_KEY to agent/.env or set supabase.anon_key in models.yaml."
        )
    return create_client(url, key)


# =============================================================================
# EMBEDDING (OpenAI text-embedding-3-small)
# =============================================================================

def _embed(text: str) -> list[float]:
    """
    Generate a 1536-dim embedding using OpenAI text-embedding-3-small.
    Falls back to a local hash-based pseudo-embedding if the API is unavailable.
    """
    try:
        from sovereignai.providers import get_llm_client
        return get_llm_client().embed(text)
    except Exception as e:
        logger.warning("Embedding via OpenAI failed (%s), using local fallback", e)
        return _local_embed(text)


def _local_embed(text: str) -> list[float]:
    """Deterministic pseudo-embedding (1536 dims) for offline fallback."""
    import math
    vector = [0.0] * 1536
    norm_text = text.lower()
    for i, ch in enumerate(norm_text):
        idx = (ord(ch) * 31 + i * 17) % 1536
        vector[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [round(v / norm, 6) for v in vector]
    return vector


# =============================================================================
# TEXT UTILITIES
# =============================================================================

def _clean_ocr(text: str) -> str:
    """Remove control characters common in OCR output from pypdf."""
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"[\u0003\u0006\u0007\u000E\u000F\u0010-\u001F]", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _format_results(rows: list[dict], fallback: bool = False) -> list[dict]:
    """Normalise Supabase rows to the format expected by rag_tool.py."""
    results = []
    for row in rows:
        title = row.get("title")
        if not title:
            docs = row.get("documents")
            if isinstance(docs, dict):
                title = docs.get("title")
            elif isinstance(docs, str):
                title = docs
        title = title or "Internal Verified Record"
        content = _clean_ocr(row.get("content") or "")
        results.append({
            "chunk": content,
            "source": title,
            "score": float(row.get("similarity", 0.8 if fallback else 0.95)),
            "doc_id": str(row.get("document_id") or row.get("id") or ""),
            "sensitivity": row.get("category", ""),
        })
    return results


# =============================================================================
# KNOWLEDGE STORE
# =============================================================================

class KnowledgeStore:

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def stats(self) -> dict:
        """
        Return knowledge-base statistics from Supabase.

        Returns:
            documents   -> number of unique documents
            chunks      -> number of document_chunks rows
            disk_mb     -> 0.0 (not accessible via anon key)
            last_ingest -> latest document created_at timestamp
        """
        try:
            sb = _get_supabase()

            # Count chunks
            chunks_resp = sb.table("document_chunks").select("id", count="exact").execute()
            chunk_count = chunks_resp.count or 0

            # Count unique documents + latest created_at
            docs_resp = sb.table("documents").select("id, created_at").execute()
            docs = docs_resp.data or []
            doc_count = len(docs)

            last_ingest = None
            if docs:
                latest = max(d.get("created_at", "") for d in docs if d.get("created_at"))
                if latest:
                    last_ingest = latest[:19]

            return {
                "documents": doc_count,
                "chunks": chunk_count,
                "disk_mb": 0.0,
                "last_ingest": last_ingest,
            }
        except Exception as e:
            logger.exception("Failed to get KB stats from Supabase: %s", e)
            return {"documents": 0, "chunks": 0, "disk_mb": 0.0, "last_ingest": None}

    # =========================================================================
    # HYBRID SEARCH
    # =========================================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
        role: str = "admin",   # admin = sees all docs (no category filter)
    ) -> list[dict]:
        """
        Search the Supabase knowledge base using the same strategy as the website:
          1. PostgreSQL full-text ranked search (search_document_chunks_ranked RPC)
          2. pgvector semantic similarity (match_document_chunks RPC)
          3. Keyword ilike fallback

        'admin' role sees all documents (no category filter applied).
        Other roles (tech/finance/support) are filtered by category.
        """
        sb = _get_supabase()
        # 'admin' role (or any unrecognized role like 'viewer'/'employee') sees all documents.
        # Only strict sub-roles in the Supabase enum ('tech', 'finance', 'support') filter by category.
        # This prevents 22P02 Postgres enum cast failures.
        category_filter = role if role in ("tech", "finance", "support") else None

        # ------------------------------------------------------------------
        # Strategy 1: PostgreSQL full-text ranked search
        # ------------------------------------------------------------------
        try:
            resp = sb.rpc(
                "search_document_chunks_ranked",
                {
                    "query_text": query,
                    "filter_company_id": None,
                    "filter_category": category_filter,
                    "match_count": top_k,
                },
            ).execute()
            if resp.data:
                logger.debug("RAG: full-text search returned %d results", len(resp.data))
                return _format_results(resp.data)
        except Exception as e:
            logger.warning("Full-text search RPC failed: %s", e)

        # ------------------------------------------------------------------
        # Strategy 2: Vector semantic search (pgvector)
        # ------------------------------------------------------------------
        try:
            embedding = _embed(query)
            resp = sb.rpc(
                "match_document_chunks",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.15,
                    "match_count": top_k,
                    "filter_company_id": None,
                    "filter_category": category_filter,
                },
            ).execute()
            if resp.data:
                logger.debug("RAG: vector search returned %d results", len(resp.data))
                return _format_results(resp.data)
        except Exception as e:
            logger.warning("Vector search RPC failed: %s", e)

        # ------------------------------------------------------------------
        # Strategy 3: Smart keyword fallback with stopword filtering
        # ------------------------------------------------------------------
        try:
            stop_words = {
                "the", "and", "for", "with", "what", "how", "why", "can", "you", "tell",
                "show", "this", "that", "from", "have", "please", "me", "give", "about",
                "on", "in", "to", "of", "it", "is", "as", "at", "by", "an", "be", "do", "or", "if",
                "so", "up", "my", "no", "we", "us", "our", "all", "are", "was", "were",
            }
            clean_words = [
                re.sub(r"[^\w]", "", w)
                for w in query.lower().split()
                if len(w) >= 3
            ]
            meaningful = [w for w in clean_words if w and w not in stop_words]
            keywords = meaningful if meaningful else clean_words
            if not keywords:
                return []

            primary = keywords[0]
            q = (
                sb.table("document_chunks")
                .select("id, document_id, category, chunk_index, content, documents(title)")
                .ilike("content", f"%{primary}%")
                .limit(top_k)
            )
            if category_filter:
                q = q.eq("category", category_filter)
            resp = q.execute()
            if resp.data:
                return _format_results(resp.data, fallback=True)
        except Exception as e:
            logger.exception("Keyword fallback search failed: %s", e)

        return []


# =============================================================================
# SINGLETON
# =============================================================================

_store: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    """Return the shared KnowledgeStore instance."""
    global _store
    if _store is None:
        _store = KnowledgeStore()
    return _store


# =============================================================================
# MANUAL SMOKE TEST
# =============================================================================

if __name__ == "__main__":
    results = get_store().search(
        "what does the SOP say about pressure limits",
        top_k=5,
        role="admin",
    )
    for r in results:
        print(r)