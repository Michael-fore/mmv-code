# MMV Platform — Implementation Plan

## Goal

Build an AI-driven farmland investment analysis platform across five domain-separated repos. The platform must:

- Fetch real data from free public sources **with full source provenance**
- Produce deterministic analysis (underwriting, risk scoring, exit optionality)
- Use an **LLM reasoning layer** to generate contextual, cited analysis where FACT/INFERENCE is separated and confidence is scored
- Output **trust-aware reports** where every claim is traceable
- Be config-driven (Texas default, swap to any state)
- Run autonomously via an agent system

---

## Architecture

```
┌─ mmv-data ──────────────────────────────────────────────┐
│  Fetchers → Flat dicts/lists with provenance metadata   │
│  USDA NASS (bulk TSV) · FRED (CSV) · EIA (API v2)      │
│  Storage → GCS raw, then Cloud SQL PostgreSQL           │
└────────────────────────┬────────────────────────────────┘
                         │ data (dicts, not imports)
                         ▼
┌─ mmv-underwriting ─────────────────────────────────────-┐
│  Analysis primitives → chained via underwrite_deal()    │
│  Land values · Cap rate · Risk scoring · Crop econ ·    │
│  Exit optionality · Full underwriting                   │
└────────────────────────┬────────────────────────────────┘
                         │ analysis results
                         ▼
┌─ mmv-reporting ────────────────────────────────────────-┐
│  Trust-aware markdown · Excel export · Notifications    │
│  Source footnotes · Confidence badges · Data freshness  │
└────────────────────────┬────────────────────────────────┘
                         │ reports
                         ▼
┌─ mmv-agent ────────────────────────────────────────────-┐
│  LLM routing · Tool discovery · Task execution          │
│  Orchestrates: fetch → analyze → report → notify        │
└─────────────────────────────────────────────────────────┘

mmv-infra: GCP deployments, Cloud SQL, GCS, Cloud Scheduler
```

### Cross-Repo Rules

- **Data is the interface** — repos communicate via data (dicts/JSON), never import code from each other
- **Change order**: mmv-data → mmv-underwriting → mmv-reporting → mmv-infra → mmv-agent
- Domain enforcement per `.agent/workflows/domain-structure.md`

---

## Current Status

### ✅ Complete

#### mmv-data/tools/
| File | What it does |
|------|-------------|
| `usda.py` | Bulk TSV download from NASS datasets — land values, cash rents, crop production |
| `fred.py` | CSV endpoint — fed funds, CPI, USD index, farm debt, 10Y treasury |
| `eia.py` | API v2 — solar generation by state, all fuel types by state |

#### mmv-underwriting/tools/
| File | What it does |
|------|-------------|
| `land_values.py` | CAGR, real returns, volatility, YoY trends |
| `cap_rate.py` | Implied cap rate series, CRE benchmark comparison |
| `risk_scoring.py` | 1980s crisis analog — 6 weighted factors, composite 0-100 |
| `crop_economics.py` | Crop stability (CV), HHI diversification, rent trends |
| `exit_analysis.py` | Solar lease premium, development potential, composite score |
| `underwrite.py` | Chains all primitives → full underwriting package with data gaps |

#### mmv-infra/clickhouse/
| File | What it does |
|------|-------------|
| `deploy.sh` | ClickHouse on GCE provisioning |
| `connect.py` | Python client smoke test |
| `teardown.sh` | Instance cleanup |

---

### 🔲 Next: Provenance Layer (mmv-data)

Wrap every fetcher's output with source metadata:

```python
{
    "value": 3220,
    "unit": "$/acre",
    "provenance": {
        "source": "USDA NASS QuickStats",
        "source_url": "https://www.nass.usda.gov/datasets/...",
        "query_params": {"state": "TX", "year": "2025"},
        "fetched_at": "2026-03-14T00:01:39Z",
        "freshness": "current",
        "is_mock": false
    }
}
```

Changes: add `provenance.py` to `mmv-data/tools/`, retrofit `tag_provenance()` into `usda.py`, `fred.py`, `eia.py`.

---

### 🔲 Next: Report Generation (mmv-reporting)

Minimum viable: markdown report rendering `underwrite_deal()` output.

- Source footnotes per data point
- FACT/INFERENCE labels on every claim
- Confidence badges (🟢 HIGH / 🟡 MEDIUM / 🔴 LOW)
- Data freshness per section
- Data Gaps & Caveats section
- Reproducibility footer

File: `mmv-reporting/tools/markdown_report.py`

---

### 🔲 Next: Persistence Layer (mmv-data + mmv-infra)

1. GCS upload with content-hash dedup → `mmv-data/tools/gcs.py`
2. Cloud SQL PostgreSQL table definitions (one flat table per source)
3. Load pipeline: fetch → GCS raw → PostgreSQL

---

### 🔲 Later: LLM Reasoning (mmv-agent)

Per-section LLM analysis with structured output:

```python
SECTION_SCHEMA = {
    "summary": str,
    "findings": [{
        "statement": str,
        "type": "FACT | INFERENCE",
        "confidence": "HIGH | MEDIUM | LOW",
        "confidence_reason": str,
        "source_citation": str,
        "data_reference": str,
    }],
    "data_gaps": [str],
    "risk_flags": [str],
}
```

Cross-section synthesis → executive summary. Fallback to deterministic `_synthesize()` if no LLM key.

---

### 🔲 Later: Agent System (mmv-agent)

- `executor.py` — task → plan → execute → report loop
- `router.py` — LLM-based task routing (Gemini primary, Opus for complex)
- `task_queue.py` — Pub/Sub consumer
- Tool discovery from domain repos at runtime

---

### 🔲 Later: Additional Data Sources (mmv-data)

| Source | What it provides |
|--------|-----------------|
| NOAA Climate Data Online | Historical temperature/precipitation |
| US Drought Monitor | Current drought conditions by state/county |
| National Weather Service | 7-day forecasts by location |
| USDA SSURGO | Soil quality metrics |
| Comparable sales | Farmland transaction data (TBD source) |

---

## Verification Plan

### End-to-End Test (Deterministic)

```bash
# Fetch data
python mmv-data/tools/usda.py --state TX
python mmv-data/tools/fred.py
python mmv-data/tools/eia.py --state TX

# Run underwriting (with test data or live)
python -m tools.underwrite  # from mmv-underwriting/

# Generate report
python -m tools.markdown_report  # from mmv-reporting/ (TODO)
```

### Trust Verification

- [ ] Every number in the report has a source footnote
- [ ] Every inference is labeled with confidence (HIGH/MEDIUM/LOW)
- [ ] Data freshness shown per section
- [ ] Data Gaps section identifies missing information
- [ ] Re-running with same data produces structurally identical output

### State Interchangeability

```bash
# Same pipeline, different state
python mmv-data/tools/usda.py --state CA
```
