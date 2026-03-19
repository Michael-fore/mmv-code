---
description: Core architecture rules and constraints for the MMV platform
---

# MMV Architecture Rules

## Storage
- **Raw files → GCS (Google Cloud Storage)**. All raw/ingested files go to GCS buckets.
- **No duplicate files.** Deduplicate before storing — use content hashing or deterministic naming.

## Compute & Infrastructure
- **Prefer serverless** wherever possible (Cloud Functions, Cloud Run, Cloud Workflows).
- **GCP Project**: `mmv-cloud`
- **Recurring tasks**: When a user requests a recurring task, spin up **Cloud Scheduler → Cloud Functions**.
- **Long-running tasks**: For potentially long-running jobs (multi-step LLM chains, batch processing, large data pipelines), use **Cloud Run Jobs** instead of Cloud Functions.

## Data & OLAP
- **Primary database: Cloud SQL PostgreSQL** (Google-managed, serverless-friendly).
  - Each data source gets its own flat table.
  - Always query the data to understand its shape before building.
- **Raw data**: Always land in GCS first, then load into PostgreSQL.
- **Free API keys are fine**: If data requires a free API key (USDA NASS, FRED, EIA, etc.), register and use one. Avoid paid/proprietary data sources unless explicitly approved.
- **ClickHouse on GCE**: Available as a secondary OLAP layer for heavy analytics (scripts in `mmv-infra/clickhouse/`). PostgreSQL remains the primary datastore.
- **BigQuery**: Avoid unless query volume is very low.

## API & Function Design
- **Composable primitives**: Distinct, atomic actions should be standalone functions/endpoints.
- **Complex tasks = chained primitives** with one-off glue logic where needed.
- Don't build monolithic endpoints — keep things modular and reusable.

## Output & User Experience
- **Dual audience**: Software engineers AND real estate professionals.
- **Tabular-first output**: All final data must be easily convertible to tabular format (DataFrames, CSV, `.xlsx`).
- Reports should be readable by non-technical stakeholders.

## AI & Models
- **Heavily AI-driven app** — multiple LLM providers.
- **Primary model: Gemini** — use for most tasks (cheap, fast, good enough).
- **Complex reasoning: Claude Opus** — use for tasks requiring deep analysis or nuanced judgment.
- Always include deterministic fallbacks where possible.
- **LLMs in the cold path only** — never call an LLM during a live scan/query. LLMs feed data pipelines (alias discovery, entity resolution) async and offline; the hot path uses deterministic lookups only.

## Data Enrichment & Signal Pattern
- **Signal Provider pattern** for all prospect scoring enrichment. Each data source (DB table, external API, client CRM) is a standalone `SignalProvider` module that fetches by `account_number` and returns scored sub-dimensions. New sources register with the registry — the core scanner query is never modified.
- **Canonical vocabulary** is the single source of truth in `signals/canonical_vocab.py`. All ingest scripts and signal providers map to it. Unknown terms are logged to `unmapped_terms` table, never silently dropped.
- **Vocab resolution job** runs: (1) immediately on new source registration, (2) nightly sweep, (3) on-demand CLI. LLM proposes additions; high-confidence mappings auto-commit, ambiguous ones queue for human review.
- **Entity name resolution** is pre-computed at ingest time into an `entity_aliases` table. Never do fuzzy string matching in the hot path.
