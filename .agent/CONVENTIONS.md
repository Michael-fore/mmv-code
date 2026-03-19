# MMV Code Conventions

> Read this before writing any new tool, fetcher, or DB query.
> These are the patterns every existing file follows — deviate and things break.

---

## Tools

### Return shape
Every tool function must return `List[dict]` — flat, JSON-serializable, no DataFrames, no custom objects.

```python
# ✅ Correct
def query_properties(county: str) -> list[dict]:
    return [{"account_number": "...", "owner_name": "...", "total_appraised_value": 1200000}]

# ❌ Wrong
def query_properties(county: str) -> pd.DataFrame: ...
def query_properties(county: str) -> dict: ...     # single dict, not a list
```

### Error shape
On failure, return a single-item list with an `error` key — never raise to the FastAPI layer.

```python
except Exception as e:
    return [{"error": str(e), "details": traceback.format_exc()}]
```

### Every tool needs a `.tool.json` manifest
No manifest = the tool is invisible to the agent. Place it in the canonical path (see ARCHITECTURE.md).

```json
{
  "name": "my_tool_name",
  "description": "One clear sentence: what does it do and what does it return?",
  "module": "pipelines.tools.my_module",
  "function": "my_function",
  "repo": "mmv-data",
  "domainLabel": "Data",
  "ontologyLayer": "market",
  "tags": ["property", "commercial"],
  "parameters": {
    "type": "object",
    "properties": {
      "county": { "type": "string", "description": "County name (lowercase, e.g. harris)" }
    },
    "required": ["county"]
  }
}
```

---

## Database

### Always use the shared connection helper

```python
# ✅ Python (mmv-data tools)
from db_connect import get_conn
conn = get_conn()

# ❌ Never open your own psycopg2.connect() — it bypasses the Cloud SQL Proxy
```

### DB_PASS is always from env — no defaults
`DB_PASS = os.environ["DB_PASS"]` — not `os.environ.get("DB_PASS", "some-password")`.

### Every table has `source` + `fetched_at` columns
```sql
source     TEXT        NOT NULL DEFAULT 'My Source Name',
fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

### Dedup strategy must match data nature
- Point-in-time snapshots → PK includes `year` or `date`
- Events (deeds, permits) → PK includes the event identifier + date
- Lookups (entities) → PK is the registry number
- Never use auto-increment IDs — use natural keys
See `data_catalog.md` for examples per table.

### Always query the data shape before writing the schema
Raw API data first → understand the shape → then write the DDL.

---

## Fetchers (mmv-data)

### GCS before PostgreSQL
All raw data lands in GCS first: `gs://mmv-raw/{source}/{YYYY-MM-DD}/{content_hash}.json`

```python
from gcs import upload_json
upload_json(data, source="usda_nass", content=data)
```

### Provenance wrapping
Wrap fetched values with source metadata for trust tracking:

```python
from provenance import wrap
return wrap(value=3220, unit="$/acre", source="USDA NASS QuickStats",
            source_url="https://...", query_params={"state": "TX"})
```

### CLI interface
Every fetcher must be runnable standalone:
```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    args = parser.parse_args()
    print(json.dumps(fetch_data(args.state), indent=2))
```

---

## Logging

```python
import logging
logger = logging.getLogger(__name__)

# ✅
logger.info("Fetched %d properties", len(rows))
logger.warning("No data returned for county=%s", county)

# ❌ Never use print() in tool functions (it pollutes FastAPI logs)
```

---

## GCS Storage naming
```
gs://mmv-raw/{source}/{YYYY-MM-DD}/{sha256_of_content}.json
```
Dedup via content hash before upload — `gcs.py` handles this.

---

## Cross-Repo Imports

**Never import Python from another repo.** Repos communicate via data (JSON/dicts).

```python
# ✅ Call via FastAPI
import requests
result = requests.post("http://localhost:8001/tools/fetch_land_values", json={"state": "TX"})

# ❌ Never
from mmv_data.tools.usda import fetch_land_values   # cross-repo import
```

---

## GCP commands

Always use:
```bash
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud <command>
```
The sandbox blocks `~/.config/gcloud`. Activate once per session:
```bash
mkdir -p /tmp/mmv_gcloud
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud auth activate-service-account \
  --key-file=~/mmv-cloud-llm-agent-key.json --project=mmv-cloud
```
