"""
ingest.py — Document ingestion pipeline: watch folder → chunk → embed → store.

Supported file types: .pdf, .docx, .txt, .md, .eml
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from sovereignai.config import get_config

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".eml", ".csv"}


def ingest_path(
    path: Path,
    recursive: bool = True,
    verbose: bool = False,
) -> dict[str, int]:
    """Ingest a file or directory into the knowledge base."""
    files = _collect_files(path, recursive)
    stats = {"docs": 0, "chunks": 0, "skipped": 0}

    for f in files:
        try:
            n = _ingest_file(f, verbose=verbose)
            stats["docs"] += 1
            stats["chunks"] += n
        except Exception as e:
            if verbose:
                print(f"  ⚠  Skipped {f.name}: {e}")
            stats["skipped"] += 1

    return stats


def _collect_files(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() in _SUPPORTED_EXTENSIONS:
            return [path]
        return []
    files = []
    glob = path.rglob("*") if recursive else path.glob("*")
    for f in glob:
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS:
            files.append(f)
    return sorted(files)


def _ingest_file(path: Path, verbose: bool = False) -> int:
    """Ingest a single file. Returns number of chunks added."""
    from sovereignai.knowledge_base.store import get_store, _embed

    cfg = get_config()
    store = get_store()
    suffix = path.suffix.lower()

    if verbose:
        print(f"  📄  Ingesting {path.name} …", end=" ")

    # Extract text
    if suffix == ".pdf":
        text = _extract_pdf(path)
    elif suffix == ".docx":
        text = _extract_docx(path)
    elif suffix in (".txt", ".md", ".csv", ".eml"):
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported: {suffix}")

    if not text or not text.strip():
        raise ValueError("No text extracted")

    # Detect doc type
    doc_type = _detect_doc_type(path, text)

    # Chunk the text
    chunks = _chunk_text(text, cfg.kb_chunk_size, cfg.kb_chunk_overlap)

    if verbose:
        print(f"{len(chunks)} chunks")

    ingested_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    count = 0

    for i, chunk in enumerate(chunks):
        # Stable, reproducible ID for upsert idempotency
        doc_id = _chunk_id(str(path), i)
        embedding = _embed(chunk)
        if embedding is None:
            continue

        store.upsert(
            doc_id=doc_id,
            text=chunk,
            embedding=embedding,
            metadata={
                "source_path": str(path),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "doc_type": doc_type,
                "ingested_at": ingested_at,
                "file_name": path.name,
            },
        )
        count += 1

    return count


def _extract_pdf(path: Path) -> str:
    """Extract text from PDF. Tries text layer first, OCR fallback."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        pages = [page.get_text() for page in doc]
        doc.close()
        text = "\n\n".join(pages)
        if text.strip():
            return text
    except ImportError:
        pass

    # If no text layer and vision model is available, we can use it
    # but for ingestion we just return empty (the vision_tool handles runtime OCR)
    return ""


def _extract_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise RuntimeError("python-docx not installed. Run: pip install python-docx")


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple word-based chunking with overlap."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap

    return chunks


def _detect_doc_type(path: Path, text: str) -> str:
    name_lower = path.name.lower()
    text_lower = text[:500].lower()
    if "sop" in name_lower or "procedure" in text_lower:
        return "sop"
    elif "manual" in name_lower or "handbook" in text_lower:
        return "manual"
    elif path.suffix.lower() == ".eml" or "from:" in text_lower:
        return "correspondence"
    elif "report" in name_lower:
        return "report"
    return "document"


def _chunk_id(source_path: str, chunk_index: int) -> str:
    raw = f"{source_path}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def watch_path(path: Path) -> None:
    """Watch a directory and re-ingest on file changes (blocking)."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory:
                    p = Path(event.src_path)
                    if p.suffix.lower() in _SUPPORTED_EXTENSIONS:
                        print(f"  🔄  Re-ingesting {p.name} …")
                        try:
                            n = _ingest_file(p, verbose=True)
                            print(f"  ✅  {n} chunks updated.")
                        except Exception as e:
                            print(f"  ❌  {e}")

            on_created = on_modified

        observer = Observer()
        observer.schedule(Handler(), str(path), recursive=True)
        observer.start()
        print(f"👁  Watching {path} … (Ctrl+C to stop)")
        try:
            import time as _time
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    except ImportError:
        raise RuntimeError("watchdog not installed. Run: pip install watchdog")

