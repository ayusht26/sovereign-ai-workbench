"""
scripts/ingest_all_docs_to_supabase.py

Comprehensive Ingestion Pipeline for ALL Files in DOCS/:
- DOCS/complete_enterprise_operations_report.pdf
- DOCS/Bylaws/ (All 14 PDFs + 11 DOC files)
- DOCS/guide/ (All 9 PDFs)
- DOCS/Indian Oil-Budget_Report/ (All 14 Annual Reports)
- DOCS/Support/ (All 3 PDFs)
- DOCS/Synthetic Quarterly budget expense/ (All 3 PDFs)

Total: 55 distinct files across the entire corpus.
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
import pypdf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COMPANY_ID = "796b5531-d535-42c9-b79b-bf88a3048318"  # Indian Oil Corporation Limited
SUPABASE_URL = "https://tybbzdbglhfnpdvgvrjs.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5YmJ6ZGJnbGhmbnBkdmd2cmpzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5MDc5NjYsImV4cCI6MjEwMzQ4Mzk2Nn0.ooAz_wKezqDKd-XxKAI_xZlkY1Hu8w_Tk5EEtzyCYzo"
ADMIN_EMAIL = "admin@tatamotors-internal.com"
ADMIN_PASSWORD = "admin123"

OPENAI_API_KEY = (
    os.getenv("OPENAI_API_KEY")
    or os.getenv("VITE_OPENAI_API_KEY")
    or "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"
)

# ---------------------------------------------------------------------------
# Auth Helper
# ---------------------------------------------------------------------------
def get_admin_token() -> str:
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    payload = json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "apikey": ANON_KEY},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        return data["access_token"]


# ---------------------------------------------------------------------------
# OpenAI Batch Embeddings
# ---------------------------------------------------------------------------
def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    clean_texts = [t.replace("\n", " ").strip() for t in texts]
    clean_texts = [t[:7000] if len(t) > 0 else "empty" for t in clean_texts]

    url = "https://api.openai.com/v1/embeddings"
    payload = json.dumps({"model": "text-embedding-3-small", "input": clean_texts}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
    )

    for attempt in range(4):
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in sorted_data]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                print(f"Rate limited, sleeping 3s (retry {attempt+1})...", flush=True)
                time.sleep(3)
            else:
                body = e.read().decode()
                raise Exception(f"OpenAI Embedding API error ({e.code}): {body}")
        except Exception as ex:
            if attempt < 3:
                time.sleep(2)
            else:
                raise ex
    return []


# ---------------------------------------------------------------------------
# Text Extraction
# ---------------------------------------------------------------------------
def extract_text_pdf(pdf_path: str, max_pages: int = 20) -> list[tuple[int, str]]:
    pages = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        total = min(len(reader.pages), max_pages)
        for i in range(total):
            txt = reader.pages[i].extract_text() or ""
            txt = txt.strip()
            if len(txt) > 40:
                pages.append((i + 1, txt))
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}", flush=True)
    return pages


def extract_text_doc(doc_path: str) -> list[tuple[int, str]]:
    """Extract strings from binary Word .doc using UTF-16LE and ASCII heuristics."""
    try:
        with open(doc_path, "rb") as f:
            content = f.read()

        s_u16 = re.findall(rb"(?:[\x20-\x7E]\x00){4,}", content)
        t_u16 = " ".join(s.decode("utf-16le", errors="ignore") for s in s_u16)

        s_asc = re.findall(rb"[\x20-\x7E\r\n]{4,}", content)
        t_asc = " ".join(s.decode("latin-1", errors="ignore") for s in s_asc)

        text = t_u16 if len(t_u16) > len(t_asc) else t_asc
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 40:
            return [(1, text)]
    except Exception as e:
        print(f"Error reading DOC {doc_path}: {e}", flush=True)
    return []


def chunk_pages(
    pages: list[tuple[int, str]], chunk_size: int = 1500, overlap: int = 150
) -> list[dict]:
    chunks = []
    for page_num, text in pages:
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_txt = text[start:end].strip()
            if len(chunk_txt) > 50:
                chunks.append(
                    {
                        "page": page_num,
                        "content": f"[Page {page_num}] {chunk_txt}",
                    }
                )
            if end == len(text):
                break
            start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Supabase Ingestion
# ---------------------------------------------------------------------------
def ingest_single_document(
    token: str,
    title: str,
    category: str,
    storage_path: str,
    chunks: list[dict],
) -> str | None:
    if not chunks:
        return None

    # 1. Insert parent document
    doc_url = f"{SUPABASE_URL}/rest/v1/documents"
    doc_payload = json.dumps(
        {
            "company_id": COMPANY_ID,
            "category": category,
            "title": title,
            "storage_path": storage_path,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        doc_url,
        data=doc_payload,
        headers={
            "Content-Type": "application/json",
            "apikey": ANON_KEY,
            "Authorization": f"Bearer {token}",
            "Prefer": "return=representation",
        },
    )

    with urllib.request.urlopen(req) as resp:
        inserted = json.loads(resp.read().decode())
        doc_id = inserted[0]["id"]

    # 2. Batch embed and insert
    batch_size = 30
    chunk_records = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_texts = [c["content"] for c in batch]
        embeddings = get_embeddings_batch(batch_texts)

        for j, c in enumerate(batch):
            chunk_records.append(
                {
                    "document_id": doc_id,
                    "company_id": COMPANY_ID,
                    "category": category,
                    "chunk_index": i + j,
                    "content": c["content"],
                    "embedding": embeddings[j],
                }
            )
        time.sleep(0.15)

    # 3. Insert chunk records
    chunks_url = f"{SUPABASE_URL}/rest/v1/document_chunks"
    chunk_payload = json.dumps(chunk_records).encode("utf-8")

    req_chunk = urllib.request.Request(
        chunks_url,
        data=chunk_payload,
        headers={
            "Content-Type": "application/json",
            "apikey": ANON_KEY,
            "Authorization": f"Bearer {token}",
        },
    )

    with urllib.request.urlopen(req_chunk) as resp:
        pass

    return doc_id


# ---------------------------------------------------------------------------
# Main Orchestrator for All 55 Files
# ---------------------------------------------------------------------------
def main():
    print("=" * 70, flush=True)
    print("INGESTING ALL FILES IN DOCS/ INTO SUPABASE (55 FILES)", flush=True)
    print("=" * 70, flush=True)

    token = get_admin_token()
    print("Admin authenticated.", flush=True)

    # 1. First, clear existing documents to avoid duplicate runs
    print("Purging existing records for a pristine state...", flush=True)
    del_req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/documents?company_id=eq.{COMPANY_ID}",
        headers={"apikey": ANON_KEY, "Authorization": f"Bearer {token}"},
        method="DELETE",
    )
    with urllib.request.urlopen(del_req) as resp:
        pass
    print("Existing records cleared.", flush=True)

    # Build queue of ALL files in DOCS/
    file_queue = []

    # 1. complete_enterprise_operations_report.pdf
    ce_path = "DOCS/complete_enterprise_operations_report.pdf"
    if os.path.exists(ce_path):
        file_queue.append((ce_path, "NovaBridge Operations - Financial Performance & Departmental Budgets", "finance", 8))
        file_queue.append((ce_path, "NovaBridge Operations - Engineering Architecture & Services", "tech", 8))
        file_queue.append((ce_path, "NovaBridge Operations - IT Support Desk, SLA & Incidents", "support", 8))
        file_queue.append((ce_path, "NovaBridge Operations - Master Enterprise Report", "admin", 8))

    # 2. DOCS/Support/ (All files)
    sup_dir = "DOCS/Support"
    for f in sorted(os.listdir(sup_dir)):
        if f.endswith(".pdf"):
            p = os.path.join(sup_dir, f)
            t = f"IT Helpdesk Support Guide: {f.replace('.pdf', '').replace('_', ' ').title()}"
            file_queue.append((p, t, "support", 10))

    # 3. DOCS/Synthetic Quarterly budget expense/ (All files)
    synth_dir = "DOCS/Synthetic Quarterly budget expense"
    for f in sorted(os.listdir(synth_dir)):
        if f.endswith(".pdf"):
            p = os.path.join(synth_dir, f)
            t = f"Quarterly Budget & Expense Report: {f.replace('.pdf', '').replace('_', ' ').title()}"
            file_queue.append((p, t, "finance", 10))

    # 4. DOCS/guide/ (All files)
    guide_dir = "DOCS/guide"
    for f in sorted(os.listdir(guide_dir)):
        if f.endswith(".pdf"):
            p = os.path.join(guide_dir, f)
            t = f"Engineering & Onboarding Guide: {f.replace('.pdf', '').replace('_', ' ').replace('-', ' ').title()}"
            file_queue.append((p, t, "tech", 20))

    # 5. DOCS/Indian Oil-Budget_Report/ (All 14 Annual Reports)
    ioc_dir = "DOCS/Indian Oil-Budget_Report"
    for f in sorted(os.listdir(ioc_dir)):
        if f.endswith(".pdf"):
            p = os.path.join(ioc_dir, f)
            name_clean = f.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
            t = f"Indian Oil Corporation Ltd - {name_clean} (Operations & Financials)"
            file_queue.append((p, t, "finance", 18))

    # 6. DOCS/Bylaws/ (All 25 files: PDFs and DOCs)
    bylaws_dir = "DOCS/Bylaws"
    for f in sorted(os.listdir(bylaws_dir)):
        p = os.path.join(bylaws_dir, f)
        clean_title = f"Corporate Governance Bylaws: {f.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()}"
        if f.endswith(".pdf"):
            file_queue.append((p, clean_title, "admin", 15))
        elif f.endswith(".doc"):
            file_queue.append((p, clean_title, "admin", 1))

    print(f"Total items in ingestion queue: {len(file_queue)}", flush=True)

    total_chunks = 0
    successful_docs = 0

    for idx, (path, title, category, max_p) in enumerate(file_queue, 1):
        if path.endswith(".pdf"):
            pages = extract_text_pdf(path, max_pages=max_p)
        elif path.endswith(".doc"):
            pages = extract_text_doc(path)
        else:
            continue

        chunks = chunk_pages(pages)
        if not chunks:
            print(f"[{idx}/{len(file_queue)}] Skipped (no text extracted): {title}", flush=True)
            continue

        print(f"[{idx}/{len(file_queue)}] Ingesting '{title}' ({category}) - {len(chunks)} chunks...", flush=True)
        doc_id = ingest_single_document(token, title, category, path, chunks)
        if doc_id:
            successful_docs += 1
            total_chunks += len(chunks)

    print("\n" + "=" * 70, flush=True)
    print("ALL FILES INGESTION COMPLETE!", flush=True)
    print(f"Total Documents Ingested: {successful_docs}", flush=True)
    print(f"Total Vector Chunks Created: {total_chunks}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
