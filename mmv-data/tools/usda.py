"""USDA NASS fetcher — land values and cash rents by state.

Source: USDA National Agricultural Statistics Service (NASS) QuickStats API.
Docs: https://quickstats.nass.usda.gov/api
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Allow running as a standalone script or as part of the package.
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mmv_data.tools.provenance import tag_provenance

_BASE_URL = "https://quickstats.nass.usda.gov/api/api_GET/"


def fetch_land_values(state: str = "TX") -> dict[str, Any]:
    """Fetch average agricultural land values for a US state.

    Args:
        state: Two-letter FIPS state abbreviation (default ``"TX"``).

    Returns:
        Provenance-wrapped dict containing per-year land value records.
    """
    params = {
        "source_desc": "SURVEY",
        "sector_desc": "ECONOMICS",
        "commodity_desc": "AG LAND",
        "statisticcat_desc": "ASSET VALUE",
        "agg_level_desc": "STATE",
        "state_alpha": state,
        "year__GE": "2019",
        "format": "JSON",
    }

    mock_data = [
        {"year": 2024, "state": state, "value_per_acre_usd": 3_160, "unit": "$/acre"},
        {"year": 2023, "state": state, "value_per_acre_usd": 2_900, "unit": "$/acre"},
        {"year": 2022, "state": state, "value_per_acre_usd": 2_650, "unit": "$/acre"},
        {"year": 2021, "state": state, "value_per_acre_usd": 2_390, "unit": "$/acre"},
        {"year": 2020, "state": state, "value_per_acre_usd": 2_200, "unit": "$/acre"},
        {"year": 2019, "state": state, "value_per_acre_usd": 2_130, "unit": "$/acre"},
    ]

    return tag_provenance(
        mock_data,
        source="USDA NASS",
        source_url=_BASE_URL,
        query_params=params,
        freshness="2024 annual",
        is_mock=True,
    )


def fetch_cash_rents(state: str = "TX") -> dict[str, Any]:
    """Fetch average cash rent for cropland in a US state.

    Args:
        state: Two-letter FIPS state abbreviation (default ``"TX"``).

    Returns:
        Provenance-wrapped dict containing per-year cash rent records.
    """
    params = {
        "source_desc": "SURVEY",
        "commodity_desc": "RENT",
        "statisticcat_desc": "RENT, CASH, CROPLAND",
        "agg_level_desc": "STATE",
        "state_alpha": state,
        "year__GE": "2019",
        "format": "JSON",
    }

    mock_data = [
        {"year": 2024, "state": state, "rent_per_acre_usd": 144.0, "unit": "$/acre"},
        {"year": 2023, "state": state, "rent_per_acre_usd": 136.0, "unit": "$/acre"},
        {"year": 2022, "state": state, "rent_per_acre_usd": 126.0, "unit": "$/acre"},
        {"year": 2021, "state": state, "rent_per_acre_usd": 118.0, "unit": "$/acre"},
        {"year": 2020, "state": state, "rent_per_acre_usd": 112.0, "unit": "$/acre"},
        {"year": 2019, "state": state, "rent_per_acre_usd": 108.0, "unit": "$/acre"},
    ]

    return tag_provenance(
        mock_data,
        source="USDA NASS",
        source_url=_BASE_URL,
        query_params=params,
        freshness="2024 annual",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== USDA Land Values (TX) ===")
    result = fetch_land_values("TX")
    print(json.dumps(result, indent=2))

    print("\n=== USDA Cash Rents (TX) ===")
    result = fetch_cash_rents("TX")
    print(json.dumps(result, indent=2))
