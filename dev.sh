#!/usr/bin/env bash
# dev.sh — Start the full MMV dev stack
# Usage: ./dev.sh [--status | --down]
set -euo pipefail

MMV_ROOT="$(cd "$(dirname "$0")" && pwd)"
CREDS=~/mmv-cloud-llm-agent-key.json
INSTANCE="mmv-cloud:us-central1:mmv-postgres"

# ─── Helpers ─────────────────────────────────────────────────────────────────

log()  { echo -e "\033[1;34m[MMV]\033[0m $*"; }
ok()   { echo -e "\033[1;32m  ✅ $*\033[0m"; }
fail() { echo -e "\033[1;31m  ❌ $*\033[0m"; }

status() {
  echo ""
  echo "=== MMV Stack Status ==="
  nc -z 127.0.0.1 5432 2>/dev/null      && ok "DB proxy  :5432" || fail "DB proxy  :5432"
  curl -s --max-time 2 http://localhost:8001/health \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'  ✅ FastAPI   :8001 ({d[\"tools\"]} tools)')" \
    2>/dev/null                          || fail "FastAPI   :8001"
  curl -s --max-time 2 http://localhost:3000/ >/dev/null 2>&1 \
                                         && ok "Node      :3000" || fail "Node      :3000"
  echo ""
}

down() {
  log "Tearing down MMV stack..."
  pkill -f cloud-sql-proxy 2>/dev/null || true
  cd "$MMV_ROOT" && docker compose down 2>/dev/null || true
  pkill -f "node server.js"  2>/dev/null || true
  lsof -ti :3000 | xargs kill 2>/dev/null || true
  ok "Stack stopped."
}

# ─── Flags ───────────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--status" ]]; then status; exit 0; fi
if [[ "${1:-}" == "--down"   ]]; then down;   exit 0; fi

# ─── Step 1: Cloud SQL Auth Proxy ────────────────────────────────────────────

log "Step 1/3 — Cloud SQL Auth Proxy..."
pkill -f cloud-sql-proxy 2>/dev/null || true
cloud-sql-proxy --credentials-file "$CREDS" "$INSTANCE" &
sleep 3
if nc -z 127.0.0.1 5432 2>/dev/null; then
  ok "DB proxy up on :5432"
else
  fail "DB proxy failed — run: brew install cloud-sql-proxy"
  exit 1
fi

# ─── Step 2: FastAPI Tool Service (Docker) ───────────────────────────────────

log "Step 2/3 — FastAPI tool service (Docker)..."
cd "$MMV_ROOT"
docker compose up tools -d
sleep 8
TOOLS=$(curl -s --max-time 5 http://localhost:8001/health \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['tools'])" 2>/dev/null || echo "?")
ok "FastAPI up on :8001 ($TOOLS tools loaded)"

# ─── Step 3: Node.js Frontend ────────────────────────────────────────────────

log "Step 3/3 — Node.js frontend..."
lsof -ti :3000 | xargs kill 2>/dev/null || true
sleep 1

cd "$MMV_ROOT/mmv-front"
NODE_PATH=/tmp/mmv-deps/node_modules node server.js &
sleep 3

if curl -s --max-time 3 http://localhost:3000/ >/dev/null 2>&1; then
  ok "Frontend up on :3000"
else
  fail "Frontend may still be starting — check with: ./dev.sh --status"
fi

# ─── Done ────────────────────────────────────────────────────────────────────

echo ""
status
log "Dev stack is up. To stop: ./dev.sh --down"
