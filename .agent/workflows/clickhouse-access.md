---
description: How to connect to ClickHouse and run gcloud commands from the sandbox
---

# GCP + ClickHouse Access

## gcloud from sandbox

The Antigravity sandbox blocks `~/.config/gcloud/`. Use `/tmp/` for the config dir:

```bash
# Always prefix gcloud commands with this:
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud <command>

# First-time auth (once per session):
mkdir -p /tmp/mmv_gcloud
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud auth activate-service-account \
  --key-file=/Users/tako/mmv-cloud-llm-agent-key.json --project=mmv-cloud
```

## ClickHouse connection details

- **Host:** `35.188.174.185`
- **Port:** `8123` (HTTP)
- **User:** `default`
- **Password:** stored in env var `CLICKHOUSE_PASSWORD`
- **GCE VM:** `clickhouse-1` in `us-central1-a`
- **Version:** 26.2

## ClickHouse HTTP API rules

- **GET** = read-only (SELECT). Mutations will fail with `READONLY` error.
- **POST** = required for all write operations (CREATE, INSERT, ALTER, DROP).
- Password has special chars — always URL-encode with `urllib.parse.urlencode()`.

```python
# Correct pattern:
import urllib.request, urllib.parse

def ch_query(sql):
    url = 'http://35.188.174.185:8123/'
    params = urllib.parse.urlencode({
        'user': 'default',
        'password': os.environ.get('CLICKHOUSE_PASSWORD', ''),
    })
    # POST body = the SQL query
    req = urllib.request.Request(f'{url}?{params}', data=sql.encode('utf-8'))
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8').strip()
```

## Firewall

- Rule `allow-clickhouse` restricts ports 8123/9000 to current IPv4 only.
- Use `curl -4` to get IPv4 (not IPv6) — GCP firewall doesn't support IPv6 CIDR.
- IAP enabled for future migration to zero-public-port setup.
