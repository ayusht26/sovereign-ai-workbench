# Sovereign AI Workbench (Bastion) — Comprehensive Viva & Technical Defense Guide

> **Project Name:** Sovereign AI Workbench (Codename: *Bastion*)  
> **Target Sector:** Public Sector Undertakings (PSUs e.g., Indian Oil Corporation Limited), Refineries, Heavy Engineering, Defense, and Regulated Industrial Enterprises.  
> **Core Value:** Air-Gapped Sovereign AI Architecture, Strict Multi-Tenant Departmental Row Level Security (RLS), Autonomous ReAct Tool Execution, Hybrid RAG with Citation Grounding, and Deterministic Office Deliverable Generation (.docx, .xlsx, .pptx).

---

## Table of Contents

1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [Complete Technology Stack & Justification ("Why?")](#2-complete-technology-stack--justification-why)
   - 2.1 Frontend Engineering Stack
   - 2.2 Agent Orchestrator & Execution Engine
   - 2.3 RAG, Database & Storage Infrastructure
   - 2.4 Security & Network Isolation
3. [System Architecture & Data Flow](#3-system-architecture--data-flow)
   - 3.1 High-Level Architectural Diagram
   - 3.2 Dual-Mode Topology: On-Premise Sovereign vs Enterprise Hybrid
   - 3.3 End-to-End Request Lifecycle
4. [Deep-Dive Module Breakdown](#4-deep-dive-module-breakdown)
   - 4.1 Frontend UI/UX & Client Deliverable Engine
   - 4.2 Autonomous Agent Orchestrator (Hand-Rolled ReAct Loop)
   - 4.3 Resident Model Router & Dynamic Tier Allocation
   - 4.4 Multi-Tenant RAG Pipeline & PostgreSQL Row Level Security (RLS)
   - 4.5 Sandboxed Code Execution & NetGuard Network Monitor
5. [Benefits & Value Proposition](#5-benefits--value-proposition)
   - 5.1 Benefits for Frontend & End-User Experience
   - 5.2 Benefits for the Agent Orchestration System
   - 5.3 Benefits for RAG & Enterprise Knowledge Retrieval
   - 5.4 Benefits for the Enterprise & Regulatory Compliance
6. [Tough Viva Questions & Examiner Defense (Q&A)](#6-tough-viva-questions--examiner-defense-qa)

---

## 1. Executive Summary & Problem Statement

### 1.1 The Context
Industrial facilities, critical infrastructure operators, and Public Sector Undertakings (PSUs) such as Indian Oil Corporation Limited (IOCL), Bharat Petroleum, and Tata Motors operate under severe regulatory frameworks (e.g., India's Digital Personal Data Protection Act, ISO/IEC 27001, and national security air-gap mandates). These organizations generate petabytes of confidential telemetry, refinery maintenance SOPs, piping and instrumentation diagrams (P&IDs), financial ledgers, and procurement bylaws.

### 1.2 The Problem We Are Solving

1. **The Cloud Data Exfiltration Dilemma:**
   - Standard commercial LLMs (OpenAI ChatGPT, Anthropic Claude Web, Google Gemini) require streaming sensitive operational data to external US/multinational cloud datacenters.
   - For an oil refinery or defense manufacturer, uploading an emergency shutdown SOP, pipeline pressure defect log, or annual capex audit to an external API constitutes a direct breach of corporate governance and national sovereignty.

2. **The "Internal Snooping" Problem in Enterprise RAG:**
   - Standard corporate RAG implementations dump all enterprise documents into a shared vector database.
   - When an IT support technician asks: *"What are the upcoming quarterly refinery margins?"* or *"Summarize executive board compensation"*, a naive vector search retrieves chunks from restricted corporate finance or governance documents.
   - Existing solutions rely on fragile prompt engineering (*"You are a helpful assistant, do not reveal finance secrets"*), which is trivially bypassed via prompt injection or role deception.

3. **The "Chatbot Toy" vs "Real Deliverable" Gap:**
   - Most generative AI interfaces are conversational toys that output markdown text blocks.
   - Plant managers, chief engineers, and finance controllers do not work in chat bubbles; they require **deterministic binary deliverables**: formal Word memos (`.docx`) with corporate headers and sign-off blocks, financial variance models with live formulas in Excel (`.xlsx`), and board-ready slide decks (`.pptx`).

4. **The Danger of Untrusted Code Execution:**
   - Autonomous coding agents must execute scripts to analyze industrial datasets or parse telemetry. If code runs on the host OS, a hallucinated or injected command (`rm -rf`, opening reverse TCP sockets, port scanning the internal plant SCADA network) can incapacitate physical machinery.

5. **Single-Model Inefficiency & GPU Bottlenecks:**
   - Deploying a monolithic 70B parameter model on-premise for every trivial greeting or summary overwhelms local VRAM (requiring expensive multi-GPU clusters like 8x A100/H100s). Conversely, using a 3B model for complex root-cause analysis yields hallucinations.

---

## 2. Complete Technology Stack & Justification ("Why?")

### 2.1 Frontend Engineering Stack

| Technology | Role / Usage | Why Chosen (Engineering Justification) |
|---|---|---|
| **React 19** | UI Component Architecture | Concurrent rendering, compiler-assisted memoization, and optimal DOM update lifecycles for high-frequency streaming of agent thought tokens and tool events. |
| **TypeScript 5.8** | Static Type Safety | Eliminates runtime interface errors across complex state machines (session state, RLS role permissions, retrieved chunks, file generation schemas). |
| **TanStack Start & TanStack Router** | Full-Stack Routing & SSR/Client Framework | Full type-safe routing, route-level loaders, built-in search params validation, and zero-bundle overhead client navigation. Provides robust client-side route guards for role-based authentication (`/admin` gated strictly to `role === 'admin'`). |
| **Vite 8** | Build Tooling & Dev Server | Lightning-fast Hot Module Replacement (HMR) and native Rollup-based tree-shaking for minimal production bundle footprint. |
| **Tailwind CSS v4** | UI Styling System | Zero-runtime CSS generation with high-performance CSS variables. Allows seamless theming for the industrial **"Obsidian Factory Dark"** control room aesthetic. |
| **Radix UI Primitives** | Headless UI Components | Fully unstyled, accessible (WAI-ARIA compliant) primitives for dialogs, popovers, dropdowns, accordions, and tabs without imposing stylistic bloat. |
| **Framer Motion 13 & GSAP + Lenis** | Dynamic Micro-Animations & Smooth Scrolling | Industrial interfaces require visual fluidity to indicate agent state (collapsible thought blocks, telemetry meters, parallax hero, file card expansions) without dropping frames. |
| **Client-Side Document Engines (`docx`, `xlsx`, `pptxgenjs`)** | In-Browser Deliverable Generation | Enables instant compilation of binary `.docx`, `.xlsx`, and `.pptx` files **directly inside the user's browser memory**. Eliminates the need to send generated report contents back to a server, preserving complete client-side data privacy. |
| **Recharts** | Telemetry & Analytics Visualization | Lightweight SVG charting for the Admin Dashboard (daily query volume, department category breakdown, user activity trends). |
| **Sonner** | Toast Notification System | Minimalist, non-blocking toast notifications for permission denials, file download readiness, and session events. |

---

### 2.2 Agent Orchestrator & Execution Engine

| Technology | Role / Usage | Why Chosen (Engineering Justification) |
|---|---|---|
| **Python 3.11+** | Core Agent Runtime | Modern async/await primitives, native typing enhancements, fast startup time, and unmatched ecosystem support for machine learning, PDF parsing, and system monitoring. |
| **Textual (v0.85+) & Rich** | Terminal User Interface (TUI) | In industrial control rooms and air-gapped server vaults, graphical desktop environments (X11/Wayland/browsers) are often disabled for security hardening. Textual provides a full reactive terminal UI with mouse support, keyboard shortcuts (`Ctrl+P`, `Esc`), split panes, and live token streaming. |
| **Typer** | CLI Framework | Type-hinted command-line parser for commands (`bastion doctor`, `bastion kb status`, `bastion audit export`, `bastion models list`). |
| **Hand-Rolled ReAct Loop (`agent_loop.py`)** | Agent Orchestration Engine | **Deliberately avoids heavyweight black-box frameworks like LangChain or AutoGen.** A custom plan → act → observe → iterate loop provides 100% deterministic control over tool call execution, token streaming, anti-loop deduplication, retry nudging, and early cancellation (`session.cancelled`). |
| **Resident Model Router (`router.py`)** | Zero-Latency Task Classifier | Evaluates user prompts with zero temperature to classify intent into 6 distinct categories (`general`, `coding`, `vision`, `spreadsheet`, `document_qa`, `planning`) and assigns the task to the most resource-efficient model tier. |
| **Docker SDK (`docker>=7.1.0`)** | Sandboxed Execution Engine | Spawns isolated ephemeral containers with `--network=none`, strict RAM quotas (2 GB), CPU quotas (2.0 cores), and read-only root filesystems to run Python, Node.js, C, C++, or Bash code safely. |
| **Network Guard (`psutil`, `net_guard/`)** | Egress Packet & Socket Monitor | Background daemon polling system network sockets every 500ms to detect and log unauthorized outbound connections, validating the air-gap boundary. |
| **Server Document Generators (`python-docx`, `python-pptx`, `openpyxl`, `pymupdf`)** | Native Office Document Compilation | Server/agent-side compilation of documents with authentic typography, tables, and corporate classification watermarks. |

---

### 2.3 RAG, Database & Storage Infrastructure

| Technology | Role / Usage | Why Chosen (Engineering Justification) |
|---|---|---|
| **PostgreSQL 15+** | Relational Core Database | ACID-compliant relational storage for multi-tenant companies, user profiles, document metadata, and immutable audit logs. |
| **pgvector Extension** | Native Vector Similarity Store | Enables high-dimensional vector search directly inside PostgreSQL. Eliminates the complexity and data synchronization hazards of running a separate external vector database (such as Pinecone or Milvus). |
| **Row Level Security (RLS)** | Kernel-Level Security Isolation | PostgreSQL RLS guarantees that queries executed by a user authenticated under a specific role (`tech`, `finance`, `support`) can **never** read or match document chunks belonging to another department, even if the similarity score is 1.0. |
| **OpenAI `text-embedding-3-small` (1536 dims)** | Dense Semantic Representation | State-of-the-art semantic retrieval performance with compact vector dimensionality (1536-dim) optimized for enterprise manuals. |
| **Deterministic Local L2-Normalized Hash Fallback** | Offline / Air-Gapped Fallback Embedding | When external network calls or embedding APIs are completely unreachable, the system generates deterministic 1536-dimensional pseudo-embeddings, ensuring the vector similarity math never crashes the database RPC. |
| **PyMuPDF (`fitz`) & pypdf** | PDF Extraction & OCR Cleansing | High-throughput parsing of complex industrial PDFs (IOCL annual reports, engineering manuals), stripping corrupted OCR control codes (`\x00-\x1F`, private-use characters). |

---

## 3. System Architecture & Data Flow

### 3.1 High-Level Architectural Diagram

```
+-----------------------------------------------------------------------------------+
|                                CLIENT LAYER                                       |
|                                                                                   |
|   +---------------------------------------+   +-------------------------------+   |
|   |         React 19 Web Client           |   |       Textual / Rich TUI      |   |
|   | (TanStack Router, Obsidian Theme,    |   | (Air-Gapped Console Terminal, |   |
|   | In-Browser DocGen: docx/xlsx/pptx)    |   | Keyboard Shortcuts, Streams)  |   |
|   +---------------------------------------+   +-------------------------------+   |
+---------------------------------------|-------------------------------|-----------+
                                        |                               |
                                        v                               v
+-----------------------------------------------------------------------------------+
|                        SECURITY & ROUTING GATEWAY                                 |
|                                                                                   |
|   +-------------------------------------+   +---------------------------------+   |
|   |   Application Department Guard      |   |       Resident Model Router     |   |
|   | (Validates role boundary:           |   | (Classifies: General, Coding,   |   |
|   | Tech vs Finance vs Support vs Admin)|   | Vision, Spreadsheet, Planning)  |   |
|   +-------------------------------------+   +---------------------------------+   |
+---------------------------------------|-------------------------------------------+
                                        |
                 +----------------------+----------------------+
                 |                                             |
                 v                                             v
+----------------------------------+         +----------------------------------+
|      RAG RETRIEVAL ENGINE        |         |    AUTONOMOUS RE-ACT ENGINE      |
|                                  |         |                                  |
| 1. Full-Text Ranked RPC          |         | Plan -> Act -> Observe -> Iterate|
| 2. pgvector Semantic Search RPC  |         |                                  |
| 3. Domain Multi-Keyword Fallback |         | +-- Tool Registry: -------------+|
|                                  |         | | fs_read / fs_write            ||
|                                  |         | | sandbox_exec (Docker net:none)||
|                                  |         | | generate_docx / pptx / xlsx   ||
|                                  |         | | sheet_tool / vision_tool      ||
|                                  |         | +-------------------------------+|
+-----------------|----------------+         +-----------------|----------------+
                  |                                            |
                  v                                            v
+----------------------------------+         +----------------------------------+
|   SUPABASE / POSTGRESQL (RLS)    |         |        LOCAL NETWORK GUARD       |
|                                  |         |                                  |
| - companies & profiles           |         | - psutil socket watcher (500ms)  |
| - documents & document_chunks    |         | - RFC-1918 / Loopback whitelist  |
| - document_access_logs (Audit)   |         | - Host OS Firewall verification  |
| - auth_profile() SecurityDefiner |         | - Tamper-evident session export  |
+----------------------------------+         +----------------------------------+
```

---

### 3.2 Dual-Mode Topology: On-Premise Sovereign vs Enterprise Hybrid

The project is intentionally architected to demonstrate **two operational topologies**:

```
MODE A: 100% AIR-GAPPED ON-PREMISE (Defense / Refinery Unit-4)
User (Terminal) ──> Textual TUI ──> Hand-Rolled Loop ──> Local vLLM / Ollama (localhost:11434)
                                         │                    ├── Qwen3.5-9B (General)
                                         │                    ├── Qwen3-Coder-Next (Coding)
                                         │                    └── Qwen3-VL-32B (Vision)
                                         ├──> Docker Sandbox (--network=none)
                                         └──> Local PostgreSQL + pgvector (Air-gapped)

MODE B: MULTI-TENANT ENTERPRISE CLOUD / HYBRID (Corporate Headquarters)
User (Browser) ──> React 19 Client ──> TanStack Start ──> OpenAI API / Gateway Proxy
                                           │                   ├── gpt-4o-mini (Fast inference)
                                           │                   └── DALL-E (Asset synthesis)
                                           ├──> Supabase Cloud (PostgreSQL + RLS + pgvector)
                                           └──> In-Browser Deliverable Engine (docx/xlsx/pptx)
```

---

### 3.3 End-to-End Request Lifecycle

#### Scenario 1: Authorized Retrieval & File Generation
1. **User Request:** A Finance Lead asks: *"Extract the Q3 refinery margins from the IOCL report and compile an executive briefing memo."*
2. **Auth & Role Check:** Session verifies user is authenticated with `role = 'finance'` and `company_id = '796b...'`.
3. **Application Guard:** `validateRoleAccess()` checks if query violates role boundaries. Query is within finance domain $\rightarrow$ **Allowed**.
4. **Model Router:** Classifies task as `general` (deliverable generation intent) with high confidence. Displays `Qwen3.6-27B` (Reasoning Tier).
5. **Hybrid RAG Retrieval:**
   - Client embeds query into 1536-dim vector.
   - Calls `search_document_chunks_ranked` / `match_document_chunks` RPC.
   - **PostgreSQL RLS** restricts search to `company_id` and `category = 'finance'`.
   - Chunks from *Indian Oil Budget & Margin Report* are returned with similarity scores (e.g., 0.94).
6. **Audit Log:** Row inserted into `document_access_logs` recording `user_id`, `document_id`, `action='query'`, and query text.
7. **Synthesis & Tool Invocation:** The model formats the findings and triggers the deliverable engine.
8. **Binary Compilation:** `generateDocxFile()` builds a real `.docx` file in client memory containing formatted headers, tables, and IOCL citations.
9. **Presentation:** User receives the streamed textual answer alongside a clickable, downloadable **File Deliverable Card**.

#### Scenario 2: Cross-Department Snooping Prevention (The Security Boundary)
1. **Malicious / Unauthorized Request:** A Tech Engineer asks: *"Show me the executive salary and dividend payout ledger from the annual finance report."*
2. **Layer 1 Defense (Application Guard):**
   - `validateRoleAccess()` intercepts prompt.
   - Detects user role is `tech` and target domain keywords match `finance`.
   - Request is immediately blocked with code `RLS-Policy-Guard`.
   - Returns clear refusal: *"As a Tech Specialist, access to corporate financial reports, capex projections, and annual budget records is restricted under company Row-Level Security (RLS) policies."*
3. **Layer 2 Defense (Database Kernel Enforcement):**
   - Even if an attacker bypasses the frontend code (e.g., via direct curl/REST call with their JWT), PostgreSQL executes:
     ```sql
     create policy "role-scoped chunk read" on document_chunks for select
       using (exists (
         select 1 from auth_profile() p
         where p.company_id = document_chunks.company_id
           and (p.role = 'admin' or p.role = document_chunks.category)
       ));
     ```
   - Because `p.role = 'tech'` and `document_chunks.category = 'finance'`, PostgreSQL returns an empty set `[]`. The model receives **zero** finance chunks.

---

## 4. Deep-Dive Module Breakdown

### 4.1 Frontend UI/UX & Client Deliverable Engine

The frontend is located in [`frontend/`](file:///d:/Coding/sovereign-ai-workbench/frontend) and provides a command-center experience:

- **TanStack Router Architecture:** Routes are statically typed via `routeTree.gen.ts`. The primary views are:
  - `/` — Landing page with Parallax Hero, interactive feature cards, and sovereignty comparison matrix.
  - `/chat` — Command Center Workbench with model selector, real-time message streaming, expandable thought blocks, source citation drawers, and session management.
  - `/admin` — Company-scoped administration portal for User Management (live username/email availability check), Document Uploads, Access Logs, and Analytics.
  - `/login` — Secure dual authentication (Email or Username login via Supabase RPC).
  - `/profile` — Self-service credentials management and avatar uploads.
- **In-Browser Deliverable Compilation (`file-generator.ts`):**
  - Uses `docx` to create tables with borders, shaded header cells, and bulleted lists.
  - Uses `xlsx` (SheetJS) to compile multi-tab workbooks with auto-fit column widths.
  - Uses `pptxgenjs` to construct 16:9 widescreen presentation decks with master slide templates and speaker notes.
  - Generates binary `Blob` objects and converts them to Data URIs for instant browser download without network egress.

---

### 4.2 Autonomous Agent Orchestrator (Hand-Rolled ReAct Loop)

Located in [`agent/sovereignai/orchestrator/agent_loop.py`](file:///d:/Coding/sovereign-ai-workbench/agent/sovereignai/orchestrator/agent_loop.py):

- **Why Not LangChain?** Commercial frameworks suffer from dependency churn, leaky abstractions, and unpredictable prompt wrapping. Bastion’s orchestrator is a clean, 380-line Python generator loop implementing:
  $$\text{Thought} \longrightarrow \text{Action (Tool Call)} \longrightarrow \text{Observation (Tool Output)} \longrightarrow \text{Iteration}$$
- **Multi-Format Tool Parser:** Open-weight models (Qwen, Hermes, Mistral) often emit tool calls in non-standard formats when quantized. `agent_loop.py` incorporates an extraction cascade:
  1. Standard OpenAI JSON tool call schema.
  2. Hermes-style XML tags: `<tool_call>func<arg_key>k</arg_key><arg_value>v</arg_value></tool_call>`.
  3. Mistral Python literal calls: `<|tool_call_start|>[func(k=v)]<|tool_call_end|>`.
  4. Raw markdown JSON code blocks.
- **Loop Prevention & Anti-Hallucination:**
  - If a model issues the exact same tool signature with identical arguments twice in one turn, the orchestrator detects the loop, re-injects the cached result, and nudges the model to synthesize conclusions.
  - If a model describes wanting to call a tool in text but fails to emit the JSON call, the orchestrator triggers an automatic retry prompt: *"You described calling [tool] but didn't actually call it. Call it now."*

---

### 4.3 Resident Model Router & Dynamic Tier Allocation

Located in [`agent/sovereignai/orchestrator/router.py`](file:///d:/Coding/sovereign-ai-workbench/agent/sovereignai/orchestrator/router.py):

- **The Philosophy:** Not every prompt requires a heavy reasoning model.
- **Routing Decision Pipeline:**
  - A lightweight, fast classifier evaluates prompt syntax, keyword patterns, and semantic intent.
  - Maps to one of 6 categories:
    1. `general` $\rightarrow$ Sovereign Tier: `Qwen3.5-9B` (General drafting, summaries).
    2. `coding` $\rightarrow$ Sovereign Tier: `Qwen3-Coder-Next` (Scripts, AST inspection, debugging).
    3. `vision` $\rightarrow$ Sovereign Tier: `Qwen3-VL-32B` (P&ID diagrams, OCR, scanned PDFs).
    4. `spreadsheet` $\rightarrow$ Sovereign Tier: `Qwen3.5-9B` (Formulas, row/col calculations).
    5. `document_qa` $\rightarrow$ Sovereign Tier: `Qwen3.6-27B` (Grounded RAG retrieval).
    6. `planning` $\rightarrow$ Sovereign Tier: `Qwen3.6-27B` (Multi-step tool decomposition).
  - Emits confidence score and classification rationale directly to the UI header (e.g., `-> routed to coding (Qwen3-Coder-Next) · 0.91 confidence`).

---

### 4.4 Multi-Tenant RAG Pipeline & PostgreSQL Row Level Security (RLS)

Located in [`agent/sovereignai/knowledge_base/store.py`](file:///d:/Coding/sovereign-ai-workbench/agent/sovereignai/knowledge_base/store.py) and [`frontend/src/lib/rag-service.ts`](file:///d:/Coding/sovereign-ai-workbench/frontend/src/lib/rag-service.ts):

- **Data Schema:**
  - `companies`: Multi-tenant root (e.g., Indian Oil Corporation Ltd).
  - `profiles`: Extends `auth.users` with `company_id`, `username`, and `role` (`admin | tech | finance | support`).
  - `documents`: Document parent records tagged with `category = user_role`.
  - `document_chunks`: Text split into 1200–1600 character windows with 15% overlap, storing 1536-dim embeddings.
  - `document_access_logs`: Immutable audit ledger storing user, document ID, action, and timestamp.
- **Non-Recursive RLS via Security Definer:**
  - Standard RLS policies that query `profiles` from inside a `profiles` policy cause infinite recursion.
  - We solved this using a `security definer` function:
    ```sql
    create or replace function auth_profile()
    returns table (company_id uuid, role user_role)
    language sql security definer stable as $$
      select company_id, role from profiles where id = auth.uid();
    $$;
    ```
- **3-Tier Hybrid Search Execution:**
  1. **Tier 1 (Ranked Full-Text RPC):** Calls `search_document_chunks_ranked` using PostgreSQL `tsvector` and `tsquery` with custom industrial stop-word pruning.
  2. **Tier 2 (Vector Similarity RPC):** Calls `match_document_chunks` using pgvector cosine distance (`<=>` operator) with similarity threshold 0.15.
  3. **Tier 3 (Multi-Keyword Fallback):** Executes client-side tokenized `ilike` matching with title match weighting (+40 score boost).

---

### 4.5 Sandboxed Code Execution & NetGuard Network Monitor

Located in [`agent/sovereignai/tools/sandbox_tool.py`](file:///d:/Coding/sovereign-ai-workbench/agent/sovereignai/tools/sandbox_tool.py) and [`agent/sovereignai/net_guard/`](file:///d:/Coding/sovereign-ai-workbench/agent/sovereignai/net_guard/):

- **Docker Sandbox Hardening:**
  - When the agent invokes `sandbox_exec`, it mounts a temporary host directory into a clean container (`python:3.11-slim`, `node:20-slim`, or `gcc:13`).
  - **`network_mode="none"` is strictly enforced.** The container has no network stack, no default gateway, and cannot resolve DNS or make TCP/UDP connections.
  - Hard memory limit: `2g`. Hard CPU limit: `2.0 cores`. Timeout: 60 seconds. Container is purged automatically (`remove=True`).
- **NetGuard Network Monitor:**
  - A background thread polls `psutil.net_connections()` every 500ms.
  - Whitelists loopback (`127.0.0.0/8`, `::1`), RFC-1918 private company subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and explicitly configured provider endpoints.
  - Any unauthorized outbound packet triggers an immediate alert and records an entry in the security audit trail.

---

## 5. Benefits & Value Proposition

### 5.1 Benefits for Frontend & End-User Experience
- **Instant Usability for Non-Technical Personnel:** Plant operators and executives don't write complex system prompts; they type natural language questions and receive clean, formatted answers with highlighted citations.
- **Zero-Latency In-Browser File Export:** Download Word memos or Excel models immediately without waiting for server batch queues.
- **Visual Confidence & Transparency:** Expandable "Thought Blocks" allow operators to inspect the model’s intermediate chain-of-thought and verification steps before trusting the output.
- **Factory Dark Mode:** Built specifically for low-light industrial control rooms to reduce eye strain over 12-hour shifts.

### 5.2 Benefits for the Agent Orchestration System
- **Resilient Autonomous Execution:** Handles multi-step instructions (e.g., *"Read document -> Extract table -> Write Python script to calculate variance -> Output Excel sheet"*) autonomously without crashing.
- **Token Efficiency:** The resident router prevents wasting tens of thousands of tokens by avoiding sending simple requests to over-parameterized models.
- **Zero Framework Lock-in:** Native Python implementation ensures full code auditability for government certification (STQC / CERT-In).

### 5.3 Benefits for RAG & Enterprise Knowledge Retrieval
- **Elimination of Cross-Department Data Leaks:** Strict RLS enforcement at the database level guarantees mathematical isolation between department records.
- **High Recall on Messy Scanned Industrial PDFs:** Clean OCR pipeline handles broken PDF ligatures, scanned tables, and technical specs that typically break naive chunkers.
- **Auditability & Traceability:** Every factual claim is backed by document citations and similarity scores, preventing ungrounded hallucinations.

### 5.4 Benefits for the Enterprise & Regulatory Compliance
- **100% Data Sovereignty:** Confidential operational IP never leaves the internal facility perimeter in air-gapped mode.
- **Immunity from Cloud WAN Outages:** In case of external telecom/satellite fiber cuts, the plant workbench continues functioning locally on plant floor workstations.
- **Immutable Compliance Logs:** Complete audit trails allow PSUs to prove ISO 27001, DPDP, and NIST compliance to external government auditors.
- **Cost Predictability:** Replaces unpredictable per-token commercial API bills with fixed, predictable on-premise hardware infrastructure.

---

## 6. Tough Viva Questions & Examiner Defense (Q&A)

Here are the most challenging technical questions an external examiner, professor, or security auditor will ask, along with model technical answers:

### Q1: "Why did you build a custom agent loop instead of using LangChain, LlamaIndex, or CrewAI?"
> **Answer:**  
> "Commercial frameworks like LangChain introduce hundreds of transitive dependencies, frequent breaking changes, and opaque prompt wrappers that obscure token flow. In critical infrastructure (such as an oil refinery or defense PSU), software must be auditable, deterministic, and CERT-In certifiable. Our hand-rolled ReAct loop in `agent_loop.py` is under 400 lines of clean Python. It provides precise control over streaming tokens, custom AST/regex parsing for diverse open-weight tool formats (like Hermes and Mistral), loop detection, and direct integration with our Docker sandbox."

---

### Q2: "How do you mathematically guarantee that a Tech Engineer cannot read confidential Finance documents?"
> **Answer:**  
> "Security is enforced at two distinct layers:
> 1. **Application Layer:** `validateRoleAccess()` in `rag-service.ts` inspects prompt intent against domain classifiers and halts unauthorized cross-department queries before they run.
> 2. **Database Kernel Layer (PostgreSQL RLS):** This is the true cryptographic boundary. In `SUPABASE.md`, Row Level Security is active on `documents` and `document_chunks`. The query runs under the authenticated user's JWT. PostgreSQL executes our `auth_profile()` security-definer helper and evaluates:
>    ```sql
>    where (p.role = 'admin' or p.role = document_chunks.category)
>    ```
>    Even if an attacker bypassed the UI and executed a raw SQL vector similarity search, PostgreSQL filters out finance chunks at the database engine level before returning rows. The similarity search mathematically returns an empty set."

---

### Q3: "What is the difference between IVFFlat and HNSW vector index algorithms in pgvector, and which is used here?"
> **Answer:**  
> "In our initial database migration (`SUPABASE.md`), an `ivfflat` index is defined with `lists = 100` using vector cosine distance (`vector_cosine_ops`). IVFFlat (Inverted File Flat) partitions vectors into Voronoi cells via k-means clustering. During search, it only evaluates centroids closest to the query vector, offering fast build times and lower RAM consumption. For larger enterprise deployments (>100,000 chunks), we can upgrade to `hnsw` (Hierarchical Navigable Small World), which builds a multi-layer graph offering higher recall at high query concurrency with slightly higher memory overhead."

---

### Q4: "If the system is air-gapped, how does embedding generation work when the OpenAI API is unreachable?"
> **Answer:**  
> "We engineered a dual-embedding strategy:
> 1. In hybrid cloud mode, the system utilizes OpenAI’s `text-embedding-3-small` (1536 dimensions) for state-of-the-art semantic search.
> 2. In strict air-gapped on-premise mode, the system can either hook into a local `nomic-embed-text` model running on Ollama/vLLM, or utilize our built-in deterministic L2-normalized hash pseudo-embedder (`generateLocalEmbedding`). This generates valid 1536-dimensional vectors directly from text character frequencies, ensuring that cosine similarity math in PostgreSQL never encounters null vectors or crashes."

---

### Q5: "What prevents a prompt injection from breaking out of your code execution tool?"
> **Answer:**  
> "Code execution is isolated via the Docker SDK in `sandbox_tool.py`. When the model writes Python or Bash code:
> - The code is written to a temporary host directory mounted into an ephemeral container.
> - **The container runs with `network_mode="none"`.** This completely strips the virtual eth0 interface; the code cannot establish outbound TCP/UDP connections, ping internal IPs, or reach SCADA devices.
> - Host resources are constrained via `mem_limit='2g'` and `nano_cpus=2000000000` (2 CPU cores).
> - Execution runs with a strict 60-second timeout, after which the container is automatically killed and destroyed (`remove=True`). Even if malicious code attempts an infinite fork-bomb or filesystem wipe, it only affects the disposable container scratchpad."

---

### Q6: "Why do you need both Ranked Full-Text Search and Vector Semantic Search in RAG?"
> **Answer:**  
> "Pure vector search suffers from the **'lexical mismatch'** problem in engineering domains. For example, specific valve codes like `SOP-114-REV3` or turbine serial numbers `IOCL-BMR-2024` may have embedding representations that cluster closely with generic manuals. Conversely, pure keyword search fails when users ask semantic questions like *'How do we handle pressure relief valve failures?'*.
> Our 3-tier hybrid pipeline combines:
> 1. PostgreSQL full-text search (`tsvector`/`tsquery` via `search_document_chunks_ranked`) to catch exact serial numbers, codes, and regulation clauses.
> 2. pgvector cosine similarity (`match_document_chunks`) to capture semantic meaning and intent.
> 3. Domain-preserving keyword fallback with stopword preservation to ensure high recall even on scanned OCR documents."

---

### Q7: "How do you handle PDF OCR errors in complex industrial documents like IOCL reports?"
> **Answer:**  
> "Scanned PDFs parsed by Python PDF libraries often contain corrupted control characters, null bytes (`\x00-\x1F`), and garbled ligature symbols (e.g., `\u0003` used as spaces). We implemented `cleanOcrText()` in both Python (`store.py`) and TypeScript (`rag-service.ts`), which runs regex filters to strip non-printable ASCII/Unicode control blocks and normalizes multiple whitespace characters before chunks are sent to the embedding model or presented to the LLM. This prevents embedding distortion and token budget waste."

---

### Q8: "How does the Model Router prevent latency degradation?"
> **Answer:**  
> "Running a full reasoning LLM on every incoming message introduces unnecessary latency (often 2–4 seconds). In Bastion, the resident router model (`router.py`) executes with `temperature = 0` and `max_tokens = 40`. It evaluates the prompt against a structured JSON schema in under 250 milliseconds. For simple Q&A or summaries, it routes to `Qwen3.5-9B`, preserving high-memory GPU resources for coding (`Qwen3-Coder-Next`) or vision tasks (`Qwen3-VL-32B`)."

---

### Q9: "Why generate Word, Excel, and PowerPoint files directly in the browser using JavaScript libraries rather than on the server?"
> **Answer:**  
> "Client-side generation using `docx`, `xlsx`, and `pptxgenjs` offers two major architectural advantages:
> 1. **Zero Server Footprint & Infinite Scalability:** The server does not spend CPU cycles compiling heavy Office Open XML zip archives. The user's device handles file rendering in milliseconds.
> 2. **Data Privacy:** Once the model generates the structured text/table payload over the stream, the binary assembly happens inside the user's browser memory. The final document never leaves the client or touches temporary server storage, reinforcing the sovereign architecture."

---

### Q10: "How does the system ensure compliance auditing for regulatory bodies?"
> **Answer:**  
> "Every user interaction is logged in the `document_access_logs` table in PostgreSQL. The log records:
> - Authenticated User ID and Company ID
> - Exact query text and timestamp
> - Referenced document ID and chunk indices
> - Action type (`query`, `view`, `download`)
> In the agent CLI, `bastion audit export` allows safety officers to export this immutable session audit trail directly into a signed `.docx` or `.json` compliance report for submission to statutory authorities."

---

### Q11: "What are the hardware requirements to run the Sovereign AI Workbench fully on-premise?"
> **Answer:**  
> "For a department-level deployment (Mode A):
> - **GPU:** A single modern workstation GPU with 16GB–24GB VRAM (such as an NVIDIA RTX 4080/4090 or RTX A5000). Using AWQ/GPTQ 4-bit quantization, `Qwen3.5-9B` consumes ~6GB VRAM, while `Qwen2.5-Coder-7B` consumes ~5GB VRAM.
> - **RAM:** 32 GB system memory.
> - **Storage:** 50 GB SSD for model weights and PostgreSQL vector indices.
> - **CPU:** 8 cores (Intel i7/Xeon or AMD Ryzen).
> For an entire refinery site, multiple GPU nodes running vLLM provide concurrent token throughput."

---

### Q12: "If someone types `/logout` in the TUI or leaves their desk, how is session security maintained?"
> **Answer:**  
> "Sessions in the TUI persist in an encrypted local JSON credentials file (`~/.bastion/auth_session.json`). Typing `/logout` immediately purges the active JWT access token, clears the in-memory chat session history, and returns the operator to the Identity & Access Management authentication screen. In the web interface, Supabase Auth handles token revocation and automatic refresh token rotation."

---

## 7. Summary Checklist for Viva Defense

- [x] **Problem Articulated:** Industrial air-gap necessity, preventing data exfiltration, eliminating internal cross-department RAG snooping, producing real deliverables.
- [x] **Frontend Architecture Clear:** TanStack Start/Router, React 19, Tailwind v4 Obsidian theme, in-browser `docx`/`xlsx`/`pptx` compilation.
- [x] **Agent Loop Defended:** Hand-rolled ReAct engine (`agent_loop.py`), multi-format AST tool parser, anti-loop deduplication.
- [x] **Security Boundary Proven:** PostgreSQL Row Level Security (RLS) via non-recursive security-definer function `auth_profile()`.
- [x] **Sandboxing Detailed:** Docker `--network=none`, memory limits, CPU quotas, ephemeral auto-removal.
- [x] **Retrieval Strategy Justified:** 3-tier hybrid search (Ranked Full-Text + pgvector Cosine + Keyword Fallback with OCR cleaning).
- [x] **Sovereignty Story Intact:** Provable zero-egress monitoring via NetGuard socket polling and local offline execution capability.
