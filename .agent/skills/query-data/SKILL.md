---
name: query-data
description: Query MMV data sources (USDA, FRED, EIA) — use this when you need farmland, macro, or energy data
---

# Query MMV Data

Use the fetchers in `mmv-data/tools/` to pull data. All tools return flat lists of dicts — no DB required.

## Quick Reference

```python
import sys
sys.path.insert(0, "/Users/tako/projects/ai-playground/MMV/mmv-data")
```

### USDA NASS (Land Values, Cash Rents, Crop Production)

> [!NOTE]
> USDA downloads a ~556MB bulk TSV from nass.usda.gov/datasets/. First call is slow (~2 min), but the data is comprehensive (full history by state).

```python
from tools.usda import fetch_land_values, fetch_cash_rents, fetch_crop_production

# Land values ($/acre) — returns: year, value_per_acre, land_type, state
land = fetch_land_values("TX", start_year=2015)

# Cash rents ($/acre/yr) — returns: year, rent_per_acre, state
rents = fetch_cash_rents("TX", start_year=2015)

# Crop production — returns: year, crop, production, unit, state
crops = fetch_crop_production("TX", crops=["CORN", "WHEAT", "COTTON", "SOYBEANS"], start_year=2020)
```

### FRED (Macro / Market Data)

```python
from tools.fred import fetch_series, fetch_all

# Single series — returns: observation_date, value, series_id
fedfunds = fetch_series("FEDFUNDS", start_date="2020-01-01")

# All default series (FEDFUNDS, CPIAUCSL, DTWEXBGS, FBDTLA, DGS10)
all_fred = fetch_all(start_date="2015-01-01")  # dict keyed by series_id
```

**Available series:**
| Series ID | Description |
|-----------|-------------|
| `FEDFUNDS` | Federal Funds Effective Rate |
| `CPIAUCSL` | Consumer Price Index (All Urban) |
| `DTWEXBGS` | Trade-Weighted USD Index |
| `FBDTLA` | Farm Business Sector Total Debt |
| `DGS10` | 10-Year Treasury Rate |

Any valid [FRED series ID](https://fred.stlouisfed.org/) works with `fetch_series()`.

### EIA (Energy Data)

```python
from tools.eia import fetch_solar_generation, fetch_all_generation_by_fuel

# Solar generation by state — returns: period, state, generation_mwh, fuel_type
solar = fetch_solar_generation(state="TX", start_year=2015)

# All fuel types for a state — returns same shape, multiple fuel_types
all_gen = fetch_all_generation_by_fuel("TX", start_year=2020)
```

> [!TIP]
> EIA rate-limits the DEMO_KEY. If you get 429 errors, wait a few seconds between calls or fetch fewer fuel types.

## Running Analysis on Fetched Data

```python
sys.path.insert(0, "/Users/tako/projects/ai-playground/MMV/mmv-underwriting")
from tools.underwrite import underwrite_deal

result = underwrite_deal("TX", land, rents, crops, all_fred, solar)
# result["summary"]["thesis"]  → "FAVORABLE" / "MIXED" / "UNFAVORABLE"
# result["sections"]           → land_values, cap_rate, risk, crop_economics, exit_optionality
# result["data_gaps"]          → list of missing data flags
```

## CLI Usage

```bash
# USDA
python mmv-data/tools/usda.py --state TX --data land_values
python mmv-data/tools/usda.py --state CA --data all

# FRED
python mmv-data/tools/fred.py                    # all default series
python mmv-data/tools/fred.py --series FEDFUNDS  # specific series

# EIA
python mmv-data/tools/eia.py --state TX
```

## Cached Data

If data has already been fetched this session, check `/tmp/mmv_initial_fetch/`:
- `usda.json` — land values + cash rents
- `fred.json` — all FRED series
- `eia.json` — solar + all-fuel generation
- `underwriting_TX.json` — full underwriting output
