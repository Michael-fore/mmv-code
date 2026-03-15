"""
Deal assembler — bridges mmv-data fetchers to mmv-underwriting.

One function call turns (lat, lon, acres, state, ...) into a fully
populated deal dict ready for run_chain(deal, farmland_underwrite).
"""

import importlib
import importlib.util
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Mono-repo import shim: directory names use hyphens (mmv-data) but Python
# imports need underscores (mmv_data).  Register underscore aliases so that
# `from mmv_data.tools.usda import ...` works from anywhere in the repo.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

for _dir_name, _mod_name in [
    ("mmv-data", "mmv_data"),
    ("mmv-underwriting", "mmv_underwriting"),
]:
    _pkg_path = _REPO_ROOT / _dir_name
    if _pkg_path.is_dir() and _mod_name not in sys.modules:
        _spec = importlib.util.spec_from_file_location(
            _mod_name,
            str(_pkg_path / "__init__.py"),
            submodule_search_locations=[str(_pkg_path)],
        )
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules[_mod_name] = _mod
        _spec.loader.exec_module(_mod)

from mmv_data.tools.usda import fetch_land_values, fetch_cash_rents
from mmv_data.tools.ssurgo import fetch_soil_data
from mmv_data.tools.drought import fetch_drought_status
from mmv_data.tools.noaa import fetch_climate_normals
from mmv_data.tools.graphcast import fetch_graphcast_forecast
from mmv_data.tools.fred import fetch_interest_rates
from mmv_data.tools.crop_production import fetch_crop_production


# ── Defaults for operating assumptions ──────────────────────────────
# These can all be overridden via the `overrides` dict.

DEFAULTS = {
    "vacancy_rate": 0.05,          # 5% unleased risk
    "hold_years": 10,
    "revenue_growth_rate": 0.02,   # 2% annual rent growth
    "expense_growth_rate": 0.025,  # 2.5% annual expense inflation
    "tax_per_acre": 15.00,
    "insurance_per_acre": 8.00,
    "management_rate": 0.08,       # 8% of EGI
    "maintenance_per_acre": 5.00,
    "exit_cap_rate": 0.035,        # 3.5% (slight cap rate expansion)
    "selling_cost_rate": 0.04,     # 4% broker + closing
    "annual_debt_service": 0,      # all-cash by default
}


def _unwrap(result: dict):
    """Extract the value from a provenance-wrapped response."""
    return result["value"]


def _cash_rent_from_usda(state: str) -> float:
    """Pull the most recent cash rent per acre for a state."""
    data = _unwrap(fetch_cash_rents(state))
    if not data:
        return 200.0  # safe fallback
    # Records are sorted by year; take the latest
    latest = max(data, key=lambda r: r["year"])
    return latest["rent_per_acre_usd"]


def _cap_rate_from_usda(state: str, cash_rent: float) -> float:
    """Derive an implied cap rate from land value and cash rent."""
    data = _unwrap(fetch_land_values(state))
    if not data:
        return 0.03  # 3% default
    latest = max(data, key=lambda r: r["year"])
    land_value = latest["value_per_acre_usd"]
    if land_value <= 0:
        return 0.03
    return cash_rent / land_value


def _drought_history_from_monitor(state: str, fips: str) -> dict:
    """Transform drought monitor data into the shape risk.py expects.

    Expects: {"pct_weeks_in_drought": float (0-100), "max_severity": str}
    """
    data = _unwrap(fetch_drought_status(state, fips))
    area = data.get("area_pct", {})

    # pct_weeks_in_drought approximated by total current drought coverage
    total_drought = data.get("total_drought_pct", 0)

    # Find max active severity level
    max_sev = "D0"
    for level in ["D4", "D3", "D2", "D1", "D0"]:
        if area.get(level, 0) > 0:
            max_sev = level
            break

    return {
        "pct_weeks_in_drought": total_drought,
        "max_severity": max_sev,
    }


def _soil_data_from_ssurgo(state: str, county_fips: str) -> dict:
    """Transform SSURGO data into the shape risk.py expects.

    Expects: {"avg_csr2": float (0-100)}
    """
    data = _unwrap(fetch_soil_data(state, county_fips))
    avg_cpi = data.get("summary", {}).get("avg_crop_productivity_index", 50)
    return {"avg_csr2": avg_cpi}


