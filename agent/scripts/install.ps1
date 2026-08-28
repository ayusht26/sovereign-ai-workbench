# ─────────────────────────────────────────────────────────────────────────────
# SovereignAI — install.ps1 (Windows PowerShell)
# Run as Administrator in PowerShell 5.1+ or PowerShell 7+
#
# What this does:
#   1. Check prerequisites (Python 3.11+, Docker Desktop, Ollama)
#   2. Create a venv and install SovereignAI
#   3. Pull Ollama models and Docker sandbox images
#   4. Configure Windows Defender Firewall outbound rule
#   5. Print success instructions
# ─────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoDir   = Split-Path -Parent $ScriptDir

Write-Host ""
Write-Host "  SovereignAI — Windows Installation Script" -ForegroundColor Cyan
Write-Host ""

function Ok($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red; exit 1 }
function Info($msg) { Write-Host "  -->   $msg" -ForegroundColor Cyan }

# ── Step 1: Prerequisites ──────────────────────────────────────────────────

Info "Checking prerequisites…"

# Python 3.11+
$PythonCmd = $null
foreach ($cmd in @("python3.11", "python3.12", "python3", "python")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        $ver = & $cmd -c "import sys; print(sys.version_info >= (3,11))" 2>$null
        if ($ver -eq "True") {
            $PythonCmd = $cmd
            break
        }
    }
}
if (-not $PythonCmd) {
    Fail "Python 3.11+ not found. Install from https://python.org"
}
Ok "Python found: $(& $PythonCmd --version)"

# Docker
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Fail "Docker not found. Install Docker Desktop from https://www.docker.com/products/docker-desktop"
}
try {
    docker info 2>&1 | Out-Null
    Ok "Docker Desktop is running"
} catch {
    Fail "Docker daemon not running. Start Docker Desktop and retry."
}

# Ollama
if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
    Fail "Ollama not found. Install from https://ollama.com/download"
}
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
    Ok "Ollama running at http://127.0.0.1:11434"
} catch {
    Warn "Ollama not responding. Starting ollama serve in background…"
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

# ── Step 2: Create venv + install ─────────────────────────────────────────

Info "Creating Python virtual environment…"
$VenvDir = Join-Path $RepoDir ".venv"
& $PythonCmd -m venv $VenvDir
$Activate = Join-Path $VenvDir "Scripts\Activate.ps1"
. $Activate
pip install --upgrade pip wheel --quiet
Ok "Virtual environment created at $VenvDir"

Info "Installing SovereignAI…"
pip install -e $RepoDir --quiet
Ok "SovereignAI installed. 'sovai' is now available in this venv."

# ── Step 3: Pull Ollama models ──────────────────────────────────────────────

Write-Host ""
Info "Pulling Ollama models (~14GB total, may take 15–30 minutes)…"
Write-Host ""

$Models = @(
    @{Tag="llama3.2:3b";       Desc="router — task classifier"},
    @{Tag="qwen3.5:9b";        Desc="general reasoning / drafting"},
    @{Tag="qwen2.5-coder:7b";  Desc="coding / debugging"},
    @{Tag="qwen2.5vl:7b";      Desc="vision / OCR"},
    @{Tag="nomic-embed-text";  Desc="RAG embeddings"}
)

foreach ($m in $Models) {
    Info "Pulling $($m.Tag) ($($m.Desc))…"
    ollama pull $m.Tag
    Ok "$($m.Tag) ready"
}

# ── Step 4: Pull Docker sandbox images ────────────────────────────────────

Write-Host ""
Info "Pulling Docker sandbox images…"
docker pull python:3.11-slim; Ok "python:3.11-slim ready"
docker pull node:20-slim;     Ok "node:20-slim ready"
docker pull gcc:13;           Ok "gcc:13 ready"

# ── Step 5: Windows Firewall outbound rule ─────────────────────────────────

Write-Host ""
Info "Configuring Windows Defender Firewall outbound block rule…"
Info "(Requires Administrator — blocks all outbound except loopback)"

try {
    # Remove old rule if exists
    Remove-NetFirewallRule -DisplayName "SovereignAI-Egress-Block" -ErrorAction SilentlyContinue

    # Block all outbound from the sovai process
    New-NetFirewallRule `
        -DisplayName "SovereignAI-Egress-Block" `
        -Direction Outbound `
        -Action Block `
        -Program (Join-Path $VenvDir "Scripts\sovai.exe") `
        -Profile Any `
        -Enabled True | Out-Null
    Ok "Windows Firewall outbound block rule created for sovai.exe"
    Warn "Note: This blocks the sovai.exe process. Ollama (localhost) is on loopback and still works."
} catch {
    Warn "Could not create firewall rule (may need to run as Administrator):"
    Warn "  $_"
    Warn "To apply manually, run PowerShell as Administrator and re-run this script."
}

# ── Step 6: Success ───────────────────────────────────────────────────────

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  ✅  SovereignAI installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  To use SovereignAI:" -ForegroundColor Cyan
Write-Host "    1. Activate the venv:  .\.venv\Scripts\Activate.ps1"
Write-Host "    2. Launch the TUI:     sovai"
Write-Host "    3. Check everything:   sovai doctor"
Write-Host "    4. Add documents:      sovai kb add C:\path\to\documents"
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""

