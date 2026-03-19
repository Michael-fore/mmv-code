# MMV — LLM Agent Onboarding

This codebase is designed for LLM-assisted development. Start here.

---

## Cold Start (read these 3 files first)

| Order | File | What you'll learn |
|-------|------|-------------------|
| 1 | [`ARCHITECTURE.md`](./ARCHITECTURE.md) | How the system runs today — services, ports, data flow, repo map, GCP infra |
| 2 | [`.agent/CONVENTIONS.md`](./.agent/CONVENTIONS.md) | Code contracts — tool return shape, DB patterns, manifest rules, logging |
| 3 | [`.agent/GLOSSARY.md`](./.agent/GLOSSARY.md) | Domain terms — SPTB codes, HCAD, SFHA, cap rates, deed types, etc. |

After those three, you have everything you need to implement most tasks correctly on the first try.

---

## Key Rules

1. **New `.tool.json` manifests** → `mmv-data/pipelines/tools/manifests/` only (see `ARCHITECTURE.md`)
2. **New code** → check `domain-structure.md` first to pick the right repo
3. **DB access** → always via `get_conn()` from `db_connect.py`, never raw `psycopg2.connect()`
4. **Secrets** → never hardcode passwords or API keys; use `os.environ["VAR"]` (required, no default)
5. **After major changes** → run `/doc-coherence` to check for documentation drift

---

## Workflows & Skills

All agent context lives in `.agent/`:

```
.agent/
├── CONVENTIONS.md        ← code contracts
├── GLOSSARY.md           ← domain vocabulary
├── workflows/            ← slash-command how-tos (/db-connect, /sync-tools, /gcp-auth, etc.)
└── skills/               ← self-contained runnable skill docs
    ├── cloud_sql_proxy/  ← DB connection troubleshooting
    ├── spin_up_dev_server/ ← start all 3 local services
    ├── data-inventory/   ← list available datasets
    ├── query-data/       ← query USDA/FRED/EIA data
    ├── doc-coherence/    ← audit docs vs. code
    └── system-map/       ← visualize module dependencies
```

Before starting any task, run: `.agent/workflows/implementation-plan.md`

---

## Where Things Live

| If you need to... | Go to |
|-------------------|-------|
| Fetch data from an API | `mmv-data/pipelines/` |
| Write a new query tool | `mmv-data/pipelines/tools/` + manifest in `pipelines/tools/manifests/` |
| Underwrite a deal | `mmv-tools/underwriting/` |
| Change the UI or chat | `mmv-front/` |
| Deploy to GCP | `mmv-data/deploy/` or `mmv-infra/` |
| Connect to the DB locally | `.agent/workflows/db-connect.md` |
| Run gcloud commands | `CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud ...` |

---

## Data Schema

Before writing any SQL, read [`mmv-data/data_catalog.md`](./mmv-data/data_catalog.md) — it is the canonical reference for all tables, columns, join keys, and query patterns.
