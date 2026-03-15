"""EIA fetcher — U.S. Energy Information Administration data.

Source: EIA Open Data API v2.
Docs: https://www.eia.gov/opendata/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from .provenance import tag_provenance
except ImportError:
    from provenance import tag_provenance

_BASE_URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"


def fetch_electricity_prices(state: str = "TX") -> dict[str, Any]:
    """Fetch average retail electricity prices for a US state.

    Args:
        state: Two-letter state abbreviation (default ``"TX"``).

    Returns:
        Provenance-wrapped electricity price observations by sector.
    """
    params = {
        "frequency": "annual",
        "data[0]": "price",
        "facets[stateid][]": state,
        "start": "2019",
        "end": "2024",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
    }

    mock_data = {
        "state": state,
        "unit": "cents/kWh",
        "sector": "all sectors",
        "observations": [
            {"year": 2024, "price_cents_kwh": 12.8},
            {"year": 2023, "price_cents_kwh": 12.4},
            {"year": 2022, "price_cents_kwh": 13.0},
            {"year": 2021, "price_cents_kwh": 11.2},
            {"year": 2020, "price_cents_kwh": 10.5},
            {"year": 2019, "price_cents_kwh": 10.8},
        ],
    }

    return tag_provenance(
        mock_data,
        source="U.S. Energy Information Administration (EIA)",
        source_url=_BASE_URL,
        query_params=params,
        freshness="2024 annual",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== EIA Electricity Prices (TX) ===")
    result = fetch_electricity_prices("TX")
    print(json.dumps(result, indent=2))
