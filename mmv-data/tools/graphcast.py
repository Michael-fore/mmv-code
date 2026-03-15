"""GraphCast fetcher — Google DeepMind ML weather forecasts.

Source: GraphCast via ECMWF API and Google WeatherBench2 (GCS).
Docs:
  - https://deepmind.google/discover/blog/graphcast-ai-model-for-faster-and-more-accurate-global-weather-forecasting/
  - https://www.ecmwf.int/en/forecasts/dataset/graphcast
  - gs://weatherbench2  (WeatherBench2 dataset on Google Cloud Storage)

GraphCast provides 10-day global weather forecasts at 0.25° resolution using
a graph-neural-network architecture trained on 39 years of ERA5 reanalysis.
Key variables relevant to agricultural/real-estate underwriting:
  - 2-metre temperature
  - Total precipitation
  - 10-metre wind speed
  - Soil moisture (volumetric, layers 1-4)
  - Relative humidity
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from .provenance import tag_provenance
except ImportError:
    from provenance import tag_provenance

_ECMWF_API_URL = "https://api.ecmwf.int/v1/services/graphcast"
_GCS_BUCKET_URL = "gs://weatherbench2"


# ---------------------------------------------------------------------------
# Mock-data helpers — realistic Midwest US weather values
# ---------------------------------------------------------------------------

def _snap_to_grid(value: float, resolution: float = 0.25) -> float:
    """Snap a coordinate to the nearest 0.25° grid point."""
    return round(round(value / resolution) * resolution, 2)


def _mock_forecast_day(
    base_date: date,
    day_offset: int,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    """Generate one day of deterministic mock forecast data.

    Values are seeded from lat/lon/offset so the same inputs always
    produce the same outputs — no randomness involved.
    """
    seed = abs(hash((lat, lon, day_offset))) % 1000 / 1000.0
    forecast_date = base_date + timedelta(days=day_offset)
    month = forecast_date.month

    # Seasonal temperature curve (°C) for ~40°N Midwest US
    seasonal_base = 10.0 + 15.0 * math.sin((month - 4) * math.pi / 6)
    temp_2m = round(seasonal_base + (seed - 0.5) * 8.0, 1)
    temp_2m_max = round(temp_2m + 3.0 + seed * 4.0, 1)
    temp_2m_min = round(temp_2m - 3.0 - seed * 4.0, 1)

    precip_mm = round(max(0.0, (seed - 0.4) * 12.0), 1)
    wind_speed_ms = round(2.0 + seed * 8.0, 1)
    relative_humidity_pct = round(40.0 + seed * 45.0, 1)
    soil_moisture_m3m3 = round(0.20 + seed * 0.15, 3)

    return {
        "date": forecast_date.isoformat(),
        "lead_time_hours": day_offset * 24,
        "temperature_2m_c": temp_2m,
        "temperature_2m_max_c": temp_2m_max,
        "temperature_2m_min_c": temp_2m_min,
        "total_precipitation_mm": precip_mm,
        "wind_speed_10m_ms": wind_speed_ms,
        "relative_humidity_pct": relative_humidity_pct,
        "soil_moisture_0_7cm_m3m3": soil_moisture_m3m3,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_graphcast_forecast(
    lat: float,
    lon: float,
    forecast_date: str | date | None = None,
) -> dict[str, Any]:
    """Fetch a 10-day GraphCast weather forecast for a point location.

    Args:
        lat: Latitude in decimal degrees (WGS-84).
        lon: Longitude in decimal degrees (WGS-84).
        forecast_date: Forecast initialization date (ISO-8601 string or
            ``date`` object).  Defaults to today (UTC).

    Returns:
        Provenance-wrapped dict with a 10-day daily forecast array containing
        temperature, precipitation, wind, humidity, and soil-moisture fields.
    """
    if forecast_date is None:
        base = date.today()
    elif isinstance(forecast_date, str):
        base = date.fromisoformat(forecast_date)
    else:
        base = forecast_date

    snapped_lat = _snap_to_grid(lat)
    snapped_lon = _snap_to_grid(lon)

    params = {
        "lat": snapped_lat,
        "lon": snapped_lon,
        "init_date": base.isoformat(),
        "model": "graphcast",
        "resolution_deg": 0.25,
        "variables": [
            "2m_temperature",
            "total_precipitation",
            "10m_wind_speed",
            "relative_humidity",
            "soil_moisture_level_1",
        ],
    }

    daily = [
        _mock_forecast_day(base, offset, snapped_lat, snapped_lon)
        for offset in range(10)
    ]

    mock_data: dict[str, Any] = {
        "model": "GraphCast",
        "model_version": "GraphCast-ERA5 (2023)",
        "grid_resolution_deg": 0.25,
        "location": {
            "requested_lat": lat,
            "requested_lon": lon,
            "snapped_lat": snapped_lat,
            "snapped_lon": snapped_lon,
        },
        "init_date": base.isoformat(),
        "forecast_horizon_days": 10,
        "daily": daily,
    }

    return tag_provenance(
        mock_data,
        source="Google DeepMind GraphCast (via ECMWF / WeatherBench2)",
        source_url=_ECMWF_API_URL,
        query_params=params,
        freshness=f"10-day forecast initialized {base.isoformat()}",
        is_mock=True,
    )


def fetch_graphcast_historical(
    lat: float,
    lon: float,
    start_date: str | date,
    end_date: str | date,
) -> dict[str, Any]:
    """Fetch GraphCast historical hindcasts for a point location and date range.

    Hindcasts use the same model architecture re-run over ERA5 reanalysis
    inputs, useful for backtesting underwriting models against past weather.

    Args:
        lat: Latitude in decimal degrees (WGS-84).
        lon: Longitude in decimal degrees (WGS-84).
        start_date: Start of range (inclusive), ISO-8601 string or ``date``.
        end_date: End of range (inclusive), ISO-8601 string or ``date``.

    Returns:
        Provenance-wrapped dict with daily hindcast records.

    Raises:
        ValueError: If the date range exceeds 365 days or start > end.
    """
    if isinstance(start_date, str):
        start = date.fromisoformat(start_date)
    else:
        start = start_date
    if isinstance(end_date, str):
        end = date.fromisoformat(end_date)
    else:
        end = end_date

    if start > end:
        raise ValueError(f"start_date ({start}) must be <= end_date ({end})")
    if (end - start).days > 365:
        raise ValueError("Date range must not exceed 365 days")

    snapped_lat = _snap_to_grid(lat)
    snapped_lon = _snap_to_grid(lon)

    params = {
        "lat": snapped_lat,
        "lon": snapped_lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "model": "graphcast",
        "dataset": "weatherbench2",
        "resolution_deg": 0.25,
        "variables": [
            "2m_temperature",
            "total_precipitation",
            "10m_wind_speed",
            "relative_humidity",
            "soil_moisture_level_1",
        ],
    }

    num_days = (end - start).days + 1
    daily = [
        _mock_forecast_day(start, offset, snapped_lat, snapped_lon)
        for offset in range(num_days)
    ]
    # Historical records don't carry lead_time; replace with source tag
    for record in daily:
        record.pop("lead_time_hours", None)
        record["source"] = "ERA5 reanalysis hindcast"

    mock_data: dict[str, Any] = {
        "model": "GraphCast",
        "model_version": "GraphCast-ERA5 (2023)",
        "dataset": "WeatherBench2",
        "grid_resolution_deg": 0.25,
        "location": {
            "requested_lat": lat,
            "requested_lon": lon,
            "snapped_lat": snapped_lat,
            "snapped_lon": snapped_lon,
        },
        "date_range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "num_days": num_days,
        },
        "daily": daily,
    }

    return tag_provenance(
        mock_data,
        source="Google DeepMind GraphCast — WeatherBench2 hindcasts",
        source_url=_GCS_BUCKET_URL,
        query_params=params,
        freshness=f"hindcast {start.isoformat()} to {end.isoformat()}",
        is_mock=True,
    )


if __name__ == "__main__":
    # Demo: 10-day forecast for central Iowa (41.88°N, 93.63°W)
    print("=== GraphCast 10-Day Forecast (Central Iowa) ===")
    forecast = fetch_graphcast_forecast(41.88, -93.63)
    print(json.dumps(forecast, indent=2))

    print("\n=== GraphCast Historical Hindcast (Central Iowa, 7 days) ===")
    hist = fetch_graphcast_historical(
        41.88, -93.63, "2024-06-01", "2024-06-07"
    )
    print(json.dumps(hist, indent=2))
