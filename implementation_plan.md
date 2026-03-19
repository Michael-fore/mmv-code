# MMV Platform — Implementation Plan

## Goal

Build an AI-driven farmland investment analysis platform across six domain-separated repos. The platform must:

- Fetch real data from free public sources **with full source provenance**
- Produce deterministic analysis (underwriting, risk scoring, exit optionality)
- Use an **LLM reasoning layer** to generate contextual, cited analysis where FACT/INFERENCE is separated and confidence is scored
- Output **trust-aware reports** where every claim is traceable
- Be config-driven (Texas default, swap to any state)
- Run autonomously via an agent system

---

## Architecture

```
┌─ mmv-front ─────────────────────────────────────────────┐
│  Express server · Chat UI · Tool dashboard              │
│  User-facing entry point → bridges to agent layer       │
└────────────────────────┬────────────────────────────────┘
                         │ user requests
                         ▼
┌─ mmv-agent ────────────────────────────────────────────-┐
│  Daily pipeline · Task registry · LLM analyst           │
│  Orchestrates: fetch → analyze → report → notify        │
└──────┬────────────────┬─────────────────┬───────────────┘
       │                │                 │
       ▼                ▼                 ▼
┌─ mmv-data ──────┐ ┌─ mmv-tools/underwriting ┐ ┌─ mmv-tools/reporting ─┐
│  Fetchers       │ │  Analysis               │ │  Markdown · Excel      │
│  USDA · FRED ·  │ │  Land values ·          │ │  Notifications         │
│  EIA · NOAA ·   │ │  Cap rate · Risk        │ │  Source provenance     │
│  FEMA · Census  │ │  Exit · Underwrite      │ │  FACT/INFERENCE        │
│  → GCS → PG     │ │                         │ │                        │
└─────────────────┘ └─────────────────────────┘ └────────────────────────┘

mmv-infra: GCP deployments, Cloud SQL PostgreSQL, GCS, Cloud Scheduler

```

### Cross-Repo Rules

- **Data is the interface** — repos communicate via data (dicts/JSON), never import code from each other
- **Change order**: mmv-data → mmv-tools/underwriting → mmv-tools/reporting → mmv-infra → mmv-agent → mmv-front
- Domain enforcement per `.agent/workflows/domain-structure.md`

---

## Current Status

### ✅ Complete

#### mmv-data/pipelines/tools/
| File | What it does |
|------|-------------|
| `usda.py` | Bulk TSV download from NASS datasets — land values, cash rents, crop production |
| `fred.py` | CSV endpoint — fed funds, CPI, USD index, farm debt, 10Y treasury |
| `eia.py` | API v2 — solar generation by state, all fuel types by state |
| `noaa.py` | NOAA NCEI historical climate data |
| `drought.py` | US Drought Monitor conditions |
| `ssurgo.py` | USDA NRCS soil quality metrics |
| `census.py` | Census Bureau population data by county |
| `usda_fas.py` | USDA FAS export data |
| `usda_fsa.py` | USDA FSA CRP enrollment |
| `cad.py` | County appraisal district records (HCAD, Travis, Dallas) |
| `fema.py` | FEMA NFHL flood zone lookups |
| `tx_entities.py` | Texas corporate/LLC entity lookups |
| `sec_edgar.py` | SEC EDGAR REIT filings |
| `tamu_realestate.py` | TAMU real estate data |
| `provenance.py` | Source metadata tagging for all fetchers |
| `gcs.py` | GCS upload with content-hash dedup |
| `load_to_postgres.py` | PostgreSQL loader |


#### mmv-tools/underwriting/tools/
| File | What it does |
|------|-------------|
| `land_values.py` | CAGR, real returns, volatility, YoY trends |
| `cap_rate.py` | Implied cap rate series, CRE benchmark comparison |
| `risk_scoring.py` | 1980s crisis analog — 6 weighted factors, composite 0-100 |
| `crop_economics.py` | Crop stability (CV), HHI diversification, rent trends |
| `exit_analysis.py` | Solar lease premium, development potential, composite score |
| `underwrite.py` | Chains all primitives → full underwriting package with data gaps |
| `query_cad_properties.py` | Query CAD property records from PostgreSQL |
| `query_deed_records.py` | Query deed/transfer history |
| `query_ownership_history.py` | Query prior ownership records |
| `query_tax_history.py` | Query annual tax assessment history |
| `query_property_permits.py` | Query building permits |
| `query_sale_comps.py` | Query comparable sales |
| `query_market_reports.py` | Query CRE market reports |
| `query_asset_benchmarks.py` | Query cap rate / NOI benchmarks |
| `query_parcel_geometries.py` | Query parcel boundary geometry |