def _commodity_data_from_production(state: str) -> dict:
    """Derive commodity risk inputs from crop production data.

    Expects: {"price_volatility_pct": float, "trend": str}
    """
    data = _unwrap(fetch_crop_production(state))
    if not data:
        return {"price_volatility_pct": 15.0, "trend": "stable"}

    # Group production values by commodity, compute year-over-year volatility
    by_commodity = {}
    for rec in data:
        crop = rec["commodity_desc"]
        year = rec["year"]
        raw_val = rec.get("Value", "0")
        val = float(str(raw_val).replace(",", "")) if raw_val else 0
        by_commodity.setdefault(crop, []).append((year, val))

    # Average CV across commodities as a volatility proxy
    cvs = []
    for crop, records in by_commodity.items():
        records.sort(key=lambda r: r[0])
        values = [v for _, v in records if v > 0]
        if len(values) >= 2:
            mean = sum(values) / len(values)
            std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
            cvs.append((std / mean) * 100 if mean > 0 else 0)

    avg_vol = sum(cvs) / len(cvs) if cvs else 15.0

    # Trend: compare last two years of the largest crop
    trend = "stable"
    largest = max(by_commodity.items(), key=lambda x: len(x[1]), default=None)
    if largest:
        series = sorted(largest[1], key=lambda r: r[0])
        if len(series) >= 2:
            prev, curr = series[-2][1], series[-1][1]
            if prev > 0:
                change = (curr - prev) / prev
                if change > 0.05:
                    trend = "rising"
                elif change < -0.05:
                    trend = "declining"

    return {"price_volatility_pct": round(avg_vol, 2), "trend": trend}


def assemble_deal(
    *,
    lat: float,
    lon: float,
    acres: float,
    tillable_acres: float,
    purchase_price: float,
    equity_invested: float,
    state: str,
    county_fips: str,
    state_fips: str | None = None,
    comp_sales: list[dict] | None = None,
    overrides: dict | None = None,
) -> dict:
    """Fetch external data and build a deal dict ready for run_chain().

    Required args describe the property. Everything else is fetched or defaulted.
    Use `overrides` to replace any default assumption (e.g., hold_years, cap_rate).

    Returns a dict with all keys needed by farmland_underwrite chain.
    """
    if state_fips is None:
        state_fips = county_fips[:2]

    overrides = overrides or {}

    # ── Fetch external data ─────────────────────────────────────────
    cash_rent = overrides.pop("cash_rent_per_acre", None)
    if cash_rent is None:
        cash_rent = _cash_rent_from_usda(state)

    cap_rate = overrides.pop("cap_rate", None)
    if cap_rate is None:
        cap_rate = _cap_rate_from_usda(state, cash_rent)

    drought_history = _drought_history_from_monitor(state, state_fips)
    soil_data = _soil_data_from_ssurgo(state, county_fips)
    commodity_data = _commodity_data_from_production(state)

    # ── Assemble the deal dict ──────────────────────────────────────
    deal = {
        # Property basics
        "lat": lat,
        "lon": lon,
        "state": state,
        "county_fips": county_fips,
        "acres": acres,
        "tillable_acres": tillable_acres,
        "purchase_price": purchase_price,
        "equity_invested": equity_invested,

        # Revenue inputs
        "cash_rent_per_acre": cash_rent,
        "cap_rate": cap_rate,

        # Risk inputs (from fetchers)
        "drought_history": drought_history,
        "soil_data": soil_data,
        "commodity_data": commodity_data,

        # Comp sales (user-provided or empty)
        "comp_sales": comp_sales or [],
    }

    # Apply defaults, then let overrides win
    for key, default in DEFAULTS.items():
        deal.setdefault(key, default)
    deal.update(overrides)

    return deal


# ── Demo / smoke test ───────────────────────────────────────────────
if __name__ == "__main__":
    deal = assemble_deal(
        lat=41.88,
        lon=-93.63,
        acres=160,
        tillable_acres=152,
        purchase_price=1_760_000,   # $11,000/acre
        equity_invested=880_000,    # 50% down
        state="IA",
        county_fips="19169",        # Story County, IA
    )

    print("=== Assembled Deal ===")
    for k, v in deal.items():
        if isinstance(v, list) and len(v) > 2:
            print(f"  {k}: [{len(v)} items]")
        else:
            print(f"  {k}: {v}")

    # Run the full chain
    from mmv_underwriting.engine import run_chain
    from mmv_underwriting.chains import farmland_underwrite

    result = run_chain(deal, farmland_underwrite)
    print("\n=== Underwriting Results ===")
    for key in [
        "noi", "cap_rate_value", "comp_value",
        "composite_risk_score", "composite_risk_label",
        "exit_value", "irr", "cash_on_cash",
        "equity_multiple", "dscr",
    ]:
        print(f"  {key}: {result.get(key)}")
