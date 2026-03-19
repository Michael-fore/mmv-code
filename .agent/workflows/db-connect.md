---
description: How to connect to PostgreSQL — MUST run Cloud SQL Auth Proxy before any DB operations
---

# Database Connection

> [!IMPORTANT]
> **The Cloud SQL Auth Proxy MUST be running before any tool or script can reach the database.**
> The DB (`mmv-postgres`) is NOT accessible via direct TCP from arbitrary IPs.
> IAM auth via the proxy is the only supported connection method.

## Step 1 — Start the Auth Proxy (keep this terminal open)

// turbo
```bash
GOOGLE_APPLICATION_CREDENTIALS=/Users/tako/mmv-cloud-llm-agent-key.json \
  cloud-sql-proxy mmv-cloud:us-central1:mmv-postgres --port 5432
```

Once you see `Listening on 127.0.0.1:5432`, the tunnel is active.

## Step 2 — All tools connect to localhost

With the proxy running, all Python tools connect to `127.0.0.1:5432` automatically.
`db_connect.py` handles this — no additional config needed.

## If cloud-sql-proxy is not installed

```bash
# One-time install (Mac)
curl -o /usr/local/bin/cloud-sql-proxy \
  https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.15.2/cloud-sql-proxy.darwin.amd64 \
  && chmod +x /usr/local/bin/cloud-sql-proxy
```

## Connection details

| Setting | Value |
|---------|-------|
| Instance | `mmv-cloud:us-central1:mmv-postgres` |
| DB name | `mmv` |
| User | `mmv-agent` |
| Password | see `.env` → `DB_PASS` |
| Host (via proxy) | `127.0.0.1` |
| Port | `5432` |

## For production (Cloud Run)

Cloud Run connects via Unix socket automatically — no proxy needed.
Add `--add-cloudsql-instances mmv-cloud:us-central1:mmv-postgres` to your `gcloud run deploy` command,
and set `DB_HOST=/cloudsql/mmv-cloud:us-central1:mmv-postgres` in the service env vars.
