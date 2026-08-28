# Sovereign On-Premise Agentic AI Workbench for Confidential Industrial Work

> **Air-Gapped Sovereign AI System for PSUs, Refineries, Defense & Government Facilities.**  
> Never leaves the local network, automatically routes tasks to open-weight models, grounds reasoning in local SOPs via RAG, enforces human-in-the-loop sign-off, and produces deterministic deliverables (.docx, .pptx, .xlsx).

---

## 👥 3-Pair Team Allocation Matrix

| Pair | Team Members | Focus Area | Primary Directory | Guide |
|---|---|---|---|---|
| **Pair 1** | Person 1 + Person 2 | 🎨 Frontend UI/UX & API Integration | [`frontend/`](frontend/) | [`frontend/README.md`](frontend/README.md) |
| **Pair 2** | Person 3 + Person 4 | 🤖 FastAPI Gateway + Model Router + LangGraph Agent | [`backend/`](backend/) | [`backend/README.md`](backend/README.md) |
| **Pair 3** | Person 5 + Person 6 | 📚 RAG + Document Generation + Sandbox + Air-Gap Proof | [`rag/`](rag/), [`document_generation/`](document_generation/), [`sandbox/`](sandbox/), [`security/`](security/) | [`rag/README.md`](rag/README.md), [`security/README.md`](security/README.md) |

---

## 📁 Repository Directory Structure

```text
sovereign-ai-workbench/
├── frontend/                   # Pair 1: React + Vite + Tailwind + Framer Motion (Factory Dark Theme)
│   ├── src/
│   │   ├── components/ui/      # Skiper30 Parallax, Skiper106 Smooth Input, Lip Zoom, FileUploadCard
│   │   ├── pages/              # Landing, Control Room, Ingestion, Approval views
│   │   └── services/           # API clients & SSE streaming
├── backend/                    # Pair 2: FastAPI + LangGraph + Model Router
│   ├── app/
│   │   ├── api/                # REST endpoints (/api/chat, /api/files, /api/approval)
│   │   ├── router/             # Task routing & model selection (Reasoning / Coding / Vision)
│   │   ├── agent/              # LangGraph state machine & human-in-the-loop checkpoints
│   │   ├── models/             # vLLM / Ollama OpenAI API wrappers
│   │   └── tools/              # File, RAG, Sandbox, and Document tools
├── rag/                        # Pair 3: Knowledge Base & Vector Ingestion
│   ├── ingestion/              # PDF/DOCX loaders, chunkers & BGE-M3 embedder
│   ├── retrieval/              # Qdrant hybrid semantic search with citations
│   └── knowledge_base/         # Local confidential SOPs & manuals
├── document_generation/        # Pair 3: Deterministic Office Document Generators
│   ├── word/                   # python-docx approval note generator
│   ├── powerpoint/             # python-pptx executive briefing deck builder
│   └── excel/                  # openpyxl variance & inspection defect matrices
├── sandbox/                    # Pair 3: Untrusted code execution in gVisor / Docker (--network=none)
├── security/                   # Pair 3: Default-deny egress firewall & live packet sniffer proof
├── database/                   # PostgreSQL schema for LangGraph checkpoints & audit trails
├── models/                     # Model weights & vLLM hardware allocation guides (RTX 4090)
├── data/                       # On-premise encrypted file storage (uploads, processed, outputs)
└── docs/                       # Architecture, API specs, Setup guide, and Demo script
```

---

## 🚀 Quick Start

1. **Start Database & Vector Store**:
   ```bash
   docker-compose up -d
   ```
2. **Start Backend Gateway**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
3. **Start Frontend Client**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

For detailed setup, architectural diagrams, and hackathon presentation scripts, see [`docs/`](docs/).
