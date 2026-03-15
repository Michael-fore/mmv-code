"""USDA FAS fetcher — Foreign Agricultural Service export data.

Source: USDA FAS Global Agricultural Trade System (GATS).
Docs: https://apps.fas.usda.gov/gats/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mmv_data.tools.provenance import tag_provenance

_BASE_URL = "https://apps.fas.usda.gov/OpenData/api/esr/exports/commodityCode"


def fetch_export_data(commodity: str = "corn") -> dict[str, Any]:
    """Fetch US agricultural export volumes and values for a commodity.

    Args:
        commodity: Commodity name (default ``"corn"``).

    Returns:
        Provenance-wrapped export data by marketing year.
    """
    commodity_codes = {
        "corn": "0440000",
        "soybeans": "2222000",
        "wheat": "1001000",
        "cotton": "5201000",
    }
    code = commodity_codes.get(commodity.lower(), "0440000")

    params = {
        "commodityCode": code,
        "marketYear": "2024",
    }

    mock_data = {
        "commodity": commodity,
        "commodity_code": code,
        "unit": "metric tons (MT)",
        "marketing_years": [
            {"year": "2024/25", "exports_mt": 55_200_000, "value_usd_million": 14_820},
            {"year": "2023/24", "exports_mt": 53_800_000, "value_usd_million": 15_240},
            {"year": "2022/23", "exports_mt": 42_500_000, "value_usd_million": 17_310},
            {"year": "2021/22", "exports_mt": 62_700_000, "value_usd_million": 18_950},
            {"year": "2020/21", "exports_mt": 70_000_000, "value_usd_million": 16_130},
        ],
        "top_destinations": [
            {"country": "Mexico", "pct_share": 28.1},
            {"country": "Japan", "pct_share": 15.4},
            {"country": "Colombia", "pct_share": 8.2},
            {"country": "South Korea", "pct_share": 6.9},
            {"country": "China", "pct_share": 5.7},
        ],
    }

    return tag_provenance(
        mock_data,
        source="USDA Foreign Agricultural Service (FAS)",
        source_url=_BASE_URL,
        query_params=params,
        freshness="2024/25 marketing year",
        is_mock=True,
    )


if __name__ == "__main__":
    print("=== USDA FAS Export Data (Corn) ===")
    result = fetch_export_data("corn")
    print(json.dumps(result, indent=2))