#### mmv-tools/reporting/tools/
| File | What it does |
|------|-------------|
| `markdown_report.py` | Trust-aware markdown report rendering |

#### mmv-agent/
| File | What it does |
|------|-------------|
| `daily_pipeline.py` | Entry point for daily task execution |
| `tasks/registry.py` | Task name → class mapping |
| `tasks/executor.py` | Task execution engine |
| `tools/llm_analyst.py` | LLM-powered analysis (Gemini) |



#### mmv-front/
| File | What it does |
|------|-------------|
| `server.js` | Express server with Gemini chat + tool endpoints |
| `tools-bridge.js` | Discovers and invokes Python tools from domain repos |
| `manifest-loader.js` | Tool and pipeline template discovery via FastAPI `/tools` endpoint |

---

### ✅ Complete: Provenance Layer (mmv-data)

Every fetcher's output is wrapped with source metadata via `provenance.py`:

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

---

### ✅ Complete: Report Generation (mmv-reporting)

Markdown report rendering of `underwrite_deal()` output via `markdown_report.py`.

- Source footnotes per data point
- FACT/INFERENCE labels on every claim
- Confidence badges (🟢 HIGH / 🟡 MEDIUM / 🔴 LOW)
- Data freshness per section
- Data Gaps & Caveats section
- Reproducibility footer

🔲 Planned: Excel export, notification tools.

---

### ✅ Complete: Persistence Layer (mmv-data + mmv-infra)

1. GCS upload with content-hash dedup → `mmv-data/pipelines/tools/gcs.py`
2. PostgreSQL loader → `mmv-data/pipelines/tools/load_to_postgres.py`

---

### ✅ Complete: Additional Data Sources (mmv-data)

| Source | File | What it provides |
|--------|------|-----------------|
| NOAA Climate Data Online | `noaa.py` | Historical temperature/precipitation |
| US Drought Monitor | `drought.py` | Current drought conditions by state |
| USDA SSURGO | `ssurgo.py` | Soil quality metrics |
| Census Bureau | `census.py` | Population data by county |
| USDA FAS | `usda_fas.py` | Export data |
| USDA FSA | `usda_fsa.py` | CRP enrollment |
| HCAD | `cad.py` | County appraisal district records |
| FEMA NFHL | `fema.py` | Flood zone data |
| TX SOS / OpenCorporates | `tx_entities.py` | Corporate/LLC entity lookups |
| SEC EDGAR | `sec_edgar.py` | REIT/CRE public filings |

---

### ✅ Partial: LLM Reasoning Enhancement (mmv-agent)

`llm_analyst.py` is implemented — per-section LLM analysis using Gemini, structured output with FACT/INFERENCE labels and confidence scores.

🔲 **Remaining**: cross-section synthesis → executive summary. Currently falls back to deterministic `_synthesize()`.

---

### 🔲 Later: Additional Data Sources (mmv-data)

| Source | What it provides |
|--------|-----------------|
| National Weather Service | 7-day forecasts by location |
| Comparable sales | Farmland transaction data (TBD source) |

---

## Verification Plan

### End-to-End Test (Deterministic)

```bash
# Fetch data
python -m pipelines.tools.usda --state TX   # from mmv-data/
python -m pipelines.tools.fred              # from mmv-data/
python -m pipelines.tools.eia --state TX    # from mmv-data/

# Run underwriting (with test data or live)
python -m tools.underwrite  # from mmv-underwriting/

# Generate report
python -m tools.markdown_report  # from mmv-reporting/
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
python -m pipelines.tools.usda --state CA  # from mmv-data/
```
