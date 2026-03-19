---
description: How to onboard a new data source into the MMV signal pipeline
---

# Adding a New Data Source

Follow these steps whenever wiring in a new data table, external API, or client data feed.

## 1. Fetch and inspect raw data first

Always fetch a sample before writing any code.

```bash
# Save a sample to /tmp/ — do NOT commit raw data
python -c "import json; ..." > /tmp/sample_<source>.json
head -n 5 /tmp/sample_<source>.json | python -m json.tool
```

Understand the shape: field names, value formats, cardinality, PK strategy.

## 2. Create the DB table (if new)

Write a migration in `mmv-data/migrations/NNNN_<name>.sql`:
- Follow existing migrations as templates
- Always include `fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Define a realistic `UNIQUE` constraint for the upsert PK
- Canonical field names only (see step 4)

Run the migration:
```bash
# Requires Cloud SQL Auth Proxy running — see /db-connect workflow
psql $PG_URL -f mmv-data/migrations/NNNN_<name>.sql
```

## 3. Write the ingest script

Create `mmv-data/pipelines/tools/data_sources/<source>.py` (for external APIs)
or `mmv-data/pipelines/tools/property/<source>.py` (for property-specific data).

Rules:
- Fetch raw → GCS first, then DB (see architecture-rules)
- Map all source-specific field names to canonical names before writing
- Import from `canonical_vocab.py` for all value normalization (do NOT hardcode mappings inline)
- Call `log_unknown_term(source, field, value)` for any value not in the vocab

## 4. Run alias discovery

After fetching a sample, run the vocab resolution job to propose canonical mappings for any new terms:

```bash
# From mmv-tools/underwriting/tools/
python vocab_resolution_job.py --source <source_name> --sample /tmp/sample_<source>.json
```

This uses an LLM to propose additions to `canonical_vocab.py`. Review the output:
- High-confidence proposals are auto-staged as a diff
- Ambiguous ones are printed for manual review

Commit accepted additions to `signals/canonical_vocab.py`.

## 5. Write the Signal Provider

Create `mmv-tools/underwriting/tools/signals/<source>.py`:

```python
from .base import SignalProvider
from .canonical_vocab import normalize_property_type

class MySourceSignal(SignalProvider):
    name = "my_source"
    weight = 0.10  # contribution to composite score

    def fetch(self, conn, account_numbers, county):
        # Batch query by account_number — never N+1
        ...
        return {acct: {...signal_data...}}

    def score(self, signal_data):
        # Return dict of named sub-scores (0-100)
        return {"my_source_score": ...}

    def filter_match(self, signal_data, criteria):
        # Return False to hard-exclude a parcel
        return True
```

Register it in `signals/__init__.py`:
```python
from .my_source import MySourceSignal
REGISTRY.register(MySourceSignal())
```

## 6. Add filter params (if exposing to UI)

If the new signal should power a scan filter:

1. Add the parameter to `scan_prospects.tool.json`
2. Add the filter input to `mmv-front/public/index.html` (Prospect Scanner sidebar)
3. Wire it in `mmv-front/public/prospect-scanner.js` → `filters` object in `runScan()`

## 7. Test

```bash
# Unit test the signal provider in isolation:
python -m signals.<source>  # each module has a __main__ dry-run block

# Integration test the full scanner with the new signal:
python -m prospect_scoring --county harris --limit 10
# Verify new signal sub-score appears in output
```

## 8. Restart the tool service

```bash
# See /sync-tools or /restart-server workflows
```

---

## Batch Job Schedule (vocab_resolution_job.py)

| Trigger | When |
|---|---|
| **On new source registration** | Run immediately after step 4 above |
| **Nightly** | Cloud Scheduler → Cloud Run Job, runs at 02:00 CT |
| **On-demand** | `python vocab_resolution_job.py --all` |

Unknown terms sit in the `unmapped_terms` table. Anything unmapped for >7 days triggers a Slack alert.
