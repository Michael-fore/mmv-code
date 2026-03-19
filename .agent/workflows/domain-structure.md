---
description: Enforce domain boundaries — ensures code changes go in the correct repo
---

# Domain Structure Enforcement

Before making ANY code change, determine which repo the change belongs in. **NEVER** put code in the wrong repo.

## Quick Reference

| If the change involves... | Put it in... |
|---------------------------|-------------|
| Agent behavior, task planning, LLM routing, tool discovery, executor | **mmv-agent** |
| Data fetching (ANY API), GCS storage, dedup, raw data schemas | **mmv-data** · manifests → `pipelines/tools/manifests/` |
| Analysis, risk scoring, valuation, cap rates, exit scoring, comps | **mmv-tools/underwriting** |
| Report generation, Excel export, notifications, output formatting | **mmv-tools/reporting** |
| GCP deployments, Cloud Scheduler, Dockerfiles, CI/CD, IAM | **mmv-infra** |
| Web UI, Express server, chat interface, tool bridge to agent layer | **mmv-front** |

## Rules

1. **BaseTool interface** lives in `mmv-agent/tools/base.py` — other repos import from there *(prototyping workaround; will be replaced with a shared package or protocol later)*
2. **Tool implementations** live in their domain repo's `tools/` package, or under `mmv-tools/`
3. **Cross-domain communication** (e.g. `mmv-agent` to `mmv-data`): Always communicate over HTTP/FastAPI. NO direct Python imports across domain boundaries.
4. **Cross-domain chains** (e.g. `underwrite_deal`) live in the consuming repo (`mmv-tools/underwriting`)
5. **Data fetching** always goes in mmv-data, even if it's for a specific domain (weather → mmv-data)
6. **Analysis of that data** goes in `mmv-tools/underwriting`

## Cross-Repo Change Order

When a task spans multiple repos:
1. Start with **mmv-data** (add/modify data source)
2. Then **mmv-tools/underwriting** (add/modify analysis)
3. Then **mmv-tools/reporting** (update output)
4. Then **mmv-infra** (deploy changes)
5. Then **mmv-agent** (only if routing/discovery needs updating)
6. Finally **mmv-front** (only if UI or agent bridge needs updating)

## Repo Locations

All repos are submodules under `mmv-code/`:
```
/Users/tako/projects/ai-playground/MMV/mmv-code/
├── mmv-agent/
├── mmv-data/
├── mmv-front/
├── mmv-tools/
└── mmv-infra/
```

Standalone repo roots:
```
/Users/tako/projects/ai-playground/MMV/mmv-agent/
/Users/tako/projects/ai-playground/MMV/mmv-data/
/Users/tako/projects/ai-playground/MMV/mmv-front/
/Users/tako/projects/ai-playground/MMV/mmv-tools/
/Users/tako/projects/ai-playground/MMV/mmv-infra/
```
