"""USDA NASS QuickStats — crop production fetcher.

Fetches annual crop production data by state from the USDA National
Agricultural Statistics Service (NASS) QuickStats API.  When no API key
is configured the module returns realistic mock data so that downstream
consumers (underwriting models, reports) can develop without live access.

API docs: https://quickstats.nass.usda.gov/api/
Endpoint : https://quickstats.nass.usda.gov/api/api_GET/

Usage
-----
    from mmv_data.tools.crop_production import fetch_crop_production

    result = fetch_crop_production("TX")
    print(result["value"])        # list of crop-production records
    print(result["provenance"])   # source / freshness metadata
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Allow running as a standalone script or as part of the package.
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from .provenance import tag_provenance
except ImportError:
    from provenance import tag_provenance

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QUICKSTATS_API_URL = "https://quickstats.nass.usda.gov/api/api_GET/"
QUICKSTATS_BULK_URL = "https://quickstats.nass.usda.gov/nass_data_cache/downloads/"

DEFAULT_CROPS: list[str] = ["CORN", "WHEAT", "COTTON", "SOYBEANS"]

# Year lower-bound for the query window (inclusive).
MIN_YEAR = 2018

# Timeout in seconds for HTTP requests.
HTTP_TIMEOUT_SECONDS = 30

# ---------------------------------------------------------------------------
# Mock data — realistic TX production figures (units: BU / 480-lb bales)
# ---------------------------------------------------------------------------

_MOCK_TX_DATA: list[dict[str, Any]] = [
    {
        "commodity_desc": "CORN",
        "state_alpha": "TX",
        "year": 2023,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "286,560,000",
        "short_desc": "CORN, GRAIN - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "CORN",
        "state_alpha": "TX",
        "year": 2022,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "243,100,000",
        "short_desc": "CORN, GRAIN - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "CORN",
        "state_alpha": "TX",
        "year": 2020,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "309,400,000",
        "short_desc": "CORN, GRAIN - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "WHEAT",
        "state_alpha": "TX",
        "year": 2023,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "50,400,000",
        "short_desc": "WHEAT - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "WHEAT",
        "state_alpha": "TX",
        "year": 2022,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "35,100,000",
        "short_desc": "WHEAT - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "WHEAT",
        "state_alpha": "TX",
        "year": 2020,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "67,200,000",
        "short_desc": "WHEAT - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "COTTON",
        "state_alpha": "TX",
        "year": 2023,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "480 LB BALES",
        "Value": "7,850,000",
        "short_desc": "COTTON, UPLAND - PRODUCTION, MEASURED IN 480 LB BALES",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "COTTON",
        "state_alpha": "TX",
        "year": 2022,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "480 LB BALES",
        "Value": "3,420,000",
        "short_desc": "COTTON, UPLAND - PRODUCTION, MEASURED IN 480 LB BALES",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "COTTON",
        "state_alpha": "TX",
        "year": 2020,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "480 LB BALES",
        "Value": "8,280,000",
        "short_desc": "COTTON, UPLAND - PRODUCTION, MEASURED IN 480 LB BALES",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "SOYBEANS",
        "state_alpha": "TX",
        "year": 2023,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "5,520,000",
        "short_desc": "SOYBEANS - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "SOYBEANS",
        "state_alpha": "TX",
        "year": 2022,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "4,830,000",
        "short_desc": "SOYBEANS - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
    {
        "commodity_desc": "SOYBEANS",
        "state_alpha": "TX",
        "year": 2020,
        "statisticcat_desc": "PRODUCTION",
        "unit_desc": "BU",
        "Value": "4,140,000",
        "short_desc": "SOYBEANS - PRODUCTION, MEASURED IN BU",
        "source_desc": "SURVEY",
    },
]


def _resolve_api_key(api_key: str | None) -> str | None:
    """Return an explicit key or fall back to the NASS_API_KEY env var."""
    if api_key:
        return api_key
    return os.environ.get("NASS_API_KEY")


def _build_query_params(
    state: str,
    commodity: str,
    api_key: str,
) -> dict[str, str]:
    """Build QuickStats API query parameters for a single commodity."""
    return {
        "key": api_key,
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "group_desc": "FIELD CROPS",
        "statisticcat_desc": "PRODUCTION",
        "agg_level_desc": "STATE",
        "state_alpha": state.upper(),
        "commodity_desc": commodity.upper(),
        "year__GE": str(MIN_YEAR),
        "format": "JSON",
    }


def _mock_crop_data(
    state: str,
    crops: list[str],
) -> list[dict[str, Any]]:
    """Return mock data, filtering to requested crops.

    The built-in dataset covers TX.  For other states the same records are
    returned with the ``state_alpha`` field overwritten so that shape and
    schema are identical to live data.
    """
    upper_crops = {c.upper() for c in crops}
    records = [
        {**r, "state_alpha": state.upper()}
        for r in _MOCK_TX_DATA
        if r["commodity_desc"] in upper_crops
    ]
    return records


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_crop_production_api(
    state: str,
    crops: list[str] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch crop production data from the USDA NASS QuickStats REST API.

    Queries the API once per commodity and aggregates the results into a
    single list.  Falls back to mock data when no API key is available.

    Args:
        state: Two-letter US state abbreviation (e.g. ``"TX"``).
        crops: Commodities to query.  Defaults to
               ``["CORN", "WHEAT", "COTTON", "SOYBEANS"]``.
        api_key: NASS API key.  Falls back to ``NASS_API_KEY`` env var.

    Returns:
        Provenance-wrapped dict with ``value`` (list of record dicts) and
        ``provenance`` metadata.
    """
    crops = [c.upper() for c in (crops or DEFAULT_CROPS)]
    resolved_key = _resolve_api_key(api_key)

    # ----- mock mode -----
    if not resolved_key:
        logger.info(
            "No NASS API key found — returning mock crop production data "
            "for %s (crops: %s)",
            state,
            crops,
        )
        mock_records = _mock_crop_data(state, crops)
        return tag_provenance(
            mock_records,
            source="USDA NASS QuickStats",
            source_url=QUICKSTATS_API_URL,
            query_params={"state": state, "crops": crops, "year__GE": MIN_YEAR},
            freshness="mock — no live API key configured",
            is_mock=True,
        )

    # ----- live API mode -----
    all_records: list[dict[str, Any]] = []
    query_log: list[dict[str, str]] = []

    for commodity in crops:
        params = _build_query_params(state, commodity, resolved_key)
        url = f"{QUICKSTATS_API_URL}?{urlencode(params)}"
        query_log.append(params)

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                body = json.loads(resp.read().decode("utf-8"))

            records = body.get("data", [])
            logger.info(
                "QuickStats returned %d records for %s/%s",
                len(records),
                state,
                commodity,
            )
            all_records.extend(records)

        except HTTPError as exc:
            logger.error(
                "QuickStats HTTP %s for %s/%s: %s",
                exc.code,
                state,
                commodity,
                exc.reason,
            )
        except URLError as exc:
            logger.error(
                "QuickStats network error for %s/%s: %s",
                state,
                commodity,
                exc.reason,
            )

    return tag_provenance(
        all_records,
        source="USDA NASS QuickStats",
        source_url=QUICKSTATS_API_URL,
        query_params={"state": state, "crops": crops, "year__GE": MIN_YEAR},
        freshness=f"{MIN_YEAR}–present annual survey data",
        is_mock=False,
    )


