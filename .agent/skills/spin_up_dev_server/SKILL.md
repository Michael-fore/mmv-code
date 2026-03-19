---
name: spin_up_dev_server
description: >
  Use this skill whenever you need to start the MMV local development server.
  The stack has three components that must all be running: the Cloud SQL Auth
  Proxy (database access), the FastAPI tool service (via Docker), and the
  Node.js frontend. Run them in order — each depends on the previous.
---

# MMV Dev Server — Spin Up

> **TL;DR — one command from the MMV root:**
> ```bash
> ./dev.sh          # start everything
> ./dev.sh --status # check what's running
> ./dev.sh --down   # tear everything down
> ```
> Manual steps are documented below for reference / troubleshooting.

## Components (start in order)

| # | Component | Port | How |
|---|-----------|------|-----|
| 1 | Cloud SQL Auth Proxy | 5432 | `cloud-sql-proxy` binary |
| 2 | FastAPI tool service | 8001 | `docker compose up tools -d` |
| 3 | Node.js frontend | 3000 | `node server.js` |

---

## Step 1 — Cloud SQL Auth Proxy

```bash
pkill -f cloud-sql-proxy 2>/dev/null
cloud-sql-proxy \
  --credentials-file ~/mmv-cloud-llm-agent-key.json \
  mmv-cloud:us-central1:mmv-postgres &
sleep 2
nc -z 127.0.0.1 5432 && echo "✅ DB proxy up" || echo "❌ Proxy failed"
```

**If `cloud-sql-proxy` not found:**
```bash
brew install cloud-sql-proxy
```

**Verify:** `nc -z 127.0.0.1 5432` should succeed.

---

## Step 2 — FastAPI Tool Service (Docker)

```bash
cd /Users/tako/projects/ai-playground/MMV
docker compose up tools -d
sleep 8
curl -s http://localhost:8001/health | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'✅ {d[\"tools\"]} tools ready')"
```

**Expected output:** `✅ 41 tools ready`

**If image not built yet:**
```bash
DOCKER_BUILDKIT=0 docker build -t mmv-tool-service ./tools/
```

**Check logs if something is wrong:**
```bash
docker compose logs tools --tail 40
```

---

## Step 3 — Node.js Frontend

```bash
cd /Users/tako/projects/ai-playground/MMV/mmv-front
NODE_PATH=/tmp/mmv-node-modules/node_modules node server.js
```

**Expected output:** Banner showing `Tools loaded: 48+` and `http://localhost:3000`

---

## Quick Status Check

Run this anytime to see what's up:

```bash
echo "=== MMV Stack Status ==="
nc -z 127.0.0.1 5432 2>/dev/null && echo "✅ DB proxy  :5432" || echo "❌ DB proxy  :5432"
curl -s --max-time 2 http://localhost:8001/health \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'✅ FastAPI   :8001 ({d[\"tools\"]} tools)')" \
  2>/dev/null || echo "❌ FastAPI   :8001"
curl -s --max-time 2 http://localhost:3000/ > /dev/null 2>&1 \
  && echo "✅ Node      :3000" || echo "❌ Node      :3000"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `tools/Dockerfile` | FastAPI service image |
| `docker-compose.yml` | Docker compose config (MMV root) |
| `tools/main.py` | Tool discovery + FastAPI app |
| `mmv-front/.agent/workflows/start_local.md` | Same steps as a runnable workflow |
| `.agent/skills/cloud_sql_proxy/SKILL.md` | DB proxy troubleshooting detail |

---

## Tear Down

```bash
docker compose down          # stop tool service
pkill -f cloud-sql-proxy     # stop DB proxy
pkill -f "node server.js"    # stop Node
```
