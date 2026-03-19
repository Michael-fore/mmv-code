---
name: system-map
description: Map the internal ontology of the MMV system — shows modules, data flows, tables, cross-repo dependencies, and detects issues
---

# System Map

When a user asks "what does our system look like?", "how is X connected to Y?", "show me the architecture", or wants to find issues/orphans, run the system map:

## Text Report

```bash
python /Users/tako/projects/ai-playground/MMV/.agent/skills/system-map/scripts/system_map.py
```

This prints a structured report showing:
- **Repo overview** — every module, its public functions, and line count
- **Database tables** — all tables with PKs, columns, and which code references them
- **Data flows** — the full pipeline: External API → fetcher → table → analysis → report
- **Cross-repo dependencies** — which modules import across repo boundaries
- **Issues** — orphaned modules, unused tables, large files, missing consumers

## JSON Output

```bash
python /Users/tako/projects/ai-playground/MMV/.agent/skills/system-map/scripts/system_map.py --json
```

Or from Python:

```python
import sys
sys.path.insert(0, "/Users/tako/projects/ai-playground/MMV/.agent/skills/system-map/scripts")
from system_map import run
data = run()  # dict with: modules, tables, flows, cross_edges, issues
```

## Interactive Visual

Generate a standalone HTML file with an interactive D3.js force-directed graph:

```bash
python /Users/tako/projects/ai-playground/MMV/.agent/skills/system-map/scripts/system_map.py --html
# → /tmp/mmv_system_map.html

# Or generate and open immediately:
python /Users/tako/projects/ai-playground/MMV/.agent/skills/system-map/scripts/system_map.py --html --open
```

The visual shows:
- **Color-coded nodes** — grouped by repo, with external APIs (orange) and tables (teal)
- **Edge types** — data flow (solid arrows), imports (dashed), table access (dotted)
- **Hover** to highlight a node's connections
- **Search** to filter by module/table name
- **Drag** nodes to rearrange, **zoom** with scroll
- **Issues panel** with detected problems
