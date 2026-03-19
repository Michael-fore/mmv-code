---
name: cloud_sql_proxy
description: >
  Use this skill whenever any MMV Python tool fails with a database connection
  error (psycopg2 timeout, "could not connect to server", or similar).
  The MMV Cloud SQL instance does NOT allow direct TCP — all connections must
  go through the Cloud SQL Auth Proxy. Always start the proxy first before
  running data pipelines, backfills, or any tool that touches the PostgreSQL
  database. The correct instance connection name is mmv-cloud:us-central1:mmv-postgres
  (the project has multiple GCP projects — always use the full connection name).
---

# Cloud SQL Auth Proxy — MMV Setup

## When to Use This Skill

Any time you see errors like:
- `psycopg2.OperationalError: connection to server ... timeout expired`
- `could not connect to server: Connection refused`
- `Tool exited with code 1` from any mmv-data or mmv-underwriting tool

The Cloud SQL Auth Proxy must be running **before** any Python tool is invoked.

---

## Instance Details

| Key | Value |
|-----|-------|
| Instance connection name | `mmv-cloud:us-central1:mmv-postgres` |
| GCP Project | `mmv-cloud` |
| DB Name | `mmv` |
| DB User | `mmv-agent` |
| Credentials | `~/mmv-cloud-llm-agent-key.json` |
| Local port (via proxy) | `127.0.0.1:5432` |

> **Note:** The project has multiple GCP projects. Always use the full connection name
> `mmv-cloud:us-central1:mmv-postgres` — not just the instance name alone.

---

## Setup (One-Time)

If `cloud-sql-proxy` is not installed:

```bash
# Fix Homebrew permissions if needed
sudo chown -R tako /opt/homebrew

# Install
brew install cloud-sql-proxy
```

---

## Starting the Proxy

```bash
cloud-sql-proxy --credentials-file ~/mmv-cloud-llm-agent-key.json mmv-cloud:us-central1:mmv-postgres &
```

The `&` runs it in the background. You should see:
```
Listening on 127.0.0.1:5432...
```

---

## Verifying It's Running

```bash
pgrep -fl cloud-sql-proxy
nc -z 127.0.0.1 5432 && echo "Proxy OK"
```

---

## Stopping the Proxy

```bash
pkill -f cloud-sql-proxy
```

---

## Notes

- Authenticates using `~/mmv-cloud-llm-agent-key.json` (service account: `llm-agent@mmv-cloud.iam.gserviceaccount.com`)
- Only one proxy process needed — don't start duplicates
- Proxy does not persist across terminal sessions or reboots
- `CLOUD_SQL_INSTANCE` env var is set in `mmv-front/.env` and `tools-bridge.js`
