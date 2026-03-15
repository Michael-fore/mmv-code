---
name: data-inventory
description: Check what data is available — shows table name, row count, date range, and last fetched time
---

# Data Inventory

When a user asks "what data do we have?" or "what's available?", run the inventory script:

```bash
python /Users/tako/projects/ai-playground/MMV/.agent/skills/data-inventory/scripts/inventory.py
```

This prints a table like:

```
Dataset                      Source         Records   Date Range               Latest Value                     Last Fetched
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
land_values_TX               USDA NASS           55   2015-2025                $3,380/acre (2025)               2026-03-14 17:35
cash_rents_TX                USDA NASS           11   2015-2025                $36/acre (2025)                  2026-03-14 17:35
fred_FEDFUNDS                FRED               134   2015-01-01 to 2026-02    3.64                             2026-03-14 17:35
...
```

For JSON output (useful in code):

```bash
python /Users/tako/projects/ai-playground/MMV/.agent/skills/data-inventory/scripts/inventory.py --json
```

Or from Python:

```python
import sys
sys.path.insert(0, "/Users/tako/projects/ai-playground/MMV/.agent/skills/data-inventory/scripts")
from inventory import inventory
datasets = inventory()  # list of dicts with: name, source, records, date_range, latest_value, last_fetched
```

## Data Locations

All fetched data is cached as JSON at `/tmp/mmv_initial_fetch/`:
- `usda.json` — USDA NASS land values + cash rents
- `fred.json` — FRED macro series
- `eia.json` — EIA energy generation
- `underwriting_TX.json` — full underwriting analysis output

If no data exists, the inventory will report "(none)" and suggest running the fetchers. See the `query-data` skill for how to fetch.
