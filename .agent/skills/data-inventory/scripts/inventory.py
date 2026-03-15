"""
Inventory all available MMV data sources.

Reports table name, record count, latest data point, and date range
for each dataset — whether from cached JSON or live fetchers.

Usage:
    python inventory.py
    python inventory.py --json
"""

import json
import os
from datetime import datetime


CACHE_DIR = "/tmp/mmv_initial_fetch"


def inventory() -> list[dict]:
    """
    Scan all known data locations and return a summary per dataset.

    Returns list of dicts with: name, source, records, date_range, latest_value, last_fetched
    """
    results = []

    # Check cached JSON files
    if os.path.isdir(CACHE_DIR):
        # USDA
        usda_path = os.path.join(CACHE_DIR, "usda.json")
        if os.path.exists(usda_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(usda_path)).strftime("%Y-%m-%d %H:%M")
            with open(usda_path) as f:
                usda = json.load(f)

            for key, rows in usda.items():
                if not rows:
                    continue
                years = [r.get("year", 0) for r in rows]
                results.append({
                    "name": key,
                    "source": "USDA NASS",
                    "records": len(rows),
                    "date_range": f"{min(years)}-{max(years)}" if years else "—",
                    "latest_value": _format_latest_usda(key, rows),
                    "last_fetched": mtime,
                })

        # FRED
        fred_path = os.path.join(CACHE_DIR, "fred.json")
        if os.path.exists(fred_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(fred_path)).strftime("%Y-%m-%d %H:%M")
            with open(fred_path) as f:
                fred = json.load(f)

            for series_id, rows in fred.items():
                if not rows:
                    results.append({
                        "name": f"fred_{series_id}",
                        "source": "FRED",
                        "records": 0,
                        "date_range": "—",
                        "latest_value": "no data",
                        "last_fetched": mtime,
                    })
                    continue
                dates = [r["observation_date"] for r in rows]
                latest = rows[-1]
                results.append({
                    "name": f"fred_{series_id}",
                    "source": "FRED",
                    "records": len(rows),
                    "date_range": f"{min(dates)[:10]} to {max(dates)[:10]}",
                    "latest_value": f"{latest['value']}",
                    "last_fetched": mtime,
                })

        # EIA
        eia_path = os.path.join(CACHE_DIR, "eia.json")
        if os.path.exists(eia_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(eia_path)).strftime("%Y-%m-%d %H:%M")
            with open(eia_path) as f:
                eia = json.load(f)

            for key, rows in eia.items():
                if not rows:
                    continue
                periods = [r.get("period", "") for r in rows]
                latest = rows[-1]
                results.append({
                    "name": key,
                    "source": "EIA",
                    "records": len(rows),
                    "date_range": f"{min(periods)}-{max(periods)}" if periods else "—",
                    "latest_value": f"{latest.get('generation_mwh', 0):,.0f} MWh" if "generation_mwh" in latest else str(latest),
                    "last_fetched": mtime,
                })

        # Underwriting results
        uw_path = os.path.join(CACHE_DIR, "underwriting_TX.json")
        if os.path.exists(uw_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(uw_path)).strftime("%Y-%m-%d %H:%M")
            with open(uw_path) as f:
                uw = json.load(f)
            thesis = uw.get("summary", {}).get("thesis", "?")
            results.append({
                "name": "underwriting_TX",
                "source": "mmv-underwriting",
                "records": len(uw.get("sections", {})),
                "date_range": "—",
                "latest_value": f"Thesis: {thesis}",
                "last_fetched": mtime,
            })

    if not results:
        results.append({
            "name": "(none)",
            "source": "—",
            "records": 0,
            "date_range": "—",
            "latest_value": "No data fetched yet. Run the fetchers first.",
            "last_fetched": "—",
        })

    return results


def _format_latest_usda(key: str, rows: list[dict]) -> str:
    latest = rows[-1]
    if "value_per_acre" in latest:
        return f"${latest['value_per_acre']:,}/acre ({latest.get('year', '?')})"
    if "rent_per_acre" in latest:
        return f"${latest['rent_per_acre']:.0f}/acre ({latest.get('year', '?')})"
    if "production" in latest:
        return f"{latest['production']:,} {latest.get('unit', '')} ({latest.get('year', '?')})"
    return str(latest)


def print_table(datasets: list[dict]) -> None:
    """Print a formatted table of all datasets."""
    print(f"\n{'Dataset':<28} {'Source':<14} {'Records':>8}   {'Date Range':<24} {'Latest Value':<32} {'Last Fetched'}")
    print("─" * 130)
    for d in datasets:
        print(
            f"{d['name']:<28} {d['source']:<14} {d['records']:>8}   "
            f"{d['date_range']:<24} {d['latest_value']:<32} {d['last_fetched']}"
        )
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inventory available MMV data")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    datasets = inventory()

    if args.json:
        print(json.dumps(datasets, indent=2))
    else:
        print_table(datasets)
