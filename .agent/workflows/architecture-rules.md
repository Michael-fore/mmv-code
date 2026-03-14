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
- **BigQuery is expensive** — evaluate cheaper alternatives first:
  - AlloyDB (columnar engine for analytics)
  - Self-hosted ClickHouse on GCE
  - BigQuery on-demand only if query volume is low
- Choose the right tool based on query patterns and cost.

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
