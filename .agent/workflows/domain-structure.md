---
description: Enforce domain boundaries — ensures code changes go in the correct repo
---

# Domain Structure Enforcement

Before making ANY code change, determine which repo the change belongs in. **NEVER** put code in the wrong repo.

## Quick Reference

| If the change involves... | Put it in... |
|---------------------------|-------------|
| Agent behavior, task planning, LLM routing, tool discovery, executor | **mmv-agent** |
| Data fetching (ANY API), GCS storage, dedup, raw data schemas | **mmv-data** |
| Analysis, risk scoring, valuation, cap rates, exit scoring, comps | **mmv-underwriting** |
| Report generation, Excel export, notifications, output formatting | **mmv-reporting** |
| GCP deployments, Cloud Scheduler, Dockerfiles, CI/CD, IAM | **mmv-infra** |

## Rules

1. **BaseTool interface** lives in `mmv-agent/tools/base.py` — all other repos import from there
2. **Tool implementations** live in their domain repo's `tools/` package
3. **Cross-domain chains** (e.g. `underwrite_deal`) live in the consuming repo (mmv-underwriting), NOT in mmv-agent or mmv-data
4. **Data fetching** always goes in mmv-data, even if it's for a specific domain (weather → mmv-data, not mmv-underwriting)
5. **Analysis of that data** goes in mmv-underwriting (e.g. climate risk scoring uses data from mmv-data but the scoring logic is in mmv-underwriting)

## Cross-Repo Change Order

When a task spans multiple repos:
1. Start with **mmv-data** (add/modify data source)
2. Then **mmv-underwriting** (add/modify analysis)
3. Then **mmv-reporting** (update output)
4. Then **mmv-infra** (deploy changes)
5. Finally **mmv-agent** (only if routing/discovery needs updating)

## Repo Locations

All repos are submodules under `mmv-code/`:
```
/Users/tako/projects/ai-playground/MMV/mmv-code/
├── mmv-agent/
├── mmv-data/
├── mmv-underwriting/
├── mmv-reporting/
└── mmv-infra/
```

Standalone repo roots:
```
/Users/tako/projects/ai-playground/MMV/mmv-agent/
/Users/tako/projects/ai-playground/MMV/mmv-data/
/Users/tako/projects/ai-playground/MMV/mmv-underwriting/
/Users/tako/projects/ai-playground/MMV/mmv-reporting/
/Users/tako/projects/ai-playground/MMV/mmv-infra/
```
