---
name: doc-coherence
description: Audit all markdown docs for coherence — finds drift between READMEs, workflows, implementation plan, and actual code
---

# Documentation Coherence Audit

Run this skill whenever you suspect documentation drift, or periodically to keep docs in sync with the codebase.

## When to Use

- After adding new tools, data sources, or repos
- After changing architecture (DB, infra, deployment model)
- After moving files between repos
- Periodically as a health check
- When the user asks to "check docs" or "manage drift"

## Step 1: Discover All Markdown Files

Find every `.md` file in the codebase (excluding `node_modules`, `.git`, `dist`, `build`):

```
Locations to scan:
- /Users/tako/projects/ai-playground/MMV/*.md              (root-level docs)
- /Users/tako/projects/ai-playground/MMV/mmv-*/README.md    (repo READMEs)
- /Users/tako/projects/ai-playground/MMV/mmv-data/*.md      (data catalog)
- /Users/tako/projects/ai-playground/MMV/.agent/workflows/  (workflow rules)
```

Read ALL of them before making any judgments.

## Step 2: Cross-Reference Against Actual Code

For each repo, verify:

### Tool/File Inventory
- List actual `.py` files in each repo's `tools/` directory
- Compare against what the README claims exists
- Flag any tools listed in docs but missing in code (aspirational drift)
- Flag any files in code but missing from docs (undocumented drift)

### Architecture Claims
Check these specific claims are consistent **across all docs**:

| Claim | Check these files |
|-------|-------------------|
| Number of repos | `implementation_plan.md` goal section, `domain-structure.md` |
| Primary database | `architecture-rules.md`, `implementation_plan.md`, `mmv-infra/README.md` |
| Change order | `implementation_plan.md`, `domain-structure.md` |
| API key policy | `architecture-rules.md`, `data-rules.md` |
| Domain boundaries | `domain-structure.md` quick reference table vs actual repo contents |
| Cross-repo import rules | `rules.md` vs `domain-structure.md` rules section |

### Data Catalog vs SQL DDL
- Read `/Users/tako/projects/ai-playground/MMV/mmv-infra/sql/create_tables.sql`
- Compare every table definition against `mmv-data/data_catalog.md`
- Flag missing column definitions, mismatched types, or missing tables

### Implementation Plan Status
- For each item marked ✅ in `implementation_plan.md`, verify the file actually exists
- For each item marked 🔲, verify it hasn't already been built
- Check the architecture diagram matches the current repo structure

## Step 3: Classify Discrepancies

Rate each discrepancy by severity:

| Severity | Meaning | Examples |
|----------|---------|---------|
| 🔴 High | Contradicts reality, could cause wrong decisions | DB type mismatch, missing domain from structure |
| 🟡 Medium | Out of date but not dangerous | Stale status checkboxes, aspirational tool lists |
| 🟢 Low | Cosmetic or trivial | Typos, naming conventions, comment drift |

## Step 4: Report & Ask Questions

Present findings as a structured report with:
1. **What's coherent** — confirm what IS correct (builds trust)
2. **Discrepancies found** — each with severity, the conflicting statements, and a specific question
3. **Summary table** — quick scan of all issues

**Always ask the user before fixing.** Some "discrepancies" are intentional (aspirational docs, prototyping workarounds, etc).

## Step 5: Fix & Verify

After getting answers:
1. Apply fixes to all affected files
2. Re-read ALL updated files
3. Run a second pass looking for issues introduced by the fixes
4. Verify with spot-checks (grep for key terms, check file existence)

## Key Consistency Rules

These must ALWAYS be true across docs:

1. **Repo count** mentioned anywhere must match actual repos
2. **Change order** must be identical in `implementation_plan.md` and `domain-structure.md`
3. **Every repo** in the domain structure must have a README with a matching Scope section
4. **Every `.py` file** in a `tools/` directory should appear in either the repo README or `implementation_plan.md`
5. **Database references** must be consistent (primary = PostgreSQL, secondary = ClickHouse)
6. **API key policy** must be consistent across `architecture-rules.md` and `data-rules.md`
7. **Data catalog** table count and schemas must match `create_tables.sql`
8. **Architecture diagram** in `implementation_plan.md` must reflect actual data flow

## Common Drift Patterns

Watch for these recurring issues:

| Pattern | What happens | How to catch |
|---------|-------------|-------------|
| **Aspirational README** | README lists tools not yet built | Compare README tool table against actual files |
| **Stale status** | Implementation plan says 🔲 for something already built | Check if file exists for each 🔲 item |
| **New repo forgotten** | New repo added but not in domain-structure or change order | Count repos in filesystem vs docs |
| **DB migration** | Switched databases but old one still referenced | Grep for old DB name across all docs |
| **File moved** | File moved between repos but docs not updated | Check each README's file list against actual contents |
| **Schema drift** | SQL DDL changed but data_catalog.md not updated | Diff column lists between DDL and catalog |
