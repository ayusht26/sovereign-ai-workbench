"""
agent/sovereignai/knowledge_base/ingest.py

Ingestion pipeline:

    extract -> chunk -> embed (dense + sparse) -> upsert into Qdrant

Qdrant payload contains:
    - chunk
    - doc_id
    - source
    - sensitivity
    - allowed_roles
    - chunk_index
    - optional doc_type

This module also exposes ingest_path(), which is used by the CLI:

    sovai kb add <path>
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import tiktoken
from qdrant_client.models import PointStruct

from sovereignai.config import cfg

from sovereignai.knowledge_base.store import (
    COLLECTION_NAME,
    QdrantClient,
    QDRANT_HOST,
    QDRANT_PORT,
    _SparseEmbedder,
    _embed_dense,
    ensure_collection,
)

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


# ---------------------------------------------------------------------------
# Qdrant client
# ---------------------------------------------------------------------------

def _get_client() -> QdrantClient:
    global _client

    if _client is None:
        _client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
        )
        ensure_collection(_client)

    return _client


# ---------------------------------------------------------------------------
# 1. Text extraction
# ---------------------------------------------------------------------------

def _extract_text(path: str) -> str:
    """
    Extract text from a supported document.

    Supported:
        .pdf
        .txt
        .md

    PDF files are first processed using PyMuPDF.

    If a PDF appears to be scanned/image-based, ingestion fails clearly
    because the current vision_tool.py does not expose a standalone
    transcribe_image() function.
    """

    suffix = Path(path).suffix.lower()

    # -----------------------------------------------------------------------
    # PDF
    # -----------------------------------------------------------------------

    if suffix == ".pdf":
        import fitz

        doc = fitz.open(path)

        try:
            pages_text = [
                page.get_text()
                for page in doc
            ]
        finally:
            doc.close()

        if not pages_text:
            raise ValueError(
                f"PDF contains no pages: {path}"
            )

        total_chars = sum(
            len(text.strip())
            for text in pages_text
        )

        # Detect scanned/image-based PDFs.
        if total_chars < 20 * len(pages_text):
            logger.warning(
                "PDF %s appears to be scanned/image-based. "
                "Only %d characters were extracted.",
                path,
                total_chars,
            )

            raise RuntimeError(
                "This PDF appears to be scanned/image-based. "
                "The current VisionTool does not expose a "
                "transcribe_image() function, so scanned-PDF ingestion "
                "is not currently supported."
            )

        return "\n\n".join(pages_text)

    # -----------------------------------------------------------------------
    # TXT / Markdown
    # -----------------------------------------------------------------------

    if suffix in (".txt", ".md"):
        return Path(path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    # -----------------------------------------------------------------------
    # Unsupported format
    # -----------------------------------------------------------------------

    raise ValueError(
        f"Unsupported file type for ingestion: {suffix}"
    )


# ---------------------------------------------------------------------------
# 2. Chunking
# ---------------------------------------------------------------------------

_ENCODING = tiktoken.get_encoding("cl100k_base")


def _chunk_text(
    text: str,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
) -> list[str]:
    """
    Token-based sliding-window chunking.
    """

    tokens = _ENCODING.encode(text)

    if not tokens:
        return []

    chunks: list[str] = []

    step = max(
        chunk_size_tokens - chunk_overlap_tokens,
        1,
    )

    for start in range(0, len(tokens), step):

        window = tokens[
            start:start + chunk_size_tokens
        ]

        if not window:
            break

        chunks.append(
            _ENCODING.decode(window)
        )

        if start + chunk_size_tokens >= len(tokens):
            break

    return chunks


# ---------------------------------------------------------------------------
# 3-4. Embed + upsert
# ---------------------------------------------------------------------------

def ingest_document(
    path: str,
    doc_id: str,
    sensitivity: str,
    allowed_roles: list[str],
    doc_type: str | None = None,
) -> None:
    """
    Extract -> chunk -> embed -> upsert a single document into Qdrant.

    allowed_roles is explicitly required so that access control is not
    accidentally omitted during ingestion.
    """

    if not allowed_roles:
        raise ValueError(
            f"ingest_document({doc_id}) called with empty allowed_roles. "
            "Refusing to ingest a document with no authorized roles."
        )

    # -----------------------------------------------------------------------
    # Extract text
    # -----------------------------------------------------------------------

    text = _extract_text(path)

    # -----------------------------------------------------------------------
    # Chunk text
    # -----------------------------------------------------------------------

    chunks = _chunk_text(
        text,
        cfg.kb_chunk_size,
        cfg.kb_chunk_overlap,
    )

    if not chunks:
        logger.warning(
            "No text extracted from %s (doc_id=%s); nothing ingested",
            path,
            doc_id,
        )
        return

    # -----------------------------------------------------------------------
    # Qdrant client
    # -----------------------------------------------------------------------

    client = _get_client()

    points: list[PointStruct] = []

    # -----------------------------------------------------------------------
    # Embed every chunk
    # -----------------------------------------------------------------------

    for i, chunk in enumerate(chunks):

        try:
            # Dense embedding through local Ollama.
            dense_vector = _embed_dense(chunk)

            # Sparse BM25 embedding.
            sparse_vector = _SparseEmbedder.embed(chunk)

        except Exception:
            logger.exception(
                "Embedding failed for chunk %d of %s "
                "(doc_id=%s); skipping chunk",
                i,
                path,
                doc_id,
            )
            continue

        # -------------------------------------------------------------------
        # Payload
        # -------------------------------------------------------------------

        payload = {
            "chunk": chunk,
            "doc_id": doc_id,
            "source": path,
            "sensitivity": sensitivity,
            "allowed_roles": allowed_roles,
            "chunk_index": i,
        }

        if doc_type is not None:
            payload["doc_type"] = doc_type

        # -------------------------------------------------------------------
        # Qdrant point
        # -------------------------------------------------------------------

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": dense_vector,
                    "sparse": sparse_vector,
                },
                payload=payload,
            )
        )

    # -----------------------------------------------------------------------
    # Nothing successfully embedded
    # -----------------------------------------------------------------------

    if not points:
        logger.error(
            "All chunks failed to embed for %s "
            "(doc_id=%s); nothing upserted",
            path,
            doc_id,
        )
        return

    # -----------------------------------------------------------------------
    # Upsert into Qdrant
    # -----------------------------------------------------------------------

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    logger.info(
        "Ingested %d chunks from %s (doc_id=%s)",
        len(points),
        path,
        doc_id,
    )


# ---------------------------------------------------------------------------
# 5. CLI path ingestion
# ---------------------------------------------------------------------------

def ingest_path(
    path: str | Path,
    recursive: bool = True,
    verbose: bool = False,
) -> dict:
    """
    Ingest a single file or a directory.

    This function matches the contract expected by sovereignai.cli:

        stats = ingest_path(
            path,
            recursive=recursive,
            verbose=True,
        )

    Returns:

        {
            "docs": number of successfully processed documents,
            "chunks": number of chunks processed,
        }

    Supported files:

        .pdf
        .txt
        .md
    """

    target = Path(path).resolve()

    if not target.exists():
        raise FileNotFoundError(
            f"Path not found: {target}"
        )

    # -----------------------------------------------------------------------
    # Build list of files
    # -----------------------------------------------------------------------

    if target.is_file():

        suffix = target.suffix.lower()

        if suffix not in (
            ".pdf",
            ".txt",
            ".md",
        ):
            raise ValueError(
                f"Unsupported file type for ingestion: {suffix}"
            )

        files = [target]

    elif target.is_dir():

        if recursive:
            files = [
                p
                for p in target.rglob("*")
                if p.is_file()
            ]
        else:
            files = [
                p
                for p in target.iterdir()
                if p.is_file()
            ]

        files = [
            p
            for p in files
            if p.suffix.lower() in (
                ".pdf",
                ".txt",
                ".md",
            )
        ]

    else:
        raise ValueError(
            f"Unsupported path: {target}"
        )

    # -----------------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------------

    stats = {
        "docs": 0,
        "chunks": 0,
    }

    # -----------------------------------------------------------------------
    # No supported files
    # -----------------------------------------------------------------------

    if not files:

        if verbose:
            print(
                f"⚠️  No supported documents found in: {target}"
            )

        return stats

    # -----------------------------------------------------------------------
    # Process every file
    # -----------------------------------------------------------------------

    for file_path in files:

        if verbose:
            print(
                f"📄 Ingesting: {file_path}"
            )

        try:

            # Extract text first.
            text = _extract_text(
                str(file_path)
            )

            # Calculate chunks.
            chunks = _chunk_text(
                text,
                cfg.kb_chunk_size,
                cfg.kb_chunk_overlap,
            )

            if not chunks:

                logger.warning(
                    "No text extracted from %s; skipping",
                    file_path,
                )

                if verbose:
                    print(
                        "   ⚠️  No text extracted; skipped"
                    )

                continue

            # Perform the actual embedding + Qdrant upsert.
            ingest_document(
                path=str(file_path),
                doc_id=file_path.stem,
                sensitivity="internal",
                allowed_roles=[
                    "admin",
                    "officer",
                    "employee",
                ],
                doc_type=None,
            )

            stats["docs"] += 1
            stats["chunks"] += len(chunks)

            if verbose:
                print(
                    f"   ✓ {len(chunks)} chunks"
                )

        except Exception as exc:

            logger.exception(
                "Failed to ingest %s",
                file_path,
            )

            if verbose:
                print(
                    f"   ❌ Failed: {exc}"
                )

            # Continue processing other files when a directory is supplied.
            # For a single file, propagate the error so the CLI shows the
            # actual failure.
            if target.is_file():
                raise

    return stats


# ---------------------------------------------------------------------------
# Module CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "usage: python -m sovereignai.knowledge_base.ingest "
            "<path> [recursive]"
        )
        sys.exit(1)

    input_path = sys.argv[1]

    recursive = True

    if len(sys.argv) > 2:
        recursive = sys.argv[2].lower() not in (
            "false",
            "0",
            "no",
        )

    stats = ingest_path(
        path=input_path,
        recursive=recursive,
        verbose=True,
    )

    print(
        f"\nDone — {stats['docs']} docs, "
        f"{stats['chunks']} chunks ingested."
    )