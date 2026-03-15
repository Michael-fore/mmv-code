"""Agent task: Fetch USDA crop production data for a state.

This task wraps the ``mmv-data`` crop production fetcher and persists the
provenance-tagged result to a JSON file under ``/tmp/mmv_initial_fetch/``
so that downstream tasks (underwriting, reporting) can consume it without
re-fetching.

The module is designed to be picked up by the MMV agent executor via its
``TASK_META`` descriptor and ``run()`` entry point.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Ensure the sibling mmv-data package is importable when running inside the
# mono-repo checkout (mmv-code/).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]  # mmv-code/
sys.path.insert(0, str(_REPO_ROOT))

from mmv_data.tools.crop_production import fetch_crop_production  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task metadata — consumed by the agent executor for discovery / routing.
# ---------------------------------------------------------------------------

TASK_META: dict[str, Any] = {
    "name": "fetch_crop_production",
    "description": (
        "Fetch annual crop production data (CORN, WHEAT, COTTON, SOYBEANS) "
        "for a US state from USDA NASS QuickStats and persist to disk."
    ),
    "parameters": {
        "state": {
            "type": "string",
            "description": "Two-letter US state abbreviation",
            "default": "TX",
        },
    },
    "output_dir": "/tmp/mmv_initial_fetch",
}

OUTPUT_DIR = Path(TASK_META["output_dir"])


def run(state: str = "TX") -> dict[str, Any]:
    """Execute the crop production fetch task.

    Args:
        state: Two-letter US state abbreviation (default ``"TX"``).

    Returns:
        The provenance-wrapped crop production payload (same dict that is
        persisted to disk).
    """
    logger.info("Task fetch_crop_production: fetching data for %s", state)

    result = fetch_crop_production(state)

    # Persist to /tmp/mmv_initial_fetch/crop_production_{state}.json
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"crop_production_{state.upper()}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    record_count = len(result.get("value", []))
    is_mock = result.get("provenance", {}).get("is_mock", False)
    logger.info(
        "Task fetch_crop_production: wrote %d records to %s (mock=%s)",
        record_count,
        out_path,
        is_mock,
    )

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    target_state = sys.argv[1] if len(sys.argv) > 1 else "TX"
    output = run(target_state)

    print(json.dumps(output, indent=2))
    print(
        f"\nSaved to {OUTPUT_DIR / f'crop_production_{target_state.upper()}.json'}"
    )
