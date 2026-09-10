"""
scripts/ingest_docs_to_supabase.py

Production Ingestion Pipeline:
1. Authenticates against Supabase as Admin to acquire JWT session.
2. Parses documents from DOCS/ (PDF format) using pypdf.
3. Splits text into semantic chunks (~1200-1600 characters) with overlap.
4. Generates real 1536-dimensional embeddings using OpenAI's text-embedding-3-small.
5. Upserts documents into public.documents and vector chunks into public.document_chunks.
"""

import os
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
# OpenAI Embedding Helper
# ---------------------------------------------------------------------------
def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed text inputs using OpenAI text-embedding-3-small (1536 dims)."""
    clean_texts = [t.replace("\n", " ").strip() for t in texts]
    clean_texts = [t if len(t) > 0 else "empty" for t in clean_texts]

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
                # Ensure ordered results matching input
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in sorted_data]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                print(f"Rate limited, waiting 3s before retry {attempt+1}...")
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
# Text Extraction & Chunking
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str, max_pages: int = 30) -> list[tuple[int, str]]:
    """Extract page number and text from a PDF up to max_pages."""
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
        print(f"Error reading {pdf_path}: {e}")
    return pages


def chunk_pages(
    pages: list[tuple[int, str]], chunk_size: int = 1400, overlap: int = 150
) -> list[dict]:
    """Create overlapping semantic chunks tagged with source page."""
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
def ingest_document(
    token: str,
    title: str,
    category: str,
    storage_path: str,
    chunks: list[dict],
) -> str | None:
    if not chunks:
        print(f"Skipping {title}: No text chunks extracted.")
        return None

    print(f"\nIngesting '{title}' ({category}) - {len(chunks)} chunks...")

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

    # 2. Batch generate embeddings (batches of 25)
    batch_size = 25
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

        print(f"  Embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks...")
        time.sleep(0.3)  # Gentle pacing

    # 3. Insert chunks into document_chunks
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

    print(f"  Successfully saved {len(chunk_records)} chunks to Supabase!")
    return doc_id


# ---------------------------------------------------------------------------
# Document Ingestion Manifest
# ---------------------------------------------------------------------------
MANIFEST = [
    # 1. Complete Enterprise Operations Report (Cross-department: 3 role views)
    {
        "path": "DOCS/complete_enterprise_operations_report.pdf",
        "title": "NovaBridge Operations - Financial Performance & Departmental Budgets",
        "category": "finance",
        "max_pages": 8,
    },
    {
        "path": "DOCS/complete_enterprise_operations_report.pdf",
        "title": "NovaBridge Operations - Engineering Architecture & Services",
        "category": "tech",
        "max_pages": 8,
    },
    {
        "path": "DOCS/complete_enterprise_operations_report.pdf",
        "title": "NovaBridge Operations - IT Support Desk, SLA & Incidents",
        "category": "support",
        "max_pages": 8,
    },
    # 2. IT Support Knowledge Bases
    {
        "path": "DOCS/Support/it_helpdesk_knowledge_base.pdf",
        "title": "IT Helpdesk Knowledge Base: VPN, Remote Access & Password Reset",
        "category": "support",
        "max_pages": 15,
    },
    {
        "path": "DOCS/Support/it_helpdesk_knowledge_base_v2.pdf",
        "title": "IT Helpdesk Knowledge Base v2: Equipment Requests & Identity Services",
        "category": "support",
        "max_pages": 15,
    },
    {
        "path": "DOCS/Support/it_helpdesk_knowledge_base_v3.pdf",
        "title": "IT Helpdesk Knowledge Base v3: Network Troubleshooting & Incident Runbooks",
        "category": "support",
        "max_pages": 15,
    },
    # 3. Departmental Budget & Expenses
    {
        "path": "DOCS/Synthetic Quarterly budget expense/synthetic_quarterly_departmental_budget_expense_report.pdf",
        "title": "Quarterly Departmental Budget & Variance Report Q3 2026",
        "category": "finance",
        "max_pages": 15,
    },
    {
        "path": "DOCS/Synthetic Quarterly budget expense/synthetic_quarterly_budget_expense_report_v2.pdf",
        "title": "Quarterly Budget & Expense Review Q2 2026",
        "category": "finance",
        "max_pages": 15,
    },
    {
        "path": "DOCS/Synthetic Quarterly budget expense/synthetic_quarterly_budget_expense_report_v3.pdf",
        "title": "Quarterly Budget Planning & Departmental Capex Q4 2026",
        "category": "finance",
        "max_pages": 15,
    },
    # 4. Engineering Guides & Onboarding
    {
        "path": "DOCS/guide/synthetic_engineering_onboarding_guide.pdf",
        "title": "Engineering Onboarding Handbook & Architecture Guidelines",
        "category": "tech",
        "max_pages": 20,
    },
    {
        "path": "DOCS/guide/onboarding_guide_for_engineers.pdf",
        "title": "Engineer Environment Setup & Core Development Workflows",
        "category": "tech",
        "max_pages": 15,
    },
    {
        "path": "DOCS/guide/new_engineering_onboarding_overview.pdf",
        "title": "Engineering Platform Overview & Distributed Systems Architecture",
        "category": "tech",
        "max_pages": 20,
    },
    {
        "path": "DOCS/guide/synthetic_engineering_onboarding_guide_v2.pdf",
        "title": "Engineering Systems Guide v2: Code Standards & CI/CD Pipelines",
        "category": "tech",
        "max_pages": 20,
    },
    # 5. Indian Oil Corporation Limited (IOCL) - Annual Reports & Operational Reviews
    {
        "path": "DOCS/Indian Oil-Budget_Report/SingleAnnualReport202324.pdf",
        "title": "Indian Oil Corporation Ltd - Annual Report 2023-24 (Financial & Operations Review)",
        "category": "finance",
        "max_pages": 25,
    },
    {
        "path": "DOCS/Indian Oil-Budget_Report/IndianOil_AR_2022-23_30_07_23.pdf",
        "title": "Indian Oil Corporation Ltd - Integrated Annual Report 2022-23 (Refinery & Strategic Performance)",
        "category": "finance",
        "max_pages": 25,
    },
    {
        "path": "DOCS/Indian Oil-Budget_Report/IOCL-Annual_Report_2016-17.pdf",
        "title": "Indian Oil Corporation Ltd - Annual Report 2016-17 (Refinery Operations & Energy Transition)",
        "category": "finance",
        "max_pages": 25,
    },
    # 6. Corporate Bylaws & Governance
    {
        "path": "DOCS/Bylaws/sample corporate bylaws.pdf",
        "title": "Corporate Governance Bylaws & Operational Regulations",
        "category": "admin",
        "max_pages": 15,
    },
    {
        "path": "DOCS/Bylaws/Basic Corporate Bylaws.pdf",
        "title": "Basic Corporate Operating Bylaws & Committee Guidelines",
        "category": "admin",
        "max_pages": 15,
    },
]


def main():
    print("=" * 65)
    print("SOVEREIGN AI WORKBENCH - SUPABASE RAG INGESTION PIPELINE")
    print(f"Company: Indian Oil Corporation Limited (ID: {COMPANY_ID})")
    print("=" * 65)

    print("Authenticating admin session...")
    token = get_admin_token()
    print("Admin authenticated successfully.")

    ingested_count = 0
    total_chunks = 0

    for item in MANIFEST:
        pdf_path = item["path"]
        if not os.path.exists(pdf_path):
            print(f"Warning: File not found {pdf_path}")
            continue

        pages = extract_text_from_pdf(pdf_path, max_pages=item["max_pages"])
        chunks = chunk_pages(pages)

        doc_id = ingest_document(
            token=token,
            title=item["title"],
            category=item["category"],
            storage_path=pdf_path,
            chunks=chunks,
        )

        if doc_id:
            ingested_count += 1
            total_chunks += len(chunks)

    print("\n" + "=" * 65)
    print(f"INGESTION COMPLETE!")
    print(f"Total Documents: {ingested_count}")
    print(f"Total Vector Chunks: {total_chunks}")
    print("=" * 65)


if __name__ == "__main__":
    main()
