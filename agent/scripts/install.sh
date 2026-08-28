#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# SovereignAI — install.sh
# Run once on a connected machine, then copy everything to the air-gapped target.
#
# What this does (in order):
#   1. Check prerequisites (Python 3.11+, Docker, Ollama)
#   2. Create a Python venv and install all dependencies
#   3. Pull the four required Ollama models
#   4. Pull Docker sandbox images
#   5. Apply nftables egress firewall rules (Linux only, requires sudo)
#   6. Run verify_airgap.sh to confirm isolation
#   7. Print a success banner
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✅${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}   $*"; }
fail() { echo -e "  ${RED}❌${NC}  $*"; exit 1; }
info() { echo -e "  ${CYAN}→${NC}   $*"; }

echo ""
echo -e "${CYAN}███████╗ ██████╗ ██╗   ██╗ █████╗ ██╗${NC}"
echo -e "${CYAN}╚══════╝ ╚═════╝  ╚═══╝  ╚═╝  ╚═╝╚═╝${NC}"
echo ""
echo -e "${CYAN}  SovereignAI — Installation Script${NC}"
echo ""

# ── Step 1: Prerequisites ─────────────────────────────────────────────────

info "Checking prerequisites…"

python_cmd=""
for cmd in python3.11 python3.12 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    version=$("$cmd" -c "import sys; print(sys.version_info >= (3,11))" 2>/dev/null)
    if [ "$version" = "True" ]; then
      python_cmd="$cmd"
      break
    fi
  fi
done

if [ -z "$python_cmd" ]; then
  fail "Python 3.11+ not found. Install from https://python.org"
fi
ok "Python found: $($python_cmd --version)"

if ! command -v docker &>/dev/null; then
  fail "Docker not found. Install from https://docs.docker.com/get-docker/"
fi
if ! docker info &>/dev/null; then
  fail "Docker daemon is not running. Start it and retry."
fi
ok "Docker running: $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'ok')"

if ! command -v ollama &>/dev/null; then
  fail "Ollama not found. Install from https://ollama.com/download"
fi
# Try to start ollama if not running
if ! curl -sf http://127.0.0.1:11434/api/tags &>/dev/null; then
  warn "Ollama not responding. Attempting to start in background…"
  ollama serve &>/dev/null &
  sleep 3
  if ! curl -sf http://127.0.0.1:11434/api/tags &>/dev/null; then
    fail "Could not connect to Ollama. Run 'ollama serve' and retry."
  fi
fi
ok "Ollama running at http://127.0.0.1:11434"

# ── Step 2: Create venv + install deps ───────────────────────────────────

info "Creating Python virtual environment…"
VENV_DIR="$REPO_DIR/.venv"
"$python_cmd" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel --quiet
ok "Virtual environment created at $VENV_DIR"

info "Installing SovereignAI and all dependencies…"
pip install -e "$REPO_DIR" --quiet
ok "SovereignAI installed. 'sovai' command is now available."

# ── Step 3: Pull Ollama models ─────────────────────────────────────────────

echo ""
info "Pulling Ollama models (this may take 10–20 minutes, ~14GB total)…"
echo ""

pull_model() {
  local model="$1"
  local desc="$2"
  info "Pulling $model ($desc)…"
  if ollama pull "$model"; then
    ok "$model ready"
  else
    warn "$model pull failed — run 'ollama pull $model' manually later"
  fi
}

pull_model "llama3.2:3b"        "router — always-resident task classifier"
pull_model "qwen3.5:9b"         "general reasoning / drafting / summaries"
pull_model "qwen2.5-coder:7b"   "coding / debugging / sandbox"
pull_model "qwen2.5vl:7b"       "vision / OCR / scanned documents"
pull_model "nomic-embed-text"   "RAG embeddings"

# ── Step 4: Pull Docker sandbox images ────────────────────────────────────

echo ""
info "Pulling Docker sandbox images…"
docker pull python:3.11-slim && ok "python:3.11-slim ready" || warn "python:3.11-slim pull failed"
docker pull node:20-slim    && ok "node:20-slim ready"    || warn "node:20-slim pull failed"
docker pull gcc:13          && ok "gcc:13 ready"          || warn "gcc:13 pull failed"

# ── Step 5: Apply firewall rules (requires sudo, Linux only) ──────────────

echo ""
if [ "$(uname -s)" = "Linux" ]; then
  info "Applying nftables egress firewall rules…"
  info "(This blocks all outbound traffic except loopback — the sovereignty guarantee)"
  if command -v nft &>/dev/null; then
    if sudo -n true 2>/dev/null; then
      sudo nft -f - <<'NFTEOF'
table inet sovai_guard {
    chain output {
        type filter hook output priority 0; policy accept;
        oif lo accept
        ip daddr 127.0.0.1 accept
        ip6 daddr ::1 accept
        log prefix "SOVAI-BLOCKED: " flags all counter drop
    }
}
NFTEOF
      ok "nftables egress block applied."
    else
      warn "Cannot apply firewall rules without sudo. Run manually:"
      warn "  sudo nft -f scripts/nftables_sovai.conf"
    fi
  else
    warn "nft not found. Install: sudo apt install nftables"
    warn "Or use iptables: sudo iptables -A OUTPUT ! -d 127.0.0.1 -j DROP"
  fi
else
  warn "Firewall auto-setup only available on Linux."
  warn "On macOS/Windows, see HOW_TO_USE.md §Network Isolation."
fi

# ── Step 6: Verify air-gap ────────────────────────────────────────────────

echo ""
info "Running air-gap verification…"
if [ -x "$SCRIPT_DIR/verify_airgap.sh" ]; then
  bash "$SCRIPT_DIR/verify_airgap.sh" || warn "Air-gap verification reported issues (see above)."
else
  warn "verify_airgap.sh not found — run it manually after installation."
fi

# ── Step 7: Success ───────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅  SovereignAI installation complete!${NC}"
echo ""
echo -e "  Activate the environment:  ${CYAN}source $VENV_DIR/bin/activate${NC}"
echo -e "  Launch SovereignAI:        ${CYAN}sovai${NC}"
echo -e "  Check everything's OK:     ${CYAN}sovai doctor${NC}"
echo -e "  Add knowledge base docs:   ${CYAN}sovai kb add /path/to/documents${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

