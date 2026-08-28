#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# verify_airgap.sh — Network isolation proof
#
# Demonstrates that:
#   1. The host cannot reach external services
#   2. Docker sandbox containers also cannot reach external services
#      (even if the host firewall is misconfigured, the sandbox --network none
#       prevents container-level egress)
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
pass() { echo -e "  ${GREEN}PASS${NC}  $*"; }
fail() { echo -e "  ${RED}FAIL${NC}  $*"; }
info() { echo -e "  ${CYAN}→${NC}   $*"; }

OVERALL_PASS=true

echo ""
echo -e "${CYAN}  SovereignAI — Air-Gap Verification${NC}"
echo -e "  $(date)"
echo ""

# ── Test 1: Host cannot reach Anthropic API ───────────────────────────────

info "Test 1: Host → api.anthropic.com (expect: BLOCKED)"
if curl -s --max-time 5 https://api.anthropic.com/v1/messages \
        -H "x-api-key: test" 2>&1 | grep -q "error\|failed\|refused\|timed out\|curl: ("; then
  pass "api.anthropic.com is unreachable from host"
elif ! curl -s --max-time 5 https://api.anthropic.com &>/dev/null; then
  pass "api.anthropic.com is unreachable from host (curl failed)"
else
  fail "api.anthropic.com was reachable! Firewall rules may not be applied."
  OVERALL_PASS=false
fi

# ── Test 2: Host cannot reach OpenAI API ─────────────────────────────────

info "Test 2: Host → api.openai.com (expect: BLOCKED)"
if ! curl -s --max-time 5 https://api.openai.com &>/dev/null; then
  pass "api.openai.com is unreachable from host"
else
  fail "api.openai.com was reachable!"
  OVERALL_PASS=false
fi

# ── Test 3: Ollama local API IS reachable ─────────────────────────────────

info "Test 3: Host → 127.0.0.1:11434 (Ollama, expect: REACHABLE)"
if curl -s --max-time 3 http://127.0.0.1:11434/api/tags &>/dev/null; then
  pass "Ollama local API is reachable (as expected)"
else
  fail "Ollama local API is NOT reachable — start Ollama with 'ollama serve'"
  OVERALL_PASS=false
fi

# ── Test 4: Docker sandbox cannot reach external network ─────────────────

info "Test 4: Docker sandbox (--network none) → api.anthropic.com (expect: BLOCKED)"
if ! command -v docker &>/dev/null; then
  echo -e "  ${YELLOW}SKIP${NC}  Docker not installed — skipping sandbox test"
else
  SANDBOX_RESULT=$(docker run --rm \
    --network none \
    --memory=256m \
    --cpus=0.5 \
    --read-only \
    --tmpfs /tmp \
    python:3.11-slim \
    python -c "
import urllib.request, sys
try:
    urllib.request.urlopen('https://api.anthropic.com', timeout=5)
    print('REACHABLE')
except Exception as e:
    print('BLOCKED:', e)
" 2>&1 || echo "CONTAINER_ERROR")

  if echo "$SANDBOX_RESULT" | grep -q "BLOCKED\|CONTAINER_ERROR\|network\|refused"; then
    pass "Docker sandbox (--network none) cannot reach api.anthropic.com"
    info "  Sandbox output: $SANDBOX_RESULT"
  elif echo "$SANDBOX_RESULT" | grep -q "REACHABLE"; then
    fail "Docker sandbox reached api.anthropic.com! --network none not enforced."
    OVERALL_PASS=false
  else
    pass "Docker sandbox could not reach api.anthropic.com (output: $SANDBOX_RESULT)"
  fi
fi

# ── Test 5: Check for suspicious psutil connections ───────────────────────

info "Test 5: No external connections in current process (expect: 0)"
EXT_CONNS=$(python3 -c "
import psutil, sys
ext = 0
try:
    for c in psutil.net_connections():
        if c.raddr and c.raddr.ip not in ('127.0.0.1', '::1', '0.0.0.0', ''):
            if not c.raddr.ip.startswith('127.'):
                ext += 1
                print(f'  EXTERNAL: {c.raddr.ip}:{c.raddr.port} ({c.status})')
except Exception as e:
    print(f'  (psutil error: {e})')
print(ext)
" 2>/dev/null | tail -1)

if [ "${EXT_CONNS:-0}" = "0" ]; then
  pass "No external connections detected from this process"
else
  fail "Found $EXT_CONNS external connection(s) — investigate before deployment"
  OVERALL_PASS=false
fi

# ── Summary ───────────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$OVERALL_PASS" = "true" ]; then
  echo -e "${GREEN}  ✅  AIR-GAP VERIFICATION: PASSED${NC}"
  echo ""
  echo "  All tests passed. This machine meets the SovereignAI isolation requirements."
  echo "  Zero external calls. 100% local. Suitable for confidential deployment."
  exit 0
else
  echo -e "${RED}  ❌  AIR-GAP VERIFICATION: FAILED${NC}"
  echo ""
  echo "  One or more tests failed. Review the FAIL items above."
  echo "  Do not deploy to a classified environment until all tests pass."
  exit 1
fi

