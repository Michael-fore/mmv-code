"""US Census Bureau fetcher — population and demographic data.

Source: U.S. Census Bureau American Community Survey (ACS) API.
Docs: https://www.census.gov/data/developers/data-sets/acs-5year.html
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mmv_data.tools.provenance import tag_provenance

_BASE_URL = "https://api.census.gov/data/2023/acs/acs5"


def fetch_population_data(
    state: str = "TX",
    state_fips: str = "48",
) -> dict[str, Any]:
    """Fetch population and key demographic indicators for a US state.

    Retrieves total population, median household income, and population
    growth trend — used in market demand analysis for real estate
    underwriting.

    Args:
        state: Two-letter state abbreviation (default ``"TX"``).
        state_fips: Two-digit FIPS state code (default ``"48"`` for Texas).

    Returns:
        Provenance-wrapped population and demographic data.
    """
    params = {
        "get": "B01003_001E,B19013_001E,B01001_001E",
        "for": f"state:{state_fips}",
        "key": "CENSUS_API_KEY",
    }

    mock_data = {
        "state": state,
        "state_fips": state_fips,
        "year": 2023,
        "total_population": 30_503_340,
        "median_household_income_usd": 67_321,
        "population_trend": [
            {"year": 2023, "population": 30_503_340, "yoy_growth_pct": 1.6},
            {"year": 2022, "population": 30_029_572, "yoy_growth_pct": 1.7},
            {"year": 2021, "population": 29_527_941, "yoy_growth_pct": 1.3},
            {"year": 2020, "population": 29_145_505, "yoy_growth_pct": 1.0},
            {"year": 2019, "population": 28_862_581, "yoy_growth_pct": 1.3},
        ],
        "metro_areas": [
            {"name": "Dallas-Fort Worth-Arlington", "population": 7_862_000},
            {"name": "Houston-The Woodlands-Sugar Land", "population": 7_340_000},
            {"name": "San Antonio-New Braunfels", "population": 2_601_000},
            {"name": "Austin-Round Rock-Georgetown", "population": 2_473_000},
            {"name": "El Paso", "population": 868_000},
        ],
    }

    return tag_provenance(
        mock_data,
        source="U.S. Census Bureau (ACS 5-Year)",
        source_url=_BASE_URL,
        query_params=params,
        freshness="2023 ACS 5-year estimates",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== US Census Population Data (TX) ===")
    result = fetch_population_data("TX")
    print(json.dumps(result, indent=2))
