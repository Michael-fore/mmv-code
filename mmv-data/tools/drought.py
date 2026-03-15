"""US Drought Monitor fetcher — drought severity by state/county.

Source: U.S. Drought Monitor (USDM) web services.
Docs: https://droughtmonitor.unl.edu/DmData/DataDownload.aspx
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mmv_data.tools.provenance import tag_provenance

_BASE_URL = "https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent"


def fetch_drought_status(state: str = "TX", fips: str = "48") -> dict[str, Any]:
    """Fetch current drought severity breakdown for a US state.

    Drought categories follow the USDM scale:
      - D0: Abnormally Dry
      - D1: Moderate Drought
      - D2: Severe Drought
      - D3: Extreme Drought
      - D4: Exceptional Drought

    Args:
        state: Two-letter state abbreviation (default ``"TX"``).
        fips: Two-digit FIPS state code (default ``"48"`` for Texas).

    Returns:
        Provenance-wrapped drought severity percentages.
    """
    params = {
        "aoi": fips,
        "startdate": "2024-12-01",
        "enddate": "2024-12-10",
        "statisticsType": "1",
    }

    mock_data = {
        "state": state,
        "report_date": "2024-12-10",
        "area_pct": {
            "none": 28.4,
            "D0": 22.1,
            "D1": 18.7,
            "D2": 16.3,
            "D3": 10.2,
            "D4": 4.3,
        },
        "total_drought_pct": 71.6,
        "dsci": 198,
        "dsci_description": "Drought Severity and Coverage Index (0-500 scale)",
    }

    return tag_provenance(
        mock_data,
        source="U.S. Drought Monitor (USDM)",
        source_url=_BASE_URL,
        query_params=params,
        freshness="weekly (2024-12-10)",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== US Drought Monitor (TX) ===")
    result = fetch_drought_status("TX")
    print(json.dumps(result, indent=2))
