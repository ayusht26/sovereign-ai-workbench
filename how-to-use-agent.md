# How to Use Bastion Agent

> **Sovereign AI. OpenAI-powered. Supabase RAG. Zero local model downloads.**  
> Uses the same knowledge base as the web application — ask anything from the docs.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [First-Time Setup](#2-first-time-setup)
3. [Activating the Environment](#3-activating-the-environment)
4. [Health Check](#4-health-check)
5. [Launching the Agent TUI](#5-launching-the-agent-tui)
6. [Using the TUI](#6-using-the-tui)
7. [CLI Commands Reference](#7-cli-commands-reference)
8. [Knowledge Base (RAG)](#8-knowledge-base-rag)
9. [Model Display Names](#9-model-display-names)
10. [Configuration](#10-configuration)
11. [Audit Log Export](#11-audit-log-export)
12. [Demo Scenarios to Try](#12-demo-scenarios-to-try)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

Only two things needed:

| Tool | Version | Install |
|------|---------|---------|
| **Python** | 3.11+ | [python.org](https://python.org) |
| **OpenAI API Key** | — | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

> **Docker** is optional — only needed if you want the `sandbox_exec` tool for running code in isolation. The agent works fully without it.

**Verify Python:**

```powershell
python --version    # must show 3.11+
```

---

## 2. First-Time Setup

```powershell
# Step 1: Navigate to the agent folder
cd D:\Coding\sovereign-ai-workbench\agent

# Step 2: Create a virtual environment
python -m venv .venv

# Step 3: Activate it
.\.venv\Scripts\Activate.ps1

# Step 4: Install Bastion and all dependencies
pip install -e .

# Step 5: Create the .env file with your API key
# (The frontend .env is already copied here — verify it contains OPENAI_API_KEY)
# If not, create agent/.env with:
#   OPENAI_API_KEY=sk-proj-...

# Step 6: Verify everything is working
bastion doctor
```

That's it. No model downloads. No Ollama. No Docker required.

---

## 3. Activating the Environment

Every time you open a new terminal session:

```powershell
# Navigate to the workspace
cd D:\Coding\sovereign-ai-workbench

# Activate the venv
.\agent\.venv\Scripts\Activate.ps1
```

You'll see `(.venv)` prepended to your prompt when active.

> **Tip:** Add the activation line to your PowerShell profile (`$PROFILE`) so it activates automatically.

---

## 4. Health Check

```powershell
bastion doctor
```

Checks:

| Check | What it validates |
|-------|------------------|
| Python version | Must be 3.11+ |
| `OPENAI_API_KEY` | Must be set in env or `.env` file |
| OpenAI API reachable | Connects to `api.openai.com` |
| Supabase reachable | Connects to the project database |
| Docker (optional) | Warns if missing, won't block startup |
| Config directory | Auto-created at `~/.bastion/` |

Run `bastion doctor` after any change until all checks pass.

---

## 5. Launching the Agent TUI

```powershell
# Make sure venv is active, then:
bastion
```

The full-screen Terminal UI opens with the BASTION banner and chat input.

### Optional: Set a specific workspace

```powershell
# Agent reads/writes files relative to this folder
bastion --workspace D:\data\projects\unit-4-inspection

# Or set from inside the TUI:
# /cwd D:\data\projects\unit-4-inspection
```

---

## 6. Using the TUI

### Layout

```
+----------------------------------------------+-------------------+
|                                               | Session           |
|   Chat thread — messages, thought blocks,     | Context           |
|   tool calls, and responses stream here live  | 0 tokens          |
|                                               | $0.00             |
|  [ Ask anything...                        ]   |                   |
|                                               | Model             |
|   AUTO  ·  📁 D:\projects\unit-4              | AUTO              |
|                                               |                   |
|  tab agents  ctrl+p commands  esc interrupt   | GPU               |
|                                               | RTX 4060 Laptop   |
+----------------------------------------------+-------------------+
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Submit message |
| `Ctrl+P` | Open command palette |
| `Esc` | Interrupt current generation |
| `Ctrl+N` | Start a new session |

### In-TUI Slash Commands

| Command | What it does |
|---------|-------------|
| `/models` | Open model selection palette (`AUTO`, `Qwen3.5-9B`, `Qwen3-Coder-Next`, `Qwen3-VL-32B`) |
| `/auto` | Switch back to AUTO routing |
| `/new` | Start a new session |
| `/sessions` | Browse past sessions |
| `/kb status` | Show knowledge base statistics (Supabase) |
| `/cwd <path>` | Change the workspace directory |
| `/help` | Show all available commands |

---

### AUTO Mode — Task Routing

Every message is classified by the router model and routed to the right model tier:

| Task Category | Display Name in TUI | Example Prompt |
|--------------|---------------------|---------------|
| General (Q&A, summaries, drafting) | `Qwen3.5-9B` | "Summarize the project status." |
| Coding (write/fix/debug code) | `Qwen3-Coder-Next` | "Write a Python script to parse CSV." |
| Vision (images, scanned PDFs) | `Qwen3-VL-32B` | "What's in this diagram?" |
| Spreadsheet / financial tables | `Qwen3.5-9B` | "Analyse this Excel report." |
| Document Q&A (from knowledge base) | `Qwen3.5-9B` | "What does SOP-114 say about pressure limits?" |
| Planning (multi-step tasks) | `Qwen3.5-9B` | "Extract findings and generate a Word report." |

> The display names (Qwen3.5-9B, Qwen3-Coder-Next etc.) match the website's sovereign model naming. The underlying model is `gpt-4o-mini` for all categories.

The routing decision appears above each response:
```
-> routed to coding (Qwen3-Coder-Next) . 0.91 confidence
```

### Agentic Step Indicators

| Indicator | Meaning |
|-----------|---------|
| `+ Thought: Xms` | Collapsible reasoning block |
| `[TOOL] sandbox_exec` | Tool call in progress |
| `[OK] Success` | Tool completed successfully |
| `[FILE] File produced: output.docx` | Clickable file card |

---

## 7. CLI Commands Reference

```powershell
# Launch the TUI
bastion

# Launch with a specific workspace folder
bastion --workspace D:\path\to\your\project

# Check all dependencies
bastion doctor

# View version and banner
bastion version

# List configured models and their display names
bastion models list

# (No-op — models are API-hosted, nothing to download)
bastion models pull

# Open config file in your editor
bastion config edit

# Print current config to terminal
bastion config show

# Knowledge base status (from Supabase)
bastion kb status

# Note: documents are uploaded via the web admin panel, not the CLI
bastion kb add <path>    # shows web admin panel instructions

# Export an audit log
bastion audit export                                       # latest session -> .docx
bastion audit export --session <id> --format json         # specific session -> .json
bastion audit export --format text --output report.txt    # text to a file
```

---

## 8. Knowledge Base (RAG)

Bastion's knowledge base is **the same Supabase database the web application uses**. Documents ingested via the web admin panel are immediately available to the agent.

### How to add documents

1. Open the Bastion web app in your browser
2. Go to **Admin → Documents → Upload**
3. Upload `.pdf`, `.docx`, `.txt`, or other supported formats
4. The agent can answer questions from those documents immediately

### Check knowledge base status

```powershell
bastion kb status
```

Or from inside the TUI:
```
/kb status
```

Output:
```
  Knowledge Base Status
   Documents : 42
   Chunks    : 1,847
   Last ingest: 2026-09-11T10:30:00
```

### Query the knowledge base

Just ask naturally — the agent automatically searches the knowledge base when it detects document Q&A intent:

> _"What does SOP-114 say about valve torque limits?"_  
> _"Find all correspondence about the Unit-4 compressor failure."_  
> _"Summarise the key findings from the inspection reports."_

Responses cite document sources: **"Per SOP-114 (§3.2), the maximum torque is…"**

### How RAG works

The same three-tier search strategy as the website:
1. **PostgreSQL full-text ranked search** (`search_document_chunks_ranked` RPC)
2. **pgvector semantic search** (`match_document_chunks` RPC with OpenAI embeddings)
3. **Keyword fallback** (`ilike` on content column)

---

## 9. Model Display Names

The TUI shows sovereign model names that match the website. These are cosmetic labels:

| TUI Display Name | Real API Model | Category |
|-----------------|----------------|----------|
| `Qwen3.5-9B` | `gpt-4o-mini` | General, planning, document Q&A |
| `Qwen3-Coder-Next` | `gpt-4o-mini` | Coding, sandbox |
| `Qwen3-VL-32B` | `gpt-4o-mini` | Vision, multimodal |
| `Auto router` | `gpt-4o-mini` | Classification only |

To see the full model table:

```powershell
bastion models list
```

---

## 10. Configuration

Config file: `%USERPROFILE%\.bastion\config.yaml`  
Shipped defaults: `agent\models.yaml`

```powershell
# Edit config in your default editor
bastion config edit

# Print current config to terminal
bastion config show
```

### Reset config to defaults

```powershell
# WARNING: resets ALL custom settings
del $env:USERPROFILE\.bastion\config.yaml
```

---

## 11. Audit Log Export

Every session is automatically logged. Export for compliance/review:

```powershell
# Export the latest session as a Word document (default)
bastion audit export

# Export a specific session as JSON
bastion audit export --session <session-id> --format json

# Export as plain text to a file
bastion audit export --format text --output D:\reports\session-audit.txt
```

Supported formats: `docx` (default), `json`, `text`

---

## 12. Demo Scenarios to Try

### Scenario 1 — Auto Model Routing

```
1. Launch:  bastion
2. Ask:     "Write a short summary of what an air-gapped system is."
            -> watch: routed to general (Qwen3.5-9B)
3. Ask:     "Write a Python function that checks if a file was modified in the last 24 hours."
            -> watch: routed to coding (Qwen3-Coder-Next)
```

### Scenario 2 — Document Q&A from Knowledge Base

```
1. Launch:  bastion
2. Ask:     "What does the SOP say about pressure limits?"
            -> agent searches Supabase KB, returns answer with source citations
3. Ask:     "Find all correspondence about the Unit-4 compressor failure."
            -> agent retrieves matching document chunks from the database
```

### Scenario 3 — Agentic Document Generation

```
1. Ask: "Draft an approval note as a Word document summarising today's meeting."
2. Watch the agent:
   - Route to general (Qwen3.5-9B)
   - Call generate_docx -> produce approval_note.docx
   - Show: [FILE] File produced: approval_note.docx
```

### Scenario 4 — Code + Sandbox Execution (requires Docker)

```
1. Ask: "Write a Python script that reads a CSV and calculates the average of the
         'value' column. Include a deliberate bug, then fix it and show tests passing."
2. Watch the agent:
   - Write the script via fs_write
   - Execute in Docker sandbox (--network none) via sandbox_exec
   - Fix the bug -> run again -> passing
```

### Scenario 5 — Vision / Multimodal

```
1. Drop in a photo of a P&ID diagram or handwritten note
2. Ask: "What is the tag number of the valve in the top-right?"
3. Watch: routes to vision (Qwen3-VL-32B), answers from the actual image
```

---

## 13. Troubleshooting

```powershell
bastion doctor   # always start here
```

| Symptom | Fix |
|---------|-----|
| `bastion: command not found` | Venv not active — run `.\agent\.venv\Scripts\Activate.ps1` |
| `OPENAI_API_KEY is not set` | Add `OPENAI_API_KEY=sk-...` to `agent/.env` |
| Chat does nothing / hangs | Check your internet connection; run `bastion doctor` |
| RAG returns nothing | Check `bastion kb status`; upload docs via web admin panel |
| `Supabase not reachable` | Check internet; verify Supabase project is active |
| Sandbox fails: "image not found" | Pull Docker image: `docker pull python:3.11-slim` |
| Python < 3.11 error | Install Python 3.11+ from [python.org](https://python.org) |
| `pip install -e .` fails | Ensure venv is active and you're in the `agent/` directory |

---

_Bastion \u2014 Sovereign AI agent. OpenAI-powered. Supabase RAG. Everything in your database._
