"""FRED fetcher — Federal Reserve Economic Data.

Source: Federal Reserve Bank of St. Louis FRED API.
Docs: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mmv_data.tools.provenance import tag_provenance

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_interest_rates(series_id: str = "DGS10") -> dict[str, Any]:
    """Fetch a FRED time series (default: 10-Year Treasury yield).

    Args:
        series_id: FRED series identifier (default ``"DGS10"``).

    Returns:
        Provenance-wrapped list of date/value observations.
    """
    params = {
        "series_id": series_id,
        "observation_start": "2023-01-01",
        "file_type": "json",
    }

    mock_data = {
        "series_id": series_id,
        "title": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity",
        "observations": [
            {"date": "2024-12-01", "value": 4.39},
            {"date": "2024-11-01", "value": 4.24},
            {"date": "2024-10-01", "value": 4.10},
            {"date": "2024-09-01", "value": 3.78},
            {"date": "2024-06-01", "value": 4.32},
            {"date": "2024-03-01", "value": 4.20},
            {"date": "2024-01-01", "value": 3.95},
            {"date": "2023-12-01", "value": 3.88},
            {"date": "2023-06-01", "value": 3.81},
            {"date": "2023-01-01", "value": 3.51},
        ],
    }

    return tag_provenance(
        mock_data,
        source="Federal Reserve Economic Data (FRED)",
        source_url=_BASE_URL,
        query_params=params,
        freshness="monthly",
        is_mock=True,
    )


def fetch_farm_income(series_id: str = "B1411C0A052NBEA") -> dict[str, Any]:
    """Fetch national farm income data from FRED.

    Args:
        series_id: FRED series for farm income (default is BEA farm income series).

    Returns:
        Provenance-wrapped observations.
    """
    params = {
        "series_id": series_id,
        "observation_start": "2019-01-01",
        "file_type": "json",
    }

    mock_data = {
        "series_id": series_id,
        "title": "Farm Proprietors' Income",
        "units": "billions of USD",
        "observations": [
            {"date": "2024-01-01", "value": 87.2},
            {"date": "2023-01-01", "value": 93.5},
            {"date": "2022-01-01", "value": 119.8},
            {"date": "2021-01-01", "value": 101.3},
            {"date": "2020-01-01", "value": 72.4},
            {"date": "2019-01-01", "value": 63.1},
        ],
    }

    return tag_provenance(
        mock_data,
        source="Federal Reserve Economic Data (FRED)",
        source_url=_BASE_URL,
        query_params=params,
        freshness="2024 annual",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== FRED 10-Year Treasury Yield ===")
    result = fetch_interest_rates()
    print(json.dumps(result, indent=2))

    print("\n=== FRED Farm Income ===")
    result = fetch_farm_income()
    print(json.dumps(result, indent=2))
