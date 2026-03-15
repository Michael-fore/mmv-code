"""USDA FSA fetcher — Farm Service Agency CRP enrollment data.

Source: USDA Farm Service Agency Conservation Reserve Program (CRP).
Docs: https://www.fsa.usda.gov/programs-and-services/conservation-programs/reports-and-statistics/
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

_BASE_URL = "https://www.fsa.usda.gov/Assets/USDA-FSA-Public/usdafiles/Conservation/PDF/Summary"


def fetch_crp_enrollment(state: str = "TX") -> dict[str, Any]:
    """Fetch Conservation Reserve Program enrollment data for a US state.

    CRP data includes total enrolled acreage, annual rental payments, and
    contract counts, which are important for farmland underwriting.

    Args:
        state: Two-letter state abbreviation (default ``"TX"``).

    Returns:
        Provenance-wrapped CRP enrollment statistics.
    """
    params = {
        "state": state,
        "fiscal_year": "2024",
        "report_type": "enrollment_summary",
    }

    mock_data = {
        "state": state,
        "fiscal_year": 2024,
        "total_enrolled_acres": 3_842_100,
        "active_contracts": 48_210,
        "avg_rental_rate_per_acre_usd": 58.40,
        "annual_rental_payments_usd": 224_378_640,
        "by_practice": [
            {"practice": "CP1 - Intro of Grasses", "acres": 1_120_000},
            {"practice": "CP2 - Establishment of Grasses", "acres": 890_000},
            {"practice": "CP10 - Grass Waterways", "acres": 342_000},
            {"practice": "CP25 - Rare & Declining Habitat", "acres": 278_500},
            {"practice": "CP33 - Habitat Buffers for Upland Birds", "acres": 215_600},
            {"practice": "Other", "acres": 996_000},
        ],
        "trend": [
            {"year": 2024, "enrolled_acres": 3_842_100},
            {"year": 2023, "enrolled_acres": 3_910_400},
            {"year": 2022, "enrolled_acres": 4_012_300},
            {"year": 2021, "enrolled_acres": 4_158_700},
            {"year": 2020, "enrolled_acres": 4_295_100},
        ],
    }

    return tag_provenance(
        mock_data,
        source="USDA Farm Service Agency (FSA)",
        source_url=_BASE_URL,
        query_params=params,
        freshness="FY 2024",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== USDA FSA CRP Enrollment (TX) ===")
    result = fetch_crp_enrollment("TX")
    print(json.dumps(result, indent=2))
