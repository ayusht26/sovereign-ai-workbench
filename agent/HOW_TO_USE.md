# HOW TO USE — SovereignAI (`sovai`)

> **Local models. Local data. Zero external calls.**
> This guide covers: first-time setup, daily use, updating the agent, using it from terminal, and what someone who clones the repo needs to do.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [First-Time Setup (Fresh Clone)](#2-first-time-setup-fresh-clone)
3. [Launching SovereignAI](#3-launching-sovereignai)
4. [Using the TUI](#4-using-the-tui)
5. [CLI Commands (Terminal)](#5-cli-commands-terminal)
6. [Knowledge Base (RAG)](#6-knowledge-base-rag)
7. [Model Configuration](#7-model-configuration)
8. [Updating SovereignAI After Code Changes](#8-updating-sovereignai-after-code-changes)
9. [Network Isolation & Air-Gap Proof](#9-network-isolation--air-gap-proof)
10. [Four Demo Scenarios](#10-four-demo-scenarios)
11. [Troubleshooting (`sovai doctor`)](#11-troubleshooting-sovai-doctor)
12. [If You Clone This Repo (New Machine Setup)](#12-if-you-clone-this-repo-new-machine-setup)

---

## 1. Prerequisites

Install these once, before anything else:

| Tool             | Purpose          | Install                                                                              |
| ---------------- | ---------------- | ------------------------------------------------------------------------------------ |
| **Python 3.11+** | Runtime          | [python.org](https://python.org)                                                     |
| **Ollama**       | Local LLM server | [ollama.com/download](https://ollama.com/download)                                   |
| **Docker**       | Code sandbox     | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) |

> **Windows users:** Install via the Windows installers above. All commands below work in PowerShell.  
> **Linux users:** Use the package manager (`apt`, `dnf`, `pacman`) for Python and Docker; curl-install Ollama.

Verify prerequisites are working:

```bash
python --version    # should show 3.11+
ollama --version    # should show 0.3+
docker info         # should not error
```

---

## 2. First-Time Setup (Fresh Clone)

### Option A — Automated (recommended)

**Linux/macOS:**

```bash
cd agent/
bash scripts/install.sh
```

**Windows (PowerShell as Administrator):**

```powershell
cd agent\
.\scripts\install.ps1
```

The script will:

1. Create a Python virtual environment at `agent/.venv`
2. Install SovereignAI and all Python dependencies
3. Pull all 5 required Ollama models (~14GB)
4. Pull the 3 Docker sandbox images
5. Configure OS-level firewall rules
6. Run the air-gap verification test

### Option B — Manual (step by step)

```bash
# 1. Navigate to the agent folder
cd agent/

# 2. Create and activate a virtual environment
python -m venv .venv

# Linux/macOS:
source .venv/bin/activate

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# 3. Install the package (editable mode — changes take effect immediately)
D:\Coding\sovereign-ai-workbench

# 4. Pull required Ollama models (run Ollama first: ollama serve)
ollama pull llama3.2:3b        # router model — ~2GB
ollama pull qwen3.5:9b         # general reasoning — ~6GB
ollama pull qwen2.5-coder:7b   # coding — ~5GB
ollama pull qwen2.5vl:7b       # vision/OCR — ~5GB
ollama pull nomic-embed-text   # embeddings — ~300MB

# 5. Pull Docker sandbox images
docker pull python:3.11-slim
docker pull node:20-slim
docker pull gcc:13

# 6. Verify everything is working
sovai doctor
```

---

## 3. Launching SovereignAI

```bash
# Always activate your venv first (or add to your shell profile)
source agent/.venv/bin/activate   # Linux/macOS
# OR
agent\.venv\Scripts\Activate.ps1  # Windows

# Navigate to the folder you want to work in (becomes the workspace)
cd /data/projects/unit-4-inspection

# Launch!
sovai
```

That's it. The full-screen TUI opens in your terminal with the banner, then the chat input.

### Set workspace explicitly

```bash
sovai --workspace /data/projects/unit-4
# OR inside the TUI:
/cwd /data/projects/unit-4
```

---

## 4. Using the TUI

### Layout

```
┌────────────────────────────────────────────┬───────────────────┐
│                                             │ Session           │
│   [ASCII banner on empty state]             │ Context           │
│                                             │ 0 tokens · 0%    │
│   Chat thread — user messages, thought      │ $0.00 (local)    │
│   blocks, tool calls, and responses all     │                   │
│   stream here live                          │ Model             │
│                                             │ AUTO → qwen3.5:9b │
│  ┌──────────────────────────────────────┐  │                   │
│  │ Ask anything…                        │  │ Network           │
│  └──────────────────────────────────────┘  │ 🔒 0 ext calls    │
│                                             │                   │
│   AUTO  ·  📁 /data/projects/unit-4        │ Workspace         │
│                                             │ /data/projects…   │
│  tab agents  ctrl+p commands  esc interrupt │                   │
└────────────────────────────────────────────┴───────────────────┘
```

### Keyboard Shortcuts

| Key      | Action                       |
| -------- | ---------------------------- |
| `Enter`  | Submit message               |
| `Ctrl+P` | Open command palette         |
| `Esc`    | Interrupt current generation |
| `Ctrl+N` | New session                  |

### Slash Commands (type in the input box)

| Command          | What it does                            |
| ---------------- | --------------------------------------- |
| `/models`        | Open model selection palette            |
| `/auto`          | Switch back to AUTO model selection     |
| `/net`           | Open live network monitor               |
| `/new`           | Start a new session                     |
| `/sessions`      | Browse past sessions                    |
| `/kb status`     | Show knowledge base statistics          |
| `/kb add <path>` | Ingest a folder into the knowledge base |
| `/cwd <path>`    | Change the workspace directory          |
| `/help`          | Show all commands                       |

### AUTO Mode

By default, SovereignAI is in `AUTO` mode. Every message is classified by the tiny resident router model (`llama3.2:3b`) into one of 6 categories, and the right worker model is loaded automatically:

| Category                             | Model used                  |
| ------------------------------------ | --------------------------- |
| General (Q&A, drafting, summaries)   | `qwen3.5:9b`                |
| Coding (write/fix/debug code)        | `qwen2.5-coder:7b`          |
| Vision (images, scanned PDFs)        | `qwen2.5vl:7b`              |
| Spreadsheet (xlsx, financial tables) | `qwen3.5:9b` + `sheet_tool` |
| Document Q&A (SOPs, manuals)         | `qwen3.5:9b` + `rag_search` |
| Planning (multi-step tasks)          | `qwen3.5:9b` + all tools    |

The routing decision is always shown above each response (dim text):  
`→ routed to coding (qwen2.5-coder:7b) · 0.91 confidence`

### Watching the Agent Work

When the agent performs multi-step tasks, you'll see live:

- **`+ Thought: Xms`** — collapsible block of the model's reasoning (click to expand)
- **`🔧 Tool: sandbox_exec`** — tool call in progress (args shown, spinner active)
- **`✅ Success`** — tool completed (result shown, auto-collapsed)
- **`📎 File produced: /path/to/output.docx`** — file card for any generated deliverable

---

## 5. CLI Commands (Terminal)

All commands work from any terminal after activating the venv:

```bash
# Launch the TUI (default)
sovai

# Check all dependencies
sovai doctor

# View version and banner
sovai version

# List pulled Ollama models
sovai models list

# Pull all required models
sovai models pull

# Open config in $EDITOR
sovai config edit

# Show merged config
sovai config show

# Knowledge base management
sovai kb add /path/to/documents
sovai kb add /path/to/single-file.pdf
sovai kb status
sovai kb watch /path/to/live-folder

# Export an audit log
sovai audit export                         # exports latest session as .docx
sovai audit export --session <id> --format json
sovai audit export --format text --output report.txt
```

---

## 6. Knowledge Base (RAG)

The knowledge base lets the agent answer questions grounded in **your** organisation's actual documents — SOPs, manuals, past correspondence, inspection reports.

### Adding documents

```bash
# From terminal
sovai kb add /data/documents/sops
sovai kb add /data/correspondence/2025

# From inside the TUI
/kb add /data/documents/sops
```

Supported formats: `.pdf` (text-layer and scanned), `.docx`, `.txt`, `.md`, `.eml`, `.csv`

### How it works

1. Text is extracted (PyMuPDF for text-layer PDFs; vision model OCR for scanned pages)
2. Chunked into ~500-token pieces with 50-token overlap
3. Embedded using `nomic-embed-text` (local, via Ollama)
4. Stored in ChromaDB at `~/.sovereignai/kb/chroma/` (persistent, on-disk)

### Querying

Just ask naturally. The agent automatically uses `rag_search` for document Q&A:

> _"What does SOP-114 say about valve torque limits?"_  
> _"Find all correspondence about the Unit-4 compressor failure."_

The response will cite sources: **"Per SOP-114 §3.2, the maximum torque is…"**

### Keeping it up to date

```bash
# Re-run kb add whenever documents change
sovai kb add /data/documents/sops

# Or use watch mode (blocks terminal, re-ingests on save)
sovai kb watch /data/documents/sops
```

---

## 7. Model Configuration

The model map is in `~/.sovereignai/config.yaml`. To edit it:

```bash
sovai config edit   # opens in $EDITOR / notepad
```

### Changing models

Find the `models:` section:

```yaml
models:
  general:
    model: "qwen3.5:9b" # ← change this tag
    fallback: "llama3.1:8b"
  coding:
    model: "qwen2.5-coder:7b"
    fallback: "llama3.1:8b"
  vision:
    model: "qwen2.5vl:7b"
    fallback: "llava:7b"
```

After editing, just restart `sovai` — no code changes needed.

### Upgrade path (hardware tiers)

| Hardware                | General        | Coding             | Vision          |
| ----------------------- | -------------- | ------------------ | --------------- |
| 8GB VRAM (this default) | `qwen3.5:9b`   | `qwen2.5-coder:7b` | `qwen2.5vl:7b`  |
| 24GB single GPU         | `qwen3.6:27b`  | `qwen3-coder:30b`  | `qwen2.5vl:32b` |
| Multi-GPU server        | `llama3.3:70b` | `qwen3-coder:30b`  | `qwen2.5vl:72b` |

**Changing a row in the YAML table is the entire upgrade procedure.**

---

## 8. Updating SovereignAI After Code Changes

Because the package is installed in **editable mode** (`pip install -e .`), most code changes take effect immediately on next `sovai` launch — no reinstall needed.

### For code changes (no new dependencies)

```bash
# Just restart sovai — changes are live
sovai
```

### If you added or changed dependencies in `pyproject.toml`

```bash
pip install -e .   # re-install with new deps
sovai
```

### If you changed `models.yaml` (the default config)

The user's `~/.sovereignai/config.yaml` (if it exists) takes precedence. To apply shipped-default changes:

```bash
# Option A: Edit user config directly
sovai config edit

# Option B: Delete user config to fall back to shipped defaults
# WARNING: this resets all your custom settings
rm ~/.sovereignai/config.yaml   # Linux/macOS
del %USERPROFILE%\.sovereignai\config.yaml   # Windows
```

### Verifying after update

```bash
sovai doctor   # confirms all dependencies still present
```

---

## 9. Network Isolation & Air-Gap Proof

### What "air-gapped" means here

There is no HTTP client in this codebase capable of reaching a non-localhost address. The only outbound connection the app makes is `127.0.0.1:11434` (the local Ollama server).

This is enforced at two independent layers:

### Layer 1 — Application level (always active)

The `net_guard` module polls all network connections every 500ms. Open `/net` in the TUI to see:

- Every connection (process, local addr, remote addr, state)
- A persistent count of "external connection attempts this session" — should always read **0**
- An immediate red alert if any external connection is ever detected

### Layer 2 — OS-level firewall (configured by install scripts)

**Linux:** `nftables` rules drop all outbound traffic except loopback. Applied by `scripts/install.sh`.

```bash
# Check if rules are active
sudo nft list ruleset | grep sovai

# Apply manually
sudo nft -f - <<'EOF'
table inet sovai_guard {
  chain output {
    type filter hook output priority 0; policy accept;
    oif lo accept
    ip daddr 127.0.0.1 accept
    log prefix "SOVAI-BLOCKED: " counter drop
  }
}
EOF
```

**Windows:** Windows Defender Firewall outbound block rule for `sovai.exe`. Applied by `scripts/install.ps1` (requires Administrator).

```powershell
# Check if rule exists
Get-NetFirewallRule -DisplayName "SovereignAI-Egress-Block"

# Apply manually (Administrator PowerShell)
New-NetFirewallRule `
  -DisplayName "SovereignAI-Egress-Block" `
  -Direction Outbound -Action Block `
  -Program "$env:USERPROFILE\path\to\agent\.venv\Scripts\sovai.exe" `
  -Enabled True
```

### Running the live air-gap proof

```bash
bash scripts/verify_airgap.sh
```

Output (expected):

```
  PASS  api.anthropic.com is unreachable from host
  PASS  api.openai.com is unreachable from host
  PASS  Ollama local API is reachable (as expected)
  PASS  Docker sandbox (--network none) cannot reach api.anthropic.com
  PASS  No external connections detected from this process

  ✅  AIR-GAP VERIFICATION: PASSED
```

---

## 10. Four Demo Scenarios

Run these in order with `/net` open on a second pane to prove sovereignty throughout.

### Scenario 1 — Auto model selection

1. Launch `sovai` in AUTO mode
2. Ask: _"Write a short summary of what air-gapped systems are and why they matter."_
   - Watch routing line: `→ routed to general (qwen3.5:9b)`
3. Then ask: _"Write a Python function that checks if a file has been modified in the last 24 hours."_
   - Watch routing line switch: `→ routed to coding (qwen2.5-coder:7b)`

**The headline feature — demonstrated in 2 messages.**

### Scenario 2 — Agentic document generation

1. Attach a scanned inspection report (PDF or image): mention the path in your message
2. Ask: _"Extract the key findings from this inspection report and draft an approval note as a Word document."_
3. Watch the agent:
   - Route to `vision` → extract findings from the image
   - Hand off to `general` model for drafting
   - Call `generate_docx` → produce `approval_note.docx`
   - Show a file card: `📎 File produced: approval_note.docx`

### Scenario 3 — Coding with sandbox

1. Ask: _"Write a Python script that reads a CSV and calculates the average of the 'value' column. Include a deliberate off-by-one bug. Then find and fix the bug and show tests passing."_
2. Watch the agent:
   - Write the code via `fs_write`
   - Run it in Docker sandbox via `sandbox_exec` → failing output shown
   - Fix the bug → run again → passing output shown
   - All with `--network none` — the sandbox is physically cut off

### Scenario 4 — Multimodal (vision)

1. Drop in a photograph of a handwritten note or a P&ID diagram
2. Ask: _"What is the tag number of the valve in the top-right of this diagram?"_
3. Watch it route to `vision`, send the image to `qwen2.5vl:7b`, and answer grounded in the actual image

### Scenario 5 — Sovereignty proof

After all the above:

```bash
# In a separate terminal:
bash scripts/verify_airgap.sh
```

All five tests should show `PASS`. The `/net` panel should still show `0 external calls`.

---

## 11. Troubleshooting (`sovai doctor`)

```bash
sovai doctor
```

This checks and reports exactly what's missing:

| Issue reported     | Fix                                |
| ------------------ | ---------------------------------- |
| Python < 3.11      | Install Python 3.11+               |
| Ollama not running | `ollama serve`                     |
| Model not pulled   | `ollama pull <model-tag>`          |
| Docker not running | Start Docker Desktop               |
| Config dir missing | Created automatically on first run |

Run `sovai doctor` again after each fix until it shows all green.

### Common issues

**`sovai: command not found`**  
→ Venv not activated. Run `source agent/.venv/bin/activate` (Linux) or `agent\.venv\Scripts\Activate.ps1` (Windows) first.

**TUI opens but chat does nothing / hangs**  
→ Ollama is not running. Open another terminal and run `ollama serve`.

**Router returns wrong category**  
→ Ask is ambiguous. Override with `/models` to pin a specific model for that task.

**Sandbox fails: "image not found"**  
→ Pre-pull the Docker images: `docker pull python:3.11-slim` etc.

**Knowledge base search returns nothing**  
→ Run `sovai kb add /path/to/documents` first. Check `sovai kb status` for chunk count.

---

## 12. If You Clone This Repo (New Machine Setup)

If someone clones the repository for the first time on a new machine, here is the complete sequence:

```bash
# 1. Clone the repository
git clone <repo-url> sovereignai
cd sovereignai/agent

# 2. Install prerequisites (if not already installed)
#    - Python 3.11+: https://python.org
#    - Ollama: https://ollama.com/download  → then run: ollama serve
#    - Docker Desktop: https://docker.com/products/docker-desktop

# 3. Run the installer (automated)
#    Linux/macOS:
bash scripts/install.sh

#    Windows (PowerShell as Administrator):
.\scripts\install.ps1

# 4. If you prefer manual setup:
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows
pip install -e .
sovai models pull                 # pulls all 5 Ollama models (~14GB)
docker pull python:3.11-slim
docker pull node:20-slim
docker pull gcc:13

# 5. Verify
sovai doctor

# 6. Launch
sovai
```

### For air-gapped environments (no internet on target machine)

Do this on a connected machine first:

```bash
# Download all pip packages to a vendor folder
pip download -r <(pip freeze) -d ./vendor/

# Pull all Docker images and export them
docker pull python:3.11-slim && docker save python:3.11-slim -o vendor/python311-slim.tar
docker pull node:20-slim     && docker save node:20-slim     -o vendor/node20-slim.tar
docker pull gcc:13           && docker save gcc:13           -o vendor/gcc13.tar

# Pull all Ollama models (they're stored in ~/.ollama/models by default)
ollama pull llama3.2:3b qwen3.5:9b qwen2.5-coder:7b qwen2.5vl:7b nomic-embed-text
```

Then transfer the whole repo (including `vendor/` and `~/.ollama/models`) to the air-gapped machine:

```bash
# On the air-gapped machine:
pip install --no-index --find-links=./vendor sovereignai

# Load Docker images
docker load -i vendor/python311-slim.tar
docker load -i vendor/node20-slim.tar
docker load -i vendor/gcc13.tar

# Ollama models are already in ~/.ollama/models (transferred from source machine)

# Launch
sovai
```

---

_SovereignAI — Built for operators who cannot compromise. Everything on this machine, nothing in the cloud._
