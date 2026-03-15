"""Provenance metadata layer for MMV data fetchers.

Every piece of external data flowing into the MMV platform is wrapped with
provenance metadata so downstream consumers (underwriting, reporting) can
trace any number back to its original source, query, and retrieval time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def tag_provenance(
    data: Any,
    *,
    source: str,
    source_url: str,
    query_params: dict[str, Any] | None = None,
    freshness: str,
    is_mock: bool = False,
) -> dict[str, Any]:
    """Wrap a data payload with standardised provenance metadata.

    Args:
        data: The original data (dict, list, scalar — anything JSON-serialisable).
        source: Human-readable name of the data source (e.g. "USDA NASS").
        source_url: The API endpoint or URL the data was fetched from.
        query_params: Parameters used in the request. Defaults to empty dict.
        freshness: Temporal descriptor (e.g. "2024 annual", "real-time", "monthly").
        is_mock: True when the payload contains synthetic / test data.

    Returns:
        A dict with ``value`` (the original data) and ``provenance`` metadata.
    """
    return {
        "value": data,
        "provenance": {
            "source": source,
            "source_url": source_url,
            "query_params": query_params or {},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "freshness": freshness,
            "is_mock": is_mock,
        },
    }
