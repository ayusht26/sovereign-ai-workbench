"""
store.py — ChromaDB wrapper for the local knowledge base.

Uses the persistent embedded client (no server needed).
All data lives under ~/.sovereignai/kb/chroma/.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from sovereignai.config import get_config


class KnowledgeStore:
    """Wraps ChromaDB for local, on-disk vector storage."""

    COLLECTION_NAME = "sovereignai_kb"

    def __init__(self) -> None:
        cfg = get_config()
        chroma_dir = cfg.kb_path / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(chroma_dir))
            self._col = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            raise RuntimeError(
                "chromadb not installed. Run: pip install chromadb"
            )

    def upsert(
        self,
        doc_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> None:
        self._col.upsert(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search by query text. Returns list of {chunk, source_file, score}."""
        # Embed the query
        embedding = _embed(query)
        if embedding is None:
            return []

        where = None
        if doc_type and doc_type != "any":
            where = {"doc_type": doc_type}

        try:
            results = self._col.query(
                query_embeddings=[embedding],
                n_results=min(top_k, self._col.count() or 1),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        hits = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            # Cosine distance → similarity score
            score = 1.0 - float(dist)
            hits.append({
                "chunk": doc,
                "source_file": meta.get("source_path", "unknown"),
                "page": meta.get("page", None),
                "doc_type": meta.get("doc_type", "unknown"),
                "score": round(score, 4),
                "ingested_at": meta.get("ingested_at", ""),
            })

        return hits

    def count(self) -> int:
        return self._col.count()

    def stats(self) -> dict[str, Any]:
        cfg = get_config()
        chroma_dir = cfg.kb_path / "chroma"

        # Disk size
        disk_bytes = sum(f.stat().st_size for f in chroma_dir.rglob("*") if f.is_file())

        # Last ingest time from metadata
        last_ingest = None
        try:
            sample = self._col.get(limit=1, include=["metadatas"])
            if sample["metadatas"]:
                last_ingest = sample["metadatas"][0].get("ingested_at")
        except Exception:
            pass

        # Approximate doc count (unique source files)
        try:
            all_meta = self._col.get(include=["metadatas"])
            sources = set(m.get("source_path", "") for m in all_meta["metadatas"])
            doc_count = len(sources)
        except Exception:
            doc_count = 0

        return {
            "documents": doc_count,
            "chunks": self._col.count(),
            "disk_mb": disk_bytes / 1e6,
            "last_ingest": last_ingest,
        }

    def delete_source(self, source_path: str) -> int:
        """Remove all chunks from a given source file."""
        try:
            result = self._col.get(where={"source_path": source_path}, include=["metadatas"])
            ids = result.get("ids", [])
            if ids:
                self._col.delete(ids=ids)
            return len(ids)
        except Exception:
            return 0


def _embed(text: str) -> list[float] | None:
    """Embed text using the Ollama embedding model."""
    cfg = get_config()
    try:
        import ollama
        client = ollama.Client(host=cfg.ollama_host)
        resp = client.embed(model=cfg.embedding_model, input=text)
        return resp.embeddings[0]
    except Exception:
        return None


# Module-level singleton
_store: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    global _store
    if _store is None:
        _store = KnowledgeStore()
    return _store

