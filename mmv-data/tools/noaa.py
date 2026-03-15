"""NOAA fetcher — National Oceanic and Atmospheric Administration climate data.

Source: NOAA Climate Data Online (CDO) API.
Docs: https://www.ncdc.noaa.gov/cdo-web/webservices/v2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mmv_data.tools.provenance import tag_provenance

_BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"


def fetch_climate_normals(state: str = "TX", fips: str = "48") -> dict[str, Any]:
    """Fetch 30-year climate normals (temperature and precipitation) for a state.

    Args:
        state: Two-letter state abbreviation (default ``"TX"``).
        fips: Two-digit FIPS state code (default ``"48"`` for Texas).

    Returns:
        Provenance-wrapped climate normal records by month.
    """
    params = {
        "datasetid": "NORMAL_MLY",
        "locationid": f"FIPS:{fips}",
        "datatypeid": "MLY-TAVG-NORMAL,MLY-PRCP-NORMAL",
        "startdate": "2020-01-01",
        "enddate": "2020-12-31",
        "limit": 12,
    }

    mock_data = {
        "state": state,
        "period": "1991-2020 normals",
        "monthly": [
            {"month": 1,  "avg_temp_f": 46.1, "precip_in": 2.01},
            {"month": 2,  "avg_temp_f": 50.3, "precip_in": 2.19},
            {"month": 3,  "avg_temp_f": 57.8, "precip_in": 2.87},
            {"month": 4,  "avg_temp_f": 65.9, "precip_in": 2.97},
            {"month": 5,  "avg_temp_f": 74.0, "precip_in": 4.58},
            {"month": 6,  "avg_temp_f": 81.3, "precip_in": 3.78},
            {"month": 7,  "avg_temp_f": 84.5, "precip_in": 2.09},
            {"month": 8,  "avg_temp_f": 84.8, "precip_in": 2.27},
            {"month": 9,  "avg_temp_f": 78.4, "precip_in": 3.31},
            {"month": 10, "avg_temp_f": 67.6, "precip_in": 3.94},
            {"month": 11, "avg_temp_f": 56.0, "precip_in": 2.65},
            {"month": 12, "avg_temp_f": 47.5, "precip_in": 2.44},
        ],
    }

    return tag_provenance(
        mock_data,
        source="NOAA Climate Data Online",
        source_url=_BASE_URL,
        query_params=params,
        freshness="1991-2020 30-year normals",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== NOAA Climate Normals (TX) ===")
    result = fetch_climate_normals("TX")
    print(json.dumps(result, indent=2))
