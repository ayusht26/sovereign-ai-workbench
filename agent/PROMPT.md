# SovereignAI — Build Specification & Operator's Guide
**Codename:** SovereignAI | **CLI command:** `sovai` | **Category:** Air-gapped, multi-model, agentic AI workbench for confidential industrial/government work

---

## HOW TO USE THIS DOCUMENT

This file is written to be **pasted directly into a coding agent** (Claude Code, OpenCode, Cursor, etc.) as the master build instruction. It is written in second person, addressed to that agent ("You will build..."). Everything needed — architecture, file structure, exact library choices, tool schemas, UI spec, model routing logic, network-isolation proof, and the demo script — is in here. Part A is the build prompt. Part B (near the end) is the finished-product operator's guide you hand to end users once it's built.

Feed this whole document to your coding agent as one instruction, then iterate section by section if it runs out of context in one shot (it's designed to be built incrementally: Milestone 1 → 6, in order, each one independently demoable).

---

# PART A — THE BUILD PROMPT

You are an expert systems engineer. Build **SovereignAI**, a self-hosted, fully air-gapped, terminal-based AI agent workbench, similar in spirit and UX to Claude Code and OpenCode, but designed for on-premise deployment inside refineries, PSUs, defence-linked manufacturing units, and government offices where no data may ever leave the local network. Follow this specification exactly. Where you must make a judgment call not covered here, prefer: (1) simplicity and reliability over cleverness, (2) explicit configuration over hidden magic, (3) anything that makes the "nothing leaves this machine" claim easier to visibly prove.

## 1. Product identity

- **Product name:** SovereignAI
- **Binary / CLI command:** `sovai` (typing `sovai` in any terminal, from any directory, launches the full-screen TUI)
- **Tagline** (shown under the banner): `Local models. Local data. Zero external calls.`
- **Startup ASCII banner** — render this exact block art at launch, in the app's accent color, before the input box appears (matches the visual weight of the OpenCode/Claude Code splash screens the product is modeled on):

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

Render this with `pyfiglet` (font `ansi_shadow`) at build time if you want it regenerated programmatically rather than hard-coded, but ship the literal string above as the default so it renders identically on any machine even without `pyfiglet` installed. Color it with a two-tone gradient: the block glyphs in steel-blue/cyan (`#5FA8D3` → `#2E5A7A` top-to-bottom), the subtitle line in dim grey, and the `🔒 OFFLINE` / `🔓 ONLINE-BLOCKED` indicator in amber (`#D9A441`) — this becomes the persistent air-gap indicator reused in the status bar.

## 2. High-level architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         SovereignAI TUI (Textual)                    │
│  banner · chat thread · input box · model palette · status bar       │
└───────────────────────────────┬────────────────────────────────────┘
                                 │
┌───────────────────────────────▼────────────────────────────────────┐
│                        Agent Orchestrator                            │
│  session state · plan/act/observe loop · tool dispatcher · logging   │
└───────────┬───────────────────┬───────────────────┬────────────────┘
            │                   │                   │
   ┌────────▼───────┐  ┌────────▼────────┐ ┌────────▼─────────┐
   │  Model Router    │  │   Tool Registry  │ │  Session Store    │
   │  (task→model)    │  │  (fs, sandbox,   │ │  (sqlite, local)  │
   │  AUTO / manual   │  │  sheet, docgen,  │ └───────────────────┘
   └────────┬─────────┘  │  vision, rag)    │
            │            └────────┬─────────┘
   ┌────────▼──────────────────────▼─────────┐
   │            Ollama (localhost:11434)       │
   │  router · general · coder · vision ·      │
   │  embedding — loaded/unloaded on demand    │
   └───────────────────────────────────────────┘
            │
   ┌────────▼─────────┐   ┌────────────────┐   ┌───────────────────┐
   │ Local Vector DB    │   │  Code Sandbox   │   │  Network Guard     │
   │ (Chroma, on disk)  │   │  (Docker,       │   │  (firewall rules + │
   │  SOPs/manuals/     │   │  --network=none)│   │  live conn monitor)│
   │  correspondence    │   └────────────────┘   └───────────────────┘
   └────────────────────┘
```

Everything below the TUI box lives on one machine. There is no cloud call anywhere in this diagram, by construction — not "disabled," **not implemented**. There is no HTTP client in the codebase capable of reaching a non-localhost, non-LAN-KB address. This is the single most important design constraint in the whole system; enforce it at the code-review level, not just the network level (see §11).

## 3. Tech stack (and why)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Best ecosystem overlap between TUI, ML tooling, OCR, and Office-file generation — one runtime, no polyglot glue |
| TUI framework | [`textual`](https://textual.textualize.io/) (+ `rich`) | Production-grade terminal UI framework: real widgets, CSS-like styling, mouse support, async-native — capable of reproducing the OpenCode/Claude Code look (boxed input, status bar, command palette, streaming markdown) |
| LLM runtime | [`ollama`](https://ollama.com) via its Python client + REST API on `127.0.0.1:11434` | Already does model load/unload/quantization management, exposes a clean local API, has a built-in tool-calling protocol, and is the explicit tool the user specified |
| Agent loop | Hand-rolled ReAct-style loop (do **not** pull in a heavy framework) | Full control over the plan→act→observe loop, tool schema, and stopping conditions is required for an auditable, air-gapped system; a framework adds opaque network-capable dependencies you'd have to audit anyway |
| Vector store | [`chromadb`](https://www.trychroma.com/) (persistent, local, embedded — no server) | Zero external dependency, pure on-disk local DB, good enough at the corpus sizes (thousands of SOPs/manuals) this system targets |
| Embeddings | `nomic-embed-text` via Ollama | Ollama-native, small (~280MB), fast, well-supported |
| Code sandbox | `docker` Python SDK, containers run with `--network none`, CPU/mem/time limits | Real isolation for arbitrary code execution; network is physically cut at the container level, not just policy |
| Office file generation | `python-docx`, `python-pptx`, `openpyxl` | Standard, offline, no external services |
| PDF / scanned doc handling | `pymupdf` (fitz) for text-layer PDFs, `pdf2image` + `poppler-utils` to rasterize scanned pages for the vision model | Local, no cloud OCR API |
| CLI entry point | `typer` (thin wrapper) launching the Textual `App` | Clean `sovai`, `sovai --help`, `sovai doctor`, `sovai models pull` subcommands |
| Network monitor | `psutil` (process/connection enumeration) + optional `nftables`/`iptables` rules applied at install time | Two independent layers: a hard kernel-level block, and a visible, live application-level proof for the demo |
| Local DB (sessions, audit log) | `sqlite3` (stdlib) | Zero-config, local, auditable, easy to inspect with any SQLite browser for compliance review |

Do not add any package whose functionality requires an internet call to be useful (telemetry SDKs, license-check libraries, "phone home" update checkers, etc.). Pin all dependencies in `pyproject.toml` and vendor/mirror them internally for the actual air-gapped install (see §12.3).

## 4. Repository structure

```
sovereignai/
├── pyproject.toml
├── README.md
├── sovereignai/
│   ├── __init__.py
│   ├── cli.py                 # typer entrypoint -> `sovai`
│   ├── app.py                 # Textual App class, screens, layout
│   ├── banner.py               # ASCII art + color gradient renderer
│   ├── config.py               # loads/validates ~/.sovereignai/config.yaml
│   ├── orchestrator/
│   │   ├── agent_loop.py       # plan -> act -> observe -> iterate
│   │   ├── router.py           # task classification + model selection (AUTO)
│   │   ├── session.py          # session state, token/cost accounting
│   │   └── audit_log.py        # local append-only jsonl + sqlite audit trail
│   ├── tools/
│   │   ├── base.py             # Tool ABC, JSON schema validation
│   │   ├── fs_tools.py         # fs_read, fs_write, fs_list, fs_glob
│   │   ├── sandbox_tool.py     # docker-based code execution
│   │   ├── sheet_tool.py       # openpyxl read/write/formula tool
│   │   ├── docgen_tool.py      # docx/pptx/xlsx deliverable generation
│   │   ├── vision_tool.py      # image/scanned-PDF understanding via VLM
│   │   ├── rag_tool.py         # local knowledge-base search
│   │   └── shell_tool.py       # constrained, logged shell commands (non-sandbox, host-level, allow-listed binaries only)
│   ├── knowledge_base/
│   │   ├── ingest.py           # watch folder -> chunk -> embed -> store
│   │   └── store.py            # Chroma wrapper
│   ├── net_guard/
│   │   ├── monitor.py          # live connection watcher (psutil)
│   │   └── firewall.py         # applies/validates the OS-level egress block
│   ├── ui/
│   │   ├── screens/
│   │   │   ├── main_screen.py
│   │   │   ├── model_palette.py
│   │   │   ├── command_palette.py
│   │   │   ├── net_monitor_screen.py
│   │   │   └── session_browser.py
│   │   └── widgets/
│   │       ├── status_bar.py
│   │       ├── chat_thread.py
│   │       ├── tool_call_block.py
│   │       └── thought_block.py
│   └── models.yaml             # default task->model map, shipped, user-editable
├── scripts/
│   ├── install.sh              # installs deps, pulls default models, applies firewall
│   └── verify_airgap.sh        # runs the demo network-proof check
└── tests/
    └── ...
```

## 5. Model routing subsystem — the core "auto-pick the right model" feature

### 5.1 Task taxonomy

Define a fixed, small set of task categories. Every request is classified into exactly one:

| Task category | Typical trigger | Model role |
|---|---|---|
| `general` | Q&A, drafting notes/emails, summarizing plain text, approval-note writing, planning | general-reasoning model |
| `coding` | "write/fix/refactor/debug/run this code", anything touching a sandbox or repo | coding model |
| `vision` | An image or scanned PDF/photo is attached, or the request references a drawing/handwritten note/P&ID | vision-language model |
| `spreadsheet` | Reading/writing/calculating in `.xlsx`, financial tables, engineering calc sheets | general or coding model + `sheet_tool` |
| `document_qa` | "what does the SOP say about X", "find the correspondence about Y" | general model + `rag_tool` |
| `planning` | Multi-step task requiring the agent loop itself (default for anything not a single-shot answer) | general or coding model, orchestrating other tools |

### 5.2 The router model

Keep one small model **always resident** in VRAM (see §5.4) whose only job is classification — this is what makes AUTO mode fast (no waiting for a 7B model to load just to find out which 7B model you actually needed).

- Model: `llama3.2:3b` (stable, well-established, ~2GB at Q4 — safe default)
- Faster/newer alternative to trial if available in your Ollama library at build time: `qwen3.5:0.8b` (~1GB, very fast) — verify with `ollama list`/`ollama.com/library` since exact tags shift; keep both configured with `llama3.2:3b` as the guaranteed fallback.
- Router prompt template (send as a system prompt with the user's raw request as the user turn; **temperature 0**, **max_tokens ~40**, and require strict JSON output):

```text
You are a task router. Classify the user's request into exactly one category:
general | coding | vision | spreadsheet | document_qa | planning

Rules:
- If an image or scanned document is attached or referenced, always choose "vision".
- If the request involves writing, running, fixing, or reviewing code, choose "coding".
- If it references a spreadsheet, financial table, or asks for a calculation with rows/columns, choose "spreadsheet".
- If it asks what a manual/SOP/correspondence/past document says, choose "document_qa".
- If it is a multi-step task with more than one deliverable or clearly needs iteration, choose "planning".
- Otherwise choose "general".

Respond with ONLY this JSON, nothing else:
{"category": "<one of the six>", "confidence": <0.0-1.0>, "reason": "<max 12 words>"}
```

- Parse the JSON. If parsing fails or confidence `< 0.55`, fall back to `general` and surface a small UI note: `⚠ auto-routing uncertain, used general model — override with /models`.
- **Always show the routing decision in the UI**, dimmed, above the response: `→ routed to coding (qwen2.5-coder:7b) · 0.91 confidence`. This is both good UX and part of the "prove it's actually doing model selection" demo requirement.

### 5.3 Default model map (`models.yaml`) — tuned for a single RTX 4060 8GB laptop/workstation demo box

```yaml
# ~/.sovereignai/config.yaml -> models section (defaults, user-editable)
hardware_profile: "8gb_vram"   # 8gb_vram | 16gb_vram | 24gb_vram | server_multi_gpu

router:
  model: "llama3.2:3b"
  keep_alive: "-1"              # stays resident permanently, it's tiny

models:
  general:
    model: "qwen3.5:9b"         # primary — best quality/VRAM ratio for chat, summarizing,
    fallback: "llama3.1:8b"     # approval-note drafting, planning at this tier
  coding:
    model: "qwen2.5-coder:7b"   # strongest coding-specific model that fits 8GB cleanly
    fallback: "llama3.1:8b"
  vision:
    model: "qwen2.5vl:7b"       # best OCR/document/chart understanding at this tier
    fallback: "llava:7b"
  embedding:
    model: "nomic-embed-text"   # RAG embeddings, tiny, always resident alongside router

ollama:
  host: "http://127.0.0.1:11434"
  max_loaded_models: 1          # forces swap-not-stack on 8GB cards; router+embedder are exempted
  request_timeout_s: 600
```

Only **one** 7–9B "worker" model needs to be resident in VRAM at a time on an 8GB card (roughly 5–6GB at Q4_K_M), leaving headroom for the always-resident router (~2GB) and embedder (~300MB). Set the environment variable `OLLAMA_MAX_LOADED_MODELS=1` (or 2, to also pin the router) when starting the Ollama service, and rely on Ollama's own automatic load/unload — this is exactly the mechanism that makes "auto-pick the right model per task, swap seamlessly" work without you writing a custom model-swapping scheduler.

### 5.4 Upgrade path (document this in the config comments, don't build it yet)

When this moves from a demo laptop to an actual on-prem GPU server (the "120B-class hardware" the brief mentions), the *only* thing that should change is `models.yaml` — no code changes, because the router and orchestrator only ever see role names (`general`, `coding`, `vision`), never hardcoded model tags:

| Hardware | general | coding | vision |
|---|---|---|---|
| 8GB (this build) | `qwen3.5:9b` | `qwen2.5-coder:7b` | `qwen2.5vl:7b` |
| 24GB single GPU | `qwen3.6:27b` | `qwen3-coder:30b` (MoE) | `qwen2.5vl:32b` |
| Multi-GPU server | `gpt-oss:120b` or dense 70B-class | `qwen3-coder:30b` / larger coder MoE | `qwen2.5vl:72b` |

This table is exactly the proof point for the RFP's "new open-weight models addable later without redesigning the system" requirement — make sure a code reviewer can see that swapping a row in this YAML is the entire upgrade procedure.

## 6. The agent loop (plan → act → observe → iterate)

This is what makes SovereignAI behave like Claude Code / Codex instead of a single-shot chatbot.

```python
# orchestrator/agent_loop.py (pseudocode-level detail — implement fully)

MAX_ITERATIONS = 25

def run_agent_turn(session, user_message):
    session.append("user", user_message)
    category, model_name, confidence = router.classify(user_message, session.context)
    session.emit_ui_event("routing_decision", category, model_name, confidence)

    for step in range(MAX_ITERATIONS):
        response = ollama_chat(
            model=model_name,
            messages=session.messages_for_model(),
            tools=tool_registry.schemas_for(category),   # only expose relevant tools
            stream=True,
        )
        session.stream_to_ui(response)                    # shows "Thought:" block live

        if response.tool_calls:
            for call in response.tool_calls:
                session.emit_ui_event("tool_call_start", call)
                result = tool_registry.dispatch(call.name, call.arguments)  # sandboxed/validated
                session.emit_ui_event("tool_call_result", call, result)
                session.append("tool", result, tool_call_id=call.id)
            continue   # loop again: model observes tool results, plans next step
        else:
            session.append("assistant", response.text)
            audit_log.record(session.id, user_message, category, model_name, response, tool_calls_made=step)
            return response.text

    session.emit_ui_event("max_iterations_reached")
    return "I've hit the step limit for this task — here's what I've completed so far: ..."
```

Key behaviors to implement precisely:

- **Streaming to the UI at every step**, not just at the end — the person watching should see "Thought → tool call → tool result → next thought" exactly like the reference screenshots show a collapsible `+ Thought: 409ms` block.
- **Tool exposure is category-scoped**: a `general` document-summary task shouldn't be offered `sandbox_exec`; a `coding` task shouldn't be offered `docgen_pptx`. This keeps the model focused and keeps the audit trail meaningful (§14).
- **Every tool call and result is written to the audit log** before being shown to the model, so even if the process crashes mid-task the record survives.
- **Hard stop at `MAX_ITERATIONS`** with a partial-progress summary — never let it loop silently forever burning GPU time.
- **User can interrupt** (`esc`, matching the reference UI's `esc interrupt` hint) at any point; the in-flight tool call finishes, in-flight model generation is cancelled via the Ollama streaming cancel, and control returns to the input box.

## 7. Tool specification

Implement every tool as a subclass of a common `Tool` base class with: `name`, `description`, `json_schema` (OpenAI-style function schema, since Ollama's tool-calling API follows that convention), and `run(**kwargs) -> ToolResult`. All tools log their full input/output to the audit log.

### 7.1 `fs_read` / `fs_write` / `fs_list` / `fs_glob`
- Scoped to a **workspace root** (the current working directory `sovai` was launched from, or a configured allow-list of directories). Any path outside the workspace root is rejected with a clear error, not silently redirected.
- `fs_write` always shows a diff preview in the UI before committing when overwriting an existing file (mirrors Claude Code's edit-confirmation UX); creation of new files can be auto-approved per session settings.

### 7.2 `sandbox_exec` (code execution)
- Spins up a Docker container per execution: `docker run --rm --network none --memory=2g --cpus=2 --read-only --tmpfs /tmp -v {workspace}:/workspace:rw <lang-image> ...`
- Language images: `python:3.11-slim`, `node:20-slim`, `gcc:13` at minimum — pre-pull these during install so the sandbox never needs network access at runtime.
- Timeout: 60s default, configurable per call, hard-killed via `docker stop` on expiry.
- stdout/stderr/exit code all returned to the model and shown in an expandable "Tool: sandbox_exec" block in the UI, matching the tool-call rendering style in the reference screenshots.
- **`--network none` is non-negotiable** — this is the component most likely to be used to smuggle data out if misconfigured; test it explicitly (`verify_airgap.sh` should attempt an outbound curl from inside a sandbox container and assert it fails).

### 7.3 `sheet_tool`
- `read_sheet(path, sheet_name=None) -> structured JSON of cells/formulas`
- `write_sheet(path, updates: list[{cell, value, formula?}])`
- `create_sheet(path, sheet_name, headers, rows)`
- Built on `openpyxl`; preserves existing formatting/formulas on read-modify-write cycles rather than regenerating the whole file.

### 7.4 `docgen_tool` (the "real deliverables" requirement)
- `generate_docx(title, sections: list[{heading, body, level}], output_path)` — approval notes, reports, memos
- `generate_pptx(title, slides: list[{layout, title, bullets, notes}], output_path)`
- `generate_xlsx(...)` — reuses `sheet_tool`'s writer
- Every generated file is written under the session's workspace and immediately surfaced in the UI as a clickable/openable file card, exactly like Claude Code's "here's the file" moment — this is the payoff of the whole agentic loop and should feel like the main event, not a side effect.

### 7.5 `vision_tool` (multimodal — scanned PDFs, drawings, handwriting, photos)
- Input: image path(s) or a PDF path.
- If PDF: rasterize each page with `pdf2image` at 200 DPI, feed pages to the vision model one at a time (or batched if the model supports multi-image), reassemble a structured page-by-page extraction.
- Prompt template forces structured output for downstream use:
```text
Extract all readable text, labels, and key findings from this image.
Return JSON: {"raw_text": "...", "key_findings": ["..."], "tables": [...], "handwritten_notes": ["..."], "confidence": "high|medium|low"}
If handwriting is illegible, say so explicitly rather than guessing.
```
- The output of `vision_tool` feeds directly into the `general` model in the same agent turn for summarization/drafting — this is the exact "scanned inspection report → key findings → approval note in Word" pipeline required by the demo.

### 7.6 `rag_tool` (local knowledge base)
- `search(query, top_k=5, filters={}) -> [{chunk, source_file, score}]`
- Backed by ChromaDB persistent client at `~/.sovereignai/kb/chroma/`.
- Never returns raw chunks larger than ~800 tokens; always includes source filename + page/section so the model can cite it in the drafted output ("per SOP-114 §3.2...").

### 7.7 `shell_tool` (host-level, NOT sandboxed — use sparingly)
- Allow-list only: `ls`, `cat`, `grep`, `find`, `git status/diff/log` (read-only git operations). Nothing that writes or has network capability (`curl`, `wget`, `ssh`, `scp`, `git push`, `git clone` from remote, `pip install`, `npm install` from registry are all explicitly on a deny-list, checked before dispatch, not just by convention).
- This tool exists for cheap host introspection (checking `cwd`, listing files) without paying the Docker container startup cost; anything actually executing untrusted logic goes through `sandbox_exec` instead.

### 7.8 No web/network tool exists, period
There is deliberately **no** `web_search`, `http_fetch`, `email_send`, or any tool whose implementation opens a non-loopback, non-LAN-KB socket. Do not stub one out "for later" — its mere presence in the tool registry, even disabled by a config flag, is a bigger audit risk than not writing the code at all.

## 8. Local knowledge base (RAG) connector

- `sovai kb add <path>` — ingest a folder of SOPs, manuals, past correspondence (`.pdf`, `.docx`, `.txt`, `.md`, `.eml`).
- Ingestion pipeline: extract text (PyMuPDF for PDFs with a text layer; route to `vision_tool` OCR for scanned/image-only PDFs) → chunk (~500 tokens, 50-token overlap) → embed via `nomic-embed-text` → upsert into Chroma with metadata `{source_path, ingested_at, doc_type}`.
- `sovai kb status` shows document count, chunk count, last ingestion time, disk size — all local numbers, useful for the demo's "here's what it's grounded in" moment.
- Watch-mode (`sovai kb watch <path>`) re-ingests on file change for a live-updating knowledge base as new correspondence/SOPs land.

## 9. TUI specification (the actual look and feel)

Model the screens closely on the reference OpenCode screenshots supplied, adapted to SovereignAI's identity.

### 9.1 Main screen layout
```
┌─────────────────────────────────────────────────────────────────────────┐
│ SovereignAI                                                        ─ □ x │
├───────────────────────────────────────────┬─────────────────────────────┤
│                                             │  Session — 2026-08-28 16:06 │
│         [ASCII BANNER on empty state]      │                             │
│                                             │  Context                   │
│   ┌───────────────────────────────────┐   │  4,102 tokens · 3% used     │
│   │ Ask anything... "Draft an          │   │  $0.00 spent (fully local)  │
│   │  approval note from this report"   │   │                             │
│   └───────────────────────────────────┘   │  Model                      │
│                                             │  AUTO → qwen2.5vl:7b        │
│   AUTO  ·  📁 /data/projects/unit-4        │                             │
│                                             │  Network                   │
│                                             │  🔒 0 external calls        │
│                                             │  (12 tool calls, 0 egress)  │
│                                             │                             │
│  tab agents   ctrl+p commands   esc interrupt          SovereignAI 0.1.0 │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Current working directory is always visible** in the bottom-left of the input area (`📁 /data/projects/unit-4`) exactly as requested — this doubles as the workspace root for `fs_*` tools, so what you see is what the agent can touch. `cd`-equivalent: `/cwd <path>` command switches it live.
- **Model badge**: shows `AUTO → <resolved model>` when in AUTO mode (resolved model updates per-message as routing changes), or the pinned model name when manually selected.
- **Right-hand panel** mirrors the reference screenshots' session/context panel, but swaps `$ spent` semantics (always $0.00, it's local — call this out explicitly, it's a nice, honest flex) and swaps the `LSP` block for a **Network** block showing live egress-attempt count, which should read `0` for the entire session, always, and turn the whole badge red with an alarm if it is ever non-zero.

### 9.2 Model palette (`/models` or `ctrl+p` → "models")
Reproduce the reference `/models` list-style palette:
```
┌───────────────────────────────────────────────────────────┐
│ AUTO             Auto-detect the right model per task       │
│ qwen3.5:9b        General reasoning, drafting, summaries    │
│ qwen2.5-coder:7b  Coding, debugging, running code            │
│ qwen2.5vl:7b      Images, scanned docs, drawings, OCR         │
│ ──────────────────────────────────────────────────────────│
│ /kb              Manage local knowledge base                │
│ /net             Open network monitor                       │
└───────────────────────────────────────────────────────────┘
```
Arrow keys + enter to select, matching the reference's highlighted-row behavior. `AUTO` is the default and should be visually distinguished (e.g., pinned to top, bold) since it's the headline feature.

### 9.3 Command palette (`ctrl+p`)
At minimum: `/models`, `/auto`, `/kb add|status|watch`, `/net`, `/new` (new session), `/sessions` (browse past sessions), `/review` (review file diffs, mirroring OpenCode's `/review [commit|branch|pr]`), `/cwd <path>`, `/sandbox status`, `/help`.

### 9.4 Chat thread rendering
- User turns: left-aligned, boxed, as in the reference screenshots.
- Assistant "Thought" blocks: collapsible, prefixed `+ Thought: <duration>`, dim/italic — expand to show the model's raw planning text.
- Tool call blocks: their own bordered block, header `Tool: sandbox_exec` / `Tool: docgen_tool` etc., showing arguments, then result, collapsible after completion, auto-expanded while running with a spinner.
- File-output cards: when `docgen_tool` or `fs_write` produces a deliverable, render a distinct card with filename, size, and an "open" hint — this should feel like the payoff moment of the whole task.
- Footer status line always shows: `<mode> · <model badge> · <elapsed>` on the left, `tab agents  ctrl+p commands  esc interrupt` on the right — same information density as the reference screenshots.

### 9.5 Visual theme
Dark background (`#0D0F12`), single accent color family (steel-blue/cyan for structure, amber only for the air-gap/network indicator and warnings — never mix accent meanings). Monospace throughout. No emoji except the fixed set used for state (`🔒`/`🔓` for network, `📁` for cwd, `⚠` for warnings) — keep it restrained and professional, this is going into a government office, not a hobby project.

## 10. Network isolation — the actual "sovereign" proof

Implement **two independent layers**, and make both visible in the demo:

### 10.1 Kernel-level block (the real guarantee)
`scripts/install.sh` applies an `nftables`/`iptables` egress policy on the host: allow loopback, allow the LAN subnet the knowledge-base fileserver or Ollama server (if on a separate box) lives on, **drop everything else outbound**, logged. Provide `scripts/verify_airgap.sh` that:
1. Attempts `curl -m 3 https://api.anthropic.com` from the host → expect failure.
2. Attempts the same curl **from inside a fresh `sandbox_exec` container** → expect failure (proves the sandbox's `--network none` isn't the only thing stopping it, and that even a compromised/malicious generated script can't exfiltrate).
3. Prints a clear PASS/FAIL summary.

### 10.2 Application-level live monitor (the visible proof, for the demo)
`net_guard/monitor.py` polls `psutil.net_connections()` filtered to the SovereignAI process tree (main process + any spawned Docker containers) every 500ms, and feeds a rolling log into the `/net` screen and the main screen's Network panel:
```
┌── Network Monitor ─────────────────────────────────────────┐
│ Process           Local             Remote          State   │
│ ollama             127.0.0.1:11434   —               LISTEN  │
│ sovai              127.0.0.1:52344   127.0.0.1:11434 ESTAB   │
│                                                              │
│ External connection attempts this session: 0                │
│ Last checked: 16:07:03                                       │
└──────────────────────────────────────────────────────────────┘
```
This is the panel to have open on a second monitor/projector during the live demo, per the RFP's explicit ask for "logs or a visible network monitor" as the actual proof of the sovereign claim.

## 11. Packaging & installation

- `pyproject.toml` with `[project.scripts] sovai = "sovereignai.cli:main"`.
- Install for development: `pip install -e . --break-system-packages` (or inside a venv, preferred for a real deployment).
- Install for end users: build a wheel + vendor all pip dependencies into an internal artifact repository (air-gapped networks can't hit PyPI) — `pip download -r requirements.txt -d ./vendor/` on a connected machine once, then `pip install --no-index --find-links=./vendor sovereignai` on the air-gapped target.
- `scripts/install.sh` does, in order: install Python deps → pull Docker sandbox images → pull the four Ollama models (§5.3) → apply the firewall rules (§10.1) → run `verify_airgap.sh` → print a success banner telling the operator to type `sovai`.
- Result: after installation, **typing `sovai` in any terminal, from any directory, launches SovereignAI**, defaulting its workspace/cwd to wherever it was launched from.

## 12. Configuration file

`~/.sovereignai/config.yaml` — holds the model map (§5.3), workspace allow-list, sandbox resource limits, KB paths, and network-guard settings. Ship a commented default; `sovai config edit` opens it in `$EDITOR`; `sovai doctor` validates it and checks that Ollama, Docker, and the required models are all present, printing exactly what's missing and the one-line fix for each.

## 13. Audit logging (governance requirement, implicit in "government office" deployment)

Every turn writes an append-only record to `~/.sovereignai/audit/audit.jsonl` **and** a queryable `sqlite` mirror: timestamp, session id, user (OS username), routed category + model + confidence, every tool call with full arguments/results, final response, token counts, wall-clock duration. No response content is ever redacted from this log — it is the compliance trail, kept entirely local, never transmitted. Provide `sovai audit export --session <id> --format docx` to produce a reviewable record for an internal compliance officer.

## 14. Build order (milestones — build and demo each before moving to the next)

1. **M1** — CLI skeleton + Textual shell + ASCII banner + `/models` palette wired to a hardcoded model list (no Ollama yet). Proves the UI shell.
2. **M2** — Wire to Ollama; single-model chat working end to end, streaming into the chat thread; status bar shows real cwd and real model.
3. **M3** — Router + AUTO mode across at least `general` and `coding`; show the routing-decision line in the UI. *(This alone satisfies the RFP's "auto selection across at least two task types.")*
4. **M4** — Agent loop + `fs_tools` + `sandbox_exec`; a coding task is planned, run in the Docker sandbox, and verified end to end. *(Satisfies "coding task run and verified in a sandbox.")*
5. **M5** — `vision_tool` + `docgen_tool`; a scanned PDF → key findings → drafted `.docx` approval note, fully agentic. *(Satisfies the flagship multimodal + agentic + real-deliverable demo scenario.)*
6. **M6** — `rag_tool` + knowledge base ingestion; net_guard visible monitor + kernel firewall + `verify_airgap.sh`. *(Satisfies grounding-in-org-knowledge and the sovereignty proof.)*

Each milestone should be independently runnable and demoable — do not let M6's network-guard work block M3's routing demo, they're unrelated subsystems.

---

# PART B — OPERATOR'S GUIDE (once built)

## 15. Installing SovereignAI

```bash
# 1. Prerequisites (one-time, on the target machine or a staging machine for air-gapped transfer)
#    - Ollama installed (https://ollama.com/download)
#    - Docker installed and running
#    - Python 3.11+

# 2. Pull the models this build ships with (run once; ~14GB total download)
ollama pull llama3.2:3b          # router — always resident, classifies each request
ollama pull qwen3.5:9b           # general reasoning / drafting / summaries
ollama pull qwen2.5-coder:7b     # coding
ollama pull qwen2.5vl:7b         # vision / OCR / scanned documents / drawings
ollama pull nomic-embed-text     # embeddings for the local knowledge base

# 3. Install SovereignAI itself
git clone <internal-repo-url> sovereignai && cd sovereignai
pip install -e . --break-system-packages
./scripts/install.sh             # pulls sandbox images, applies firewall, verifies air-gap

# 4. Launch it — from anywhere, in any terminal:
sovai
```

If `sovai doctor` reports anything missing (a model not pulled, Docker not running, firewall rules not applied), it prints the exact one-line command to fix it — run that, then `sovai doctor` again until clean.

## 16. Day-to-day usage

- **Start it**: open a terminal in the folder you want to work in (e.g. `cd /data/projects/unit-4-inspection`), then type `sovai`. The workspace/cwd shown in the status bar is that folder — every file the agent reads or writes stays scoped there unless you `/cwd` elsewhere or add another allow-listed path in config.
- **Just ask**: leave the model on `AUTO` (the default) and type naturally — "summarize this inspection report and draft an approval note", "fix the bug in reactor_control.py and run the tests", "what does SOP-114 say about valve torque limits". SovereignAI classifies the request, shows you which model it picked and why (dim line above the response), and gets to work.
- **Pin a model manually**: `ctrl+p` → `models`, or just type `/models`, and pick one from the list if you want to force, say, the coding model even for a general-sounding request.
- **Attach an image or scanned PDF**: drop the file path into your message (or use the file-attach shortcut once wired into your terminal's paste handling) — SovereignAI auto-routes to `vision` and extracts text/findings before continuing.
- **Watch it work, not just wait**: tool calls (file reads, sandbox runs, document generation) stream into the chat as their own expandable blocks in real time — this is meant to be watched, the way you'd watch Claude Code or Codex work, not a black box you wait on.
- **Check the sovereignty claim yourself, any time**: `/net` opens the live network monitor. It should read `0 external calls` from the moment you launch to the moment you quit, for every task, including coding tasks run in the sandbox.
- **Interrupt anything**: `esc` at any point stops the current step cleanly.
- **Build a knowledge base once, benefit forever**: `sovai kb add /path/to/sops-and-manuals` (or `/kb add ...` inside the app) — after that, `document_qa`-style questions are grounded in and cite your organization's actual manuals/correspondence, not the model's general training data.
- **Review generated files**: anything the agent produces (a `.docx` approval note, a `.pptx` deck, a fixed script) appears as a file card in the chat with its path — open it directly from your file manager, nothing is hidden in a temp folder you have to go hunting for.
- **New session / browse past sessions**: `/new` to start clean, `/sessions` to reopen and continue a previous one — full history is kept locally in SQLite, nothing expires unless you delete it.

## 17. The four-scenario demo script (matches the "Expected Solution" requirements exactly)

Run these in order, with `/net` open on a second pane the whole time.

1. **Model auto-selection across task types**: ask a general drafting question, then immediately a coding question, in the same session, on `AUTO`. Point at the dim routing line changing from `qwen3.5:9b` to `qwen2.5-coder:7b` between the two responses.
2. **Agentic end-to-end task**: hand it a scanned inspection report (image or PDF). Ask it to "pull out the key findings and draft an approval note as a Word file." Watch it route to `vision`, extract findings, hand off to the `general` model for drafting, call `docgen_tool`, and produce a `.docx` file card — one request, no manual steps in between.
3. **Coding task, run and verified in a sandbox**: ask it to write a small utility with a bug seeded in, then "find and fix the bug and prove the tests pass." Watch the `sandbox_exec` tool-call block show the failing run, the fix, and the passing run.
4. **Multimodal understanding**: hand it a photograph of a handwritten inspection note or a P&ID snippet and ask a specific question about it ("what's the tag number on the valve in the top-right?"). Watch it route to `vision` and answer grounded in the actual image.
5. **The sovereignty proof itself**: throughout all of the above, keep `/net` visible. At the end, run `scripts/verify_airgap.sh` live and show the PASS output — including the sandbox-container egress attempt that fails.

---

*End of specification. Build milestones M1→M6 in order; each is independently demoable; the model map in §5.3 is the only thing that needs to change to scale this from an 8GB laptop demo to a real on-prem GPU server.*