# SovereignAI

**Local models. Local data. Zero external calls.**

A self-hosted, fully air-gapped, terminal-based AI agent workbench for on-premise deployment inside refineries, PSUs, defence-linked manufacturing units, and government offices where no data may ever leave the local network.

```
███████╗ ██████╗ ██╗   ██╗ █████╗ ██╗
██╔════╝██╔═══██╗██║   ██║██╔══██╗██║
███████╗██║   ██║██║   ██║███████║██║
╚════██║██║   ██║╚██╗ ██╔╝██╔══██║██║
███████║╚██████╔╝ ╚████╔╝ ██║  ██║██║
╚══════╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝╚═╝

        S O V E R E I G N   A I
   air-gapped agent · v0.1.0 · 🔒 OFFLINE
```

## Quick Start

```bash
# Prerequisites: Python 3.11+, Docker, Ollama

# 1. Clone and install
git clone <repo> sovereignai && cd sovereignai/agent
pip install -e .

# 2. Pull required models (~14GB)
sovai models pull

# 3. Launch
sovai
```

See [HOW_TO_USE.md](HOW_TO_USE.md) for the full guide.

## What It Does

- **Auto-routes requests** to the right model (general / coding / vision) using a tiny resident router model
- **Full agentic loop** — plan → act → observe → iterate, streaming live to the terminal
- **Real deliverables** — produces `.docx`, `.pptx`, `.xlsx` files directly from a single request
- **Runs code in isolation** — Docker containers with `--network none`, CPU/memory limits
- **Understands documents** — scanned PDFs, handwritten notes, P&IDs via vision model
- **Local knowledge base** — ingest your SOPs/manuals and ask questions about them
- **Zero external calls** — auditable at the code level, provable with a live network monitor

## Architecture

```
TUI (Textual) → Agent Orchestrator → Model Router → Ollama (localhost:11434)
                     ↓                                     ↓
              Tool Registry                        ChromaDB (local RAG)
              fs_read/write, sandbox_exec,
              sheet_tool, docgen_tool,
              vision_tool, rag_tool
```

## Requirements

| Component | Minimum               |
| --------- | --------------------- |
| Python    | 3.11+                 |
| RAM       | 16 GB                 |
| VRAM      | 8 GB (RTX 4060 class) |
| Storage   | 20 GB (models)        |
| Docker    | Desktop 4.x+          |
| Ollama    | 0.3.x+                |

## Models (Default — 8GB VRAM)

| Role       | Model              | Purpose                         |
| ---------- | ------------------ | ------------------------------- |
| Router     | `llama3.2:3b`      | Always-resident task classifier |
| General    | `qwen3.5:9b`       | Drafting, summaries, Q&A        |
| Coding     | `qwen2.5-coder:7b` | Code generation, debugging      |
| Vision     | `qwen2.5vl:7b`     | OCR, scanned PDFs, images       |
| Embeddings | `nomic-embed-text` | RAG knowledge base              |

Upgrade to larger models by editing `~/.sovereignai/config.yaml` — no code changes needed.
