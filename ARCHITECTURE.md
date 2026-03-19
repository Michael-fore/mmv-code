# MMV Architecture — Operational Reference

> This document describes how the system **actually runs today**, not the aspirational roadmap.
> For roadmap and status, see [`implementation_plan.md`](./implementation_plan.md).

---

## System Overview

MMV is a land and commercial real estate intelligence platform. An analyst types a question in a chat UI; the system routes it through an LLM, discovers and calls Python tools, queries a PostgreSQL database, and returns a structured answer.

```
Browser
  └── mmv-front (Express, :3000)
        ├── POST /api/chat      → Gemini API (gemini-2.5-pro)
        │     └── Function Calls → POST /api/tools/:name
        │                              └── tools-bridge.js
        │                                    └── POST http://localhost:8001/tools/:name
        │                                          └── FastAPI tool service (:8001, Docker)
        │                                                └── Python tool functions
        │                                                      └── PostgreSQL (:5432, via Cloud SQL Proxy)
        └── GET /api/tools      → manifest-loader.js → GET http://localhost:8001/tools
```

---

## Services (Local Dev)

| Service | Port | How to start | Source |
|---------|------|-------------|--------|
| Cloud SQL Auth Proxy | 5432 | `cloud-sql-proxy --credentials-file ~/mmv-cloud-llm-agent-key.json mmv-cloud:us-central1:mmv-postgres &` | Binary |
| FastAPI tool service | 8001 | `docker compose up tools -d` | `tools/` → `tools/main.py` |
| Node.js frontend | 3000 | `NODE_PATH=/tmp/mmv-node-modules/node_modules node server.js` | `mmv-front/server.js` |

**Start order**: Proxy → FastAPI → Node. Each depends on the previous.
Full startup steps: see `.agent/skills/spin_up_dev_server/SKILL.md`.

**Quick status check:**
```bash
nc -z 127.0.0.1 5432 && echo "✅ DB proxy" || echo "❌ DB proxy"
curl -s http://localhost:8001/health | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'✅ FastAPI ({d[\"tools\"]} tools)')"
curl -s http://localhost:3000/ > /dev/null && echo "✅ Node" || echo "❌ Node"
```

---

## Data Flow

### Add a new data source
```
External API → fetcher script (mmv-data/pipelines/) → GCS (gs://mmv-raw/...) → PostgreSQL (mmv-data/migrate.py)
```

### Answer a chat question
```
User message → mmv-front/server.js → Gemini (with tool declarations)
  → Gemini emits function call → mmv-front/tools-bridge.js
  → POST http://localhost:8001/tools/{name} → FastAPI (tools/main.py)
  → Python tool function → psycopg2 → PostgreSQL
  → JSON result → Gemini continues → final answer to user
```

### Tool discovery at startup
```
mmv-front/manifest-loader.js calls GET http://localhost:8001/tools
  → FastAPI scans *.tool.json in pipelines/tools/manifests/ (per repo)
  → Returns full manifests used to build Gemini function declarations
  → Fallback: disk scan → hardcoded FALLBACK_TOOLS (last resort)
```

---

## Repo Map

All repos are submodules under the monorepo root (`/Users/tako/projects/ai-playground/MMV`).

| Repo | Owns | Key dirs |
|------|------|---------|
| `mmv-data` | Data fetching, GCS upload, PostgreSQL loading, migrations | `pipelines/tools/`, `pipelines/tools/manifests/`, `migrations/` |
| `mmv-tools/underwriting` | Analysis: cap rates, risk scoring, underwriting | `underwriting/tools/` |
| `mmv-tools/reporting` | Report generation, Excel export | `reporting/tools/` |
| `mmv-agent` | Daily pipeline, LLM analyst, task orchestration | `pipelines/`, `tasks/` |
| `mmv-front` | Chat UI, Express server, tool bridge | `server.js`, `tools-bridge.js`, `manifest-loader.js` |
| `mmv-infra` | GCP deployments, Cloud SQL, GCS, Cloud Scheduler | `sql/`, `deploy/` |
| `tools/` (root) | FastAPI tool service (shared, mounts all repos) | `main.py`, `db.py` |

**Cross-repo rule**: Repos communicate via data (JSON), never via Python imports across boundaries.

**Change order** when a task spans repos:
`mmv-data → mmv-tools/underwriting → mmv-tools/reporting → mmv-infra → mmv-agent → mmv-front`

---

## Infrastructure (GCP)

| Resource | Value |
|----------|-------|
| GCP Project | `mmv-cloud` |
| Cloud SQL Instance | `mmv-cloud:us-central1:mmv-postgres` |
| Database | `mmv` |
| DB User | `mmv-agent` |
| DB Password | see `.env` → `DB_PASS` (also in Secret Manager: `mmv-db-pass`) |
| GCS Bucket | `gs://mmv-raw/` |
| Service Account | `llm-agent@mmv-cloud.iam.gserviceaccount.com` |
| Credentials (local) | `~/mmv-cloud-llm-agent-key.json` |
| Cloud Run Job | `mmv-backfill` (us-central1) |

**GCP auth for gcloud commands**: `CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud ...`
(sandbox blocks `~/.config/gcloud` — always use `/tmp/mmv_gcloud`)

---

## Tool Manifest Locations (Canonical)

> **Only create `.tool.json` files at these paths:**

| Repo | Canonical manifest path |
|------|------------------------|
| `mmv-data` | `mmv-data/pipelines/tools/manifests/` |
| `mmv-tools/underwriting` | `mmv-tools/underwriting/tools/` |
| `mmv-tools/reporting` | `mmv-tools/reporting/tools/` |
| `mmv-agent` | `mmv-agent/pipelines/` |

FastAPI discovers all manifests at startup. After adding one: `docker compose restart tools`.

---

## Key Files

| File | Purpose |
|------|---------|
| `tools/main.py` | FastAPI app — tool discovery, dispatch |
| `tools/db.py` | Shared psycopg2 connection pool |
| `mmv-front/server.js` | Express server, Gemini chat endpoint |
| `mmv-front/tools-bridge.js` | Proxies Gemini function calls → FastAPI |
| `mmv-front/manifest-loader.js` | Discovers tools and builds Gemini declarations |
| `mmv-data/pipelines/tools/db/db_connect.py` | Python DB connection helper (all tools use this) |
| `mmv-data/data_catalog.md` | **Canonical DB schema reference** — read before writing any SQL |
| `docker-compose.yml` | Starts FastAPI tool service |
| `.env` | Local env vars (DB_PASS, API keys — gitignored) |

---

## Skills & Workflows

Agent context files live in `.agent/`:

```
.agent/
├── workflows/         ← Slash-command workflows (/db-connect, /sync-tools, etc.)
└── skills/            ← Self-contained how-tos with runnable scripts
    ├── cloud_sql_proxy/
    ├── data-inventory/
    ├── doc-coherence/
    ├── query-data/
    ├── spin_up_dev_server/
    └── system-map/
```

Run `/doc-coherence` after any significant change to catch documentation drift.
