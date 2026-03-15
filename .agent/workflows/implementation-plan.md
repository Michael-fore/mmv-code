---
description: Read the implementation plan before making any changes
---

# Implementation Plan Context

Before making ANY code change, read the master implementation plan:

```
/Users/tako/projects/ai-playground/MMV/implementation_plan.md
```

This file contains:
- The full architecture (which repo owns what)
- Current status of all components (what's built vs TODO)
- Priority order for next work
- Verification plan

Also read these workflows at `/Users/tako/projects/ai-playground/MMV/.agent/workflows/`:
- `architecture-rules.md` — storage, compute, data, output rules
- `domain-structure.md` — which repo code belongs in
- `data-rules.md` — how to fetch and store data
- `rules.md` — cross-repo interface rules
