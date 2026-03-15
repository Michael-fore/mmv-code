"""SSURGO fetcher — USDA Soil Survey Geographic Database.

Source: USDA Natural Resources Conservation Service (NRCS) Soil Data Access.
Docs: https://sdmdataaccess.nrcs.usda.gov/
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

_BASE_URL = "https://sdmdataaccess.nrcs.usda.gov/Tabular/SDMTabularService/post.rest"


def fetch_soil_data(
    state: str = "TX",
    county_fips: str = "48201",
) -> dict[str, Any]:
    """Fetch dominant soil component data for a county from SSURGO.

    Returns aggregated soil characteristics including capability class,
    drainage class, and crop productivity index — critical inputs for
    farmland underwriting.

    Args:
        state: Two-letter state abbreviation (default ``"TX"``).
        county_fips: Five-digit county FIPS code (default ``"48201"`` — Harris County, TX).

    Returns:
        Provenance-wrapped soil survey data for the county.
    """
    params = {
        "format": "JSON",
        "query_type": "mapunit_aggregated",
        "area_symbol": county_fips,
    }

    mock_data = {
        "state": state,
        "county_fips": county_fips,
        "county_name": "Harris County",
        "dominant_components": [
            {
                "mukey": "654321",
                "map_unit_name": "Lake Charles clay, 0 to 1 percent slopes",
                "pct_area": 18.3,
                "capability_class": "2w",
                "drainage_class": "Somewhat poorly drained",
                "farm_class": "Prime farmland",
                "crop_productivity_index": 82,
                "hydric_rating": "Predominantly Hydric",
            },
            {
                "mukey": "654322",
                "map_unit_name": "Bernard clay loam, 0 to 1 percent slopes",
                "pct_area": 14.7,
                "capability_class": "3w",
                "drainage_class": "Somewhat poorly drained",
                "farm_class": "Prime farmland if drained",
                "crop_productivity_index": 74,
                "hydric_rating": "Partially Hydric",
            },
            {
                "mukey": "654323",
                "map_unit_name": "Katy fine sandy loam, 0 to 1 percent slopes",
                "pct_area": 11.2,
                "capability_class": "2e",
                "drainage_class": "Moderately well drained",
                "farm_class": "Prime farmland",
                "crop_productivity_index": 78,
                "hydric_rating": "Not Hydric",
            },
        ],
        "summary": {
            "total_map_units": 47,
            "pct_prime_farmland": 42.6,
            "pct_hydric_soils": 31.8,
            "avg_crop_productivity_index": 71,
        },
    }

    return tag_provenance(
        mock_data,
        source="USDA NRCS SSURGO",
        source_url=_BASE_URL,
        query_params=params,
        freshness="FY 2024 survey",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== SSURGO Soil Data (Harris County, TX) ===")
    result = fetch_soil_data("TX", "48201")
    print(json.dumps(result, indent=2))