def fetch_crop_production_bulk(state: str) -> dict[str, Any]:
    """Fetch crop production via the NASS bulk TSV download (stub).

    The NASS QuickStats bulk download provides a single ~1 GB tab-separated
    file covering *all* commodities, states, and years.  In practice this
    file regularly times out during download and is too large to parse in a
    serverless function.  This stub documents the approach and returns an
    error payload so callers can fall through to the per-commodity API.

    Args:
        state: Two-letter US state abbreviation (unused — documented for
               interface parity with :func:`fetch_crop_production_api`).

    Returns:
        Provenance-wrapped dict whose ``value`` is an error descriptor.
    """
    error_payload = {
        "error": "bulk_download_not_implemented",
        "detail": (
            "The NASS bulk TSV download (~1 GB) times out for large files "
            "and is not suitable for serverless/on-demand use.  Use the "
            "per-commodity REST API via fetch_crop_production_api() instead."
        ),
    }
    return tag_provenance(
        error_payload,
        source="USDA NASS QuickStats (bulk)",
        source_url=f"{QUICKSTATS_BULK_URL}qs.crops.txt",
        query_params={"state": state},
        freshness="N/A — not fetched",
        is_mock=False,
    )


def fetch_crop_production(
    state: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch crop production data, trying the REST API first then bulk.

    This is the primary entry point for consumers.  It attempts the
    per-commodity QuickStats REST API; if that fails (e.g. no key, network
    error returning zero records) it falls back to the bulk download stub
    which itself explains why that path is unsuitable.

    Args:
        state: Two-letter US state abbreviation (e.g. ``"TX"``).
        api_key: Optional NASS API key override.

    Returns:
        Provenance-wrapped dict — see :func:`fetch_crop_production_api`.
    """
    result = fetch_crop_production_api(state, api_key=api_key)

    # If the API returned actual records, use them.
    if result.get("value"):
        return result

    # Otherwise fall back to bulk (which is a stub explaining the limitation).
    logger.warning(
        "API returned no records for %s — falling back to bulk (stub).", state
    )
    return fetch_crop_production_bulk(state)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    target_state = sys.argv[1] if len(sys.argv) > 1 else "TX"
    output = fetch_crop_production(target_state)
    print(json.dumps(output, indent=2))
