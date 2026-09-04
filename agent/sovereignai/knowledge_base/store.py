"""
agent/sovereignai/knowledge_base/store.py

Hybrid (BM25 + dense vector) retrieval over a self-hosted Qdrant instance,
with role-based access control enforced INSIDE the Qdrant query (a native
payload filter), never as a post-hoc Python filter.

==============================================================================
READ THIS BEFORE TOUCHING `role` IN search()
==============================================================================

By the time `role` reaches this function, it is already resolved and already
trustworthy. The call chain (all upstream of this file) is:

    session (real, authenticated)
        -> current_user_role.set(session.user_role)   [agent_loop.py]
        -> role = current_user_role.get()              [rag_tool.py]
        -> get_store().search(..., role=role)          [rag_tool.py]

The LLM never supplies `role` as a tool-call argument and never sees this
parameter.

The only thing this function does with `role` is build a Qdrant filter:

    allowed_roles contains role

The filter is applied INSIDE the Qdrant query, before retrieval.
==============================================================================

"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import ollama

from qdrant_client import QdrantClient

from qdrant_client.models import (
    FieldCondition,
    Filter,
    FusionQuery,
    Fusion,
    MatchAny,
    MatchValue,
    Prefetch,
    SparseVector,
)

from sovereignai.config import cfg


logger = logging.getLogger(__name__)


# =============================================================================
# QDRANT CONFIGURATION
# =============================================================================

COLLECTION_NAME = "sovereign_kb"

QDRANT_HOST = getattr(
    cfg,
    "qdrant_host",
    "localhost",
)

QDRANT_PORT = getattr(
    cfg,
    "qdrant_port",
    6333,
)


# =============================================================================
# OLLAMA CONFIGURATION
# =============================================================================

OLLAMA_URL = getattr(
    cfg,
    "ollama_url",
    "http://localhost:11434",
)

_ollama_client = ollama.Client(
    host=OLLAMA_URL
)


# =============================================================================
# DENSE EMBEDDING
# =============================================================================

def _embed_dense(text: str) -> list[float]:
    """
    Generate a dense embedding using the local Ollama embedding model.
    """

    response = _ollama_client.embeddings(
        model=cfg.embedding_model,
        prompt=text,
    )

    return response["embedding"]


# =============================================================================
# SPARSE BM25 EMBEDDING
# =============================================================================

class _SparseEmbedder:
    """
    Wrapper around FastEmbed's Qdrant BM25 sparse embedding model.

    The model is loaded lazily on first use.
    """

    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            from fastembed import SparseTextEmbedding

            cls._model = SparseTextEmbedding(
                model_name="Qdrant/bm25"
            )

        return cls._model

    @classmethod
    def embed(cls, text: str) -> SparseVector:
        """
        Convert text into a Qdrant-compatible sparse vector.
        """

        model = cls._get_model()

        result = next(
            model.query_embed(text)
        )

        return SparseVector(
            indices=result.indices.tolist(),
            values=result.values.tolist(),
        )


# =============================================================================
# QDRANT COLLECTION SETUP
# =============================================================================

def ensure_collection(
    client: QdrantClient,
    dense_size: int = 768,
) -> None:
    """
    Ensure that the sovereign_kb collection exists.

    Dense vector:
        nomic-embed-text

    Sparse vector:
        Qdrant BM25
    """

    from qdrant_client.models import (
        Distance,
        SparseVectorParams,
        VectorParams,
    )

    if client.collection_exists(
        COLLECTION_NAME
    ):
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,

        vectors_config={
            "dense": VectorParams(
                size=dense_size,
                distance=Distance.COSINE,
            )
        },

        sparse_vectors_config={
            "sparse": SparseVectorParams()
        },
    )


# =============================================================================
# KNOWLEDGE STORE
# =============================================================================

class KnowledgeStore:

    def __init__(self) -> None:
        """
        Initialize Qdrant client and ensure the collection exists.
        """

        self._client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
        )

        ensure_collection(
            self._client
        )

    # =========================================================================
    # KNOWLEDGE BASE STATISTICS
    # =========================================================================

    def stats(self) -> dict:
        """
        Return knowledge-base statistics.

        Returns:

            documents  -> number of unique documents
            chunks     -> number of Qdrant points
            disk_mb    -> estimated collection disk usage
            last_ingest -> latest source-file modification time
        """

        collection = self._client.get_collection(
            COLLECTION_NAME
        )

        # ---------------------------------------------------------------------
        # Find unique documents and latest source modification time
        # ---------------------------------------------------------------------

        documents = set()

        latest_timestamp = None

        offset = None

        while True:

            points, next_offset = self._client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:

                payload = point.payload or {}

                # -------------------------------------------------------------
                # Document ID
                # -------------------------------------------------------------

                doc_id = payload.get(
                    "doc_id"
                )

                if doc_id:
                    documents.add(
                        doc_id
                    )

                # -------------------------------------------------------------
                # Source file modification time
                # -------------------------------------------------------------

                source = payload.get(
                    "source"
                )

                if source:

                    try:

                        source_path = Path(
                            source
                        )

                        if source_path.exists():

                            modified_time = source_path.stat().st_mtime

                            if (
                                latest_timestamp is None
                                or modified_time > latest_timestamp
                            ):
                                latest_timestamp = modified_time

                    except (
                        OSError,
                        ValueError,
                    ):
                        pass

            if next_offset is None:
                break

            offset = next_offset

        # ---------------------------------------------------------------------
        # Determine disk size
        # ---------------------------------------------------------------------

        disk_mb = 0.0

        try:

            collection_info = self._client.get_collection(
                COLLECTION_NAME
            )

            disk_size = getattr(
                collection_info,
                "disk_size",
                None,
            )

            if disk_size:
                disk_mb = (
                    float(disk_size)
                    / (1024 * 1024)
                )

        except Exception:

            logger.exception(
                "Unable to determine Qdrant disk usage"
            )

        # ---------------------------------------------------------------------
        # Format last ingest timestamp
        # ---------------------------------------------------------------------

        last_ingest = None

        if latest_timestamp is not None:

            last_ingest = datetime.fromtimestamp(
                latest_timestamp
            ).isoformat(
                timespec="seconds"
            )

        # ---------------------------------------------------------------------
        # Return exactly the fields expected by cli.py
        # ---------------------------------------------------------------------

        return {
            "documents": len(documents),

            "chunks": collection.points_count or 0,

            "disk_mb": disk_mb,

            "last_ingest": last_ingest,
        }

    # =========================================================================
    # HYBRID SEARCH
    # =========================================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
        role: str = "viewer",
    ) -> list[dict]:
        """
        Hybrid BM25 + dense vector search.

        RBAC is enforced inside Qdrant.

        `role` is treated only as a filter value supplied by the authenticated
        session upstream.
        """

        # ---------------------------------------------------------------------
        # Generate embeddings
        # ---------------------------------------------------------------------

        try:

            dense_vector = _embed_dense(
                query
            )

            sparse_vector = _SparseEmbedder.embed(
                query
            )

        except Exception:

            logger.exception(
                "Embedding step failed for query %r",
                query,
            )

            return []

        # ---------------------------------------------------------------------
        # Build access-control filter
        # ---------------------------------------------------------------------

        must_conditions = [

            FieldCondition(
                key="allowed_roles",

                match=MatchAny(
                    any=[role]
                ),
            )

        ]

        # Optional document type filtering
        if doc_type is not None:

            must_conditions.append(

                FieldCondition(
                    key="doc_type",

                    match=MatchValue(
                        value=doc_type
                    ),
                )

            )

        access_filter = Filter(
            must=must_conditions
        )

        # ---------------------------------------------------------------------
        # Hybrid retrieval
        # ---------------------------------------------------------------------

        try:

            response = self._client.query_points(

                collection_name=COLLECTION_NAME,

                prefetch=[

                    # ---------------------------------------------------------
                    # Dense semantic retrieval
                    # ---------------------------------------------------------

                    Prefetch(
                        query=dense_vector,

                        using="dense",

                        filter=access_filter,

                        limit=top_k * 4,
                    ),

                    # ---------------------------------------------------------
                    # Sparse BM25 retrieval
                    # ---------------------------------------------------------

                    Prefetch(
                        query=sparse_vector,

                        using="sparse",

                        filter=access_filter,

                        limit=top_k * 4,
                    ),

                ],

                # -------------------------------------------------------------
                # Reciprocal Rank Fusion
                # -------------------------------------------------------------

                query=FusionQuery(
                    fusion=Fusion.RRF
                ),

                # -------------------------------------------------------------
                # Apply RBAC at final query level too
                # -------------------------------------------------------------

                query_filter=access_filter,

                limit=top_k,

                with_payload=True,
            )

        except Exception:

            logger.exception(
                "Qdrant query failed for query %r (role=%s)",
                query,
                role,
            )

            return []

        # ---------------------------------------------------------------------
        # No results
        # ---------------------------------------------------------------------

        points = response.points

        if not points:
            return []

        # ---------------------------------------------------------------------
        # Convert Qdrant points into application results
        # ---------------------------------------------------------------------

        results = []

        for point in points:

            payload = point.payload or {}

            results.append(
                {
                    "chunk": payload.get(
                        "chunk",
                        "",
                    ),

                    "source": payload.get(
                        "source",
                        "",
                    ),

                    "score": float(
                        point.score
                    ),

                    "doc_id": payload.get(
                        "doc_id",
                        "",
                    ),

                    "sensitivity": payload.get(
                        "sensitivity",
                        "",
                    ),
                }
            )

        return results


# =============================================================================
# SINGLETON
# =============================================================================

_store: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    """
    Return the shared KnowledgeStore instance.
    """

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
        role="tech_lead",
    )

    for result in results:

        print(result)