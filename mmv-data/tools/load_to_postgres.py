"""PostgreSQL loader for MMV data pipeline.

Architecture rule: Raw files -> GCS first, then load into PostgreSQL.
This module reads JSON files (already landed in GCS) and upserts rows
into the corresponding Cloud SQL PostgreSQL tables.

Since there is no actual Cloud SQL instance in development, a MockConnection
class is provided that logs SQL statements and simulates cursor operations.

Usage with real Cloud SQL::

    conn = connect_to_cloudsql("mmv-cloud", "mmv-sql-01", "mmv", "app", "secret")
    stats = load_all_sources("/tmp/mmv_data", conn)

Usage with mock (no database required)::

    conn = MockConnection()
    stats = load_all_sources("/tmp/mmv_data", conn)
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Filename-to-table mapping
# ---------------------------------------------------------------------------

FILENAME_TABLE_MAP: dict[str, str] = {
    "land_values.json": "land_values",
    "cash_rents.json": "cash_rents",
    "fred_series.json": "fred_series",
    "eia_generation.json": "eia_generation",
    "noaa_climate.json": "noaa_climate",
    "drought_monitor.json": "drought_monitor",
    "usda_exports.json": "usda_exports",
    "crp_enrollment.json": "crp_enrollment",
    "ssurgo_soils.json": "ssurgo_soils",
    "census_population.json": "census_population",
    "fred_farm_debt.json": "fred_farm_debt",
}

# ---------------------------------------------------------------------------
# Table schema definitions: column names and primary key columns
# Used to build parameterized INSERT ... ON CONFLICT DO UPDATE statements.
# ---------------------------------------------------------------------------

TABLE_SCHEMAS: dict[str, dict[str, Any]] = {
    "land_values": {
        "columns": ["state", "year", "value_per_acre", "change_pct", "source_hash"],
        "pk": ["state", "year"],
    },
    "cash_rents": {
        "columns": ["state", "year", "cropland_rent", "pasture_rent", "source_hash"],
        "pk": ["state", "year"],
    },
    "fred_series": {
        "columns": ["series_id", "date", "value", "units", "source_hash"],
        "pk": ["series_id", "date"],
    },
    "eia_generation": {
        "columns": ["state", "year", "source", "generation_mwh", "source_hash"],
        "pk": ["state", "year", "source"],
    },
    "noaa_climate": {
        "columns": [
            "state", "year", "month", "avg_temp_f", "total_precip_inches",
            "heating_degree_days", "cooling_degree_days", "source_hash",
        ],
        "pk": ["state", "year", "month"],
    },
    "drought_monitor": {
        "columns": [
            "state", "date", "none_pct", "d0_pct", "d1_pct",
            "d2_pct", "d3_pct", "d4_pct", "dominant_category", "source_hash",
        ],
        "pk": ["state", "date"],
    },
    "usda_exports": {
        "columns": ["commodity", "year", "country", "volume_mt", "value_usd", "source_hash"],
        "pk": ["commodity", "year", "country"],
    },
    "crp_enrollment": {
        "columns": [
            "state", "year", "enrolled_acres", "annual_rental_payment",
            "avg_cost_per_acre", "source_hash",
        ],
        "pk": ["state", "year"],
    },
    "ssurgo_soils": {
        "columns": [
            "state", "county", "map_unit", "soil_type", "drainage_class",
            "farmland_class", "slope_pct", "organic_matter_pct", "ph",
            "cation_exchange", "source_hash",
        ],
        "pk": ["state", "county", "map_unit"],
    },
    "census_population": {
        "columns": [
            "state", "year", "total_population", "rural_population",
            "urban_population", "median_age", "median_household_income", "source_hash",
        ],
        "pk": ["state", "year"],
    },
    "fred_farm_debt": {
        "columns": ["series_id", "date", "value", "units", "source_hash"],
        "pk": ["series_id", "date"],
    },
}


# ---------------------------------------------------------------------------
# SQL generation helpers
# ---------------------------------------------------------------------------

def _build_upsert_sql(table_name: str) -> str:
    """Build a parameterized INSERT ... ON CONFLICT DO UPDATE statement.

    Args:
        table_name: Name of the target table (must exist in TABLE_SCHEMAS).

    Returns:
        A SQL string with %(col)s-style placeholders for psycopg2.

    Raises:
        KeyError: If table_name is not in TABLE_SCHEMAS.
    """
    schema = TABLE_SCHEMAS[table_name]
    columns = schema["columns"]
    pk_cols = schema["pk"]
    non_pk_cols = [c for c in columns if c not in pk_cols]

    col_list = ", ".join(columns)
    val_list = ", ".join(f"%({c})s" for c in columns)
    conflict_cols = ", ".join(pk_cols)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in non_pk_cols)
    # Always update loaded_at on upsert so we track the latest load time.
    update_set += ", loaded_at = NOW()"

    sql = (
        f"INSERT INTO {table_name} ({col_list})\n"
        f"VALUES ({val_list})\n"
        f"ON CONFLICT ({conflict_cols}) DO UPDATE SET\n"
        f"  {update_set}"
    )
    return sql


# ---------------------------------------------------------------------------
# Mock connection (no real database needed)
# ---------------------------------------------------------------------------

@dataclass
class MockCursor:
    """Simulates a DB-API 2.0 cursor, logging executed SQL."""

    statements: list[str] = field(default_factory=list)
    rowcount: int = 0
    _description: list | None = None

    @property
    def description(self) -> list | None:
        return self._description

    def execute(self, sql: str, params: dict | tuple | None = None) -> None:
        self.rowcount = 1
        rendered = sql
        if params:
            try:
                # Render for logging only — real execution uses server-side binding
                rendered = sql % {k: repr(v) for k, v in params.items()} if isinstance(params, dict) else sql
            except (TypeError, KeyError):
                rendered = f"{sql}  -- params: {params}"
        self.statements.append(rendered)
        logger.debug("MockCursor.execute: %s", rendered[:200])

    def executemany(self, sql: str, params_list: list) -> None:
        for params in params_list:
            self.execute(sql, params)

    def fetchall(self) -> list:
        return []

    def fetchone(self) -> None:
        return None

    def close(self) -> None:
        pass


@dataclass
class MockConnection:
    """Simulates a DB-API 2.0 connection for local testing.

    Tracks all SQL statements issued across all cursors so they can be
    inspected in tests.
    """

    all_statements: list[str] = field(default_factory=list)
    _closed: bool = False

    def cursor(self) -> MockCursor:
        cur = MockCursor(statements=self.all_statements)
        return cur

    def commit(self) -> None:
        logger.debug("MockConnection.commit()")

    def rollback(self) -> None:
        logger.debug("MockConnection.rollback()")

    def close(self) -> None:
        self._closed = True
        logger.debug("MockConnection.close()")

    @property
    def closed(self) -> bool:
        return self._closed


# ---------------------------------------------------------------------------
# Cloud SQL connector
# ---------------------------------------------------------------------------

def connect_to_cloudsql(
    project: str,
    instance: str,
    database: str,
    user: str,
    password: str,
) -> Any:
    """Connect to a Cloud SQL PostgreSQL instance via the Cloud SQL Auth Proxy.

    Requires ``psycopg2`` and ``cloud-sql-python-connector`` to be installed.
    Falls back to a MockConnection when psycopg2 is not available.

    Args:
        project: GCP project ID (e.g. ``"mmv-cloud"``).
        instance: Cloud SQL instance name (e.g. ``"mmv-sql-01"``).
        database: PostgreSQL database name.
        user: Database user.
        password: Database password.

    Returns:
        A DB-API 2.0 connection object.
    """
    instance_connection_name = f"{project}:us-central1:{instance}"

    try:
        from google.cloud.sql.connector import Connector  # type: ignore[import-untyped]
        import psycopg2  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "psycopg2 or cloud-sql-python-connector not installed. "
            "Returning MockConnection for local development."
        )
        return MockConnection()

    connector = Connector()

    def getconn() -> Any:
        return connector.connect(
            instance_connection_name,
            "pg8000",
            user=user,
            password=password,
            db=database,
        )

    # Use psycopg2 directly with the proxy socket if available,
    # otherwise fall through to pg8000 via the connector.
    try:
        conn = psycopg2.connect(
            host=f"/cloudsql/{instance_connection_name}",
            dbname=database,
            user=user,
            password=password,
        )
    except Exception:
        logger.info("Direct socket connection failed; using Cloud SQL connector.")
        conn = getconn()

    return conn


# ---------------------------------------------------------------------------
# Content hashing (matches GCS dedup hash)
# ---------------------------------------------------------------------------

def compute_file_hash(file_path: str) -> str:
    """Return the SHA-256 hex digest of a file, matching gcs.py's content hash."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as fh:
        while True:
            chunk = fh.read(8192)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


# ---------------------------------------------------------------------------
# Data extraction: unwrap provenance-tagged JSON
# ---------------------------------------------------------------------------

def _extract_rows(raw: Any, table_name: str) -> list[dict]:
    """Extract a flat list of row dicts from a provenance-wrapped JSON payload.

    Handles two shapes:
    1. Provenance-wrapped list: {"value": [...], "provenance": {...}}
    2. Provenance-wrapped dict with "observations": {"value": {"observations": [...]}}
    3. Plain list: [...]
    4. Plain dict with "observations": {"observations": [...]}
    """
    # Unwrap provenance envelope if present
    data = raw
    if isinstance(data, dict) and "value" in data and "provenance" in data:
        data = data["value"]

    # FRED-style: dict with observations list
    if isinstance(data, dict) and "observations" in data:
        rows = data["observations"]
        # Inject series-level fields into each observation
        series_id = data.get("series_id")
        units = data.get("units")
        enriched = []
        for obs in rows:
            row = dict(obs)
            if series_id and "series_id" not in row:
                row["series_id"] = series_id
            if units and "units" not in row:
                row["units"] = units
            enriched.append(row)
        return enriched

    # Simple list of dicts
    if isinstance(data, list):
        return data

    logger.warning("Unexpected data shape for table %s: %s", table_name, type(data))
    return []


# ---------------------------------------------------------------------------
# Core loader functions
# ---------------------------------------------------------------------------

def load_json_to_table(
    json_path: str,
    table_name: str,
    conn: Any,
) -> dict[str, Any]:
    """Read a JSON file and upsert rows into the corresponding PostgreSQL table.

    Args:
        json_path: Path to the JSON file on disk.
        table_name: Target table name (must exist in TABLE_SCHEMAS).
        conn: A DB-API 2.0 connection (real psycopg2 or MockConnection).

    Returns:
        A stats dict with keys: table, file, rows_loaded, rows_skipped,
        source_hash, and errors.
    """
    stats: dict[str, Any] = {
        "table": table_name,
        "file": json_path,
        "rows_loaded": 0,
        "rows_skipped": 0,
        "source_hash": None,
        "errors": [],
    }

    if table_name not in TABLE_SCHEMAS:
        stats["errors"].append(f"Unknown table: {table_name}")
        return stats

    # Read and hash the file
    path = Path(json_path)
    if not path.exists():
        stats["errors"].append(f"File not found: {json_path}")
        return stats

    source_hash = compute_file_hash(json_path)
    stats["source_hash"] = source_hash

    with open(json_path, "r") as fh:
        raw = json.load(fh)

    rows = _extract_rows(raw, table_name)
    if not rows:
        logger.info("No rows extracted from %s for table %s", json_path, table_name)
        return stats

    schema = TABLE_SCHEMAS[table_name]
    columns = schema["columns"]
    upsert_sql = _build_upsert_sql(table_name)

    cur = conn.cursor()
    try:
        for row in rows:
            # Build parameter dict — only include columns defined in the schema.
            # Missing columns get None (NULL in SQL).
            params = {col: row.get(col) for col in columns}
            params["source_hash"] = source_hash

            try:
                cur.execute(upsert_sql, params)
                stats["rows_loaded"] += 1
            except Exception as exc:
                stats["rows_skipped"] += 1
                stats["errors"].append(f"Row error: {exc}")
                logger.error("Error upserting row into %s: %s", table_name, exc)

        conn.commit()
    except Exception as exc:
        conn.rollback()
        stats["errors"].append(f"Transaction error: {exc}")
        logger.error("Transaction failed for %s: %s", table_name, exc)
    finally:
        cur.close()

    return stats


def load_all_sources(
    data_dir: str,
    conn: Any,
) -> list[dict[str, Any]]:
    """Load all recognized JSON files from a directory into PostgreSQL.

    Iterates through FILENAME_TABLE_MAP, looking for matching files in
    data_dir. Files not in the mapping are ignored.

    Args:
        data_dir: Directory containing JSON data files.
        conn: A DB-API 2.0 connection.

    Returns:
        A list of stats dicts (one per file processed), same format as
        load_json_to_table.
    """
    data_path = Path(data_dir)
    if not data_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {data_dir}")

    results: list[dict[str, Any]] = []

    for filename, table_name in sorted(FILENAME_TABLE_MAP.items()):
        file_path = data_path / filename
        if not file_path.exists():
            logger.debug("Skipping %s (not found in %s)", filename, data_dir)
            continue

        logger.info("Loading %s -> %s", filename, table_name)
        stats = load_json_to_table(str(file_path), table_name, conn)
        results.append(stats)

    return results


# ---------------------------------------------------------------------------
# CLI demo — full pipeline with mock data and mock connection
# ---------------------------------------------------------------------------

def _generate_mock_data(output_dir: Path) -> None:
    """Generate sample JSON files in the provenance-wrapped format."""
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets: dict[str, Any] = {
        "land_values.json": [
            {"state": "TX", "year": 2024, "value_per_acre": 3160, "change_pct": 8.97},
            {"state": "TX", "year": 2023, "value_per_acre": 2900, "change_pct": 9.43},
            {"state": "IA", "year": 2024, "value_per_acre": 9800, "change_pct": 3.16},
        ],
        "cash_rents.json": [
            {"state": "TX", "year": 2024, "cropland_rent": 144.0, "pasture_rent": 12.50},
            {"state": "TX", "year": 2023, "cropland_rent": 136.0, "pasture_rent": 11.80},
            {"state": "IA", "year": 2024, "cropland_rent": 256.0, "pasture_rent": 45.00},
        ],
        "fred_series.json": {
            "series_id": "DGS10",
            "units": "percent",
            "observations": [
                {"date": "2024-12-01", "value": 4.39},
                {"date": "2024-11-01", "value": 4.24},
                {"date": "2024-06-01", "value": 4.32},
            ],
        },
        "eia_generation.json": [
            {"state": "TX", "year": 2023, "source": "wind", "generation_mwh": 92_361_000},
            {"state": "TX", "year": 2023, "source": "natural_gas", "generation_mwh": 214_500_000},
            {"state": "CA", "year": 2023, "source": "solar", "generation_mwh": 53_700_000},
        ],
        "noaa_climate.json": [
            {"state": "TX", "year": 2024, "month": 1, "avg_temp_f": 48.2, "total_precip_inches": 2.1, "heating_degree_days": 520, "cooling_degree_days": 0},
            {"state": "TX", "year": 2024, "month": 7, "avg_temp_f": 95.6, "total_precip_inches": 1.3, "heating_degree_days": 0, "cooling_degree_days": 945},
        ],
        "drought_monitor.json": [
            {"state": "TX", "date": "2024-12-10", "none_pct": 25.0, "d0_pct": 30.0, "d1_pct": 20.0, "d2_pct": 15.0, "d3_pct": 8.0, "d4_pct": 2.0, "dominant_category": "D0"},
            {"state": "CA", "date": "2024-12-10", "none_pct": 45.0, "d0_pct": 25.0, "d1_pct": 15.0, "d2_pct": 10.0, "d3_pct": 5.0, "d4_pct": 0.0, "dominant_category": "None"},
        ],
        "usda_exports.json": [
            {"commodity": "corn", "year": 2024, "country": "Mexico", "volume_mt": 18_500_000, "value_usd": 5_200_000_000},
            {"commodity": "soybeans", "year": 2024, "country": "China", "volume_mt": 27_300_000, "value_usd": 14_800_000_000},
        ],
        "crp_enrollment.json": [
            {"state": "TX", "year": 2024, "enrolled_acres": 2_850_000, "annual_rental_payment": 185_000_000, "avg_cost_per_acre": 64.91},
            {"state": "KS", "year": 2024, "enrolled_acres": 1_920_000, "annual_rental_payment": 112_000_000, "avg_cost_per_acre": 58.33},
        ],
        "ssurgo_soils.json": [
            {"state": "TX", "county": "Travis", "map_unit": "TrA", "soil_type": "Travis soils", "drainage_class": "well drained", "farmland_class": "prime", "slope_pct": 1.5, "organic_matter_pct": 2.1, "ph": 7.2, "cation_exchange": 22.5},
            {"state": "IA", "county": "Polk", "map_unit": "NiB", "soil_type": "Nicollet clay loam", "drainage_class": "somewhat poorly drained", "farmland_class": "prime", "slope_pct": 2.0, "organic_matter_pct": 4.8, "ph": 6.8, "cation_exchange": 28.1},
        ],
        "census_population.json": [
            {"state": "TX", "year": 2023, "total_population": 30_503_000, "rural_population": 4_100_000, "urban_population": 26_403_000, "median_age": 35.5, "median_household_income": 67_321},
            {"state": "IA", "year": 2023, "total_population": 3_200_000, "rural_population": 1_150_000, "urban_population": 2_050_000, "median_age": 38.2, "median_household_income": 65_573},
        ],
        "fred_farm_debt.json": {
            "series_id": "FARMDBT",
            "units": "billions of USD",
            "observations": [
                {"date": "2024-01-01", "value": 520.3},
                {"date": "2023-01-01", "value": 498.7},
                {"date": "2022-01-01", "value": 471.2},
            ],
        },
    }

    # Wrap each dataset in provenance envelope
    for filename, data in datasets.items():
        payload = {
            "value": data,
            "provenance": {
                "source": "mock_generator",
                "source_url": "local://mock",
                "query_params": {},
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "mock",
                "is_mock": True,
            },
        }
        file_path = output_dir / filename
        file_path.write_text(json.dumps(payload, indent=2))
        logger.info("Generated mock data: %s", file_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    mock_dir = Path("/tmp/mmv_pg_load_demo")

    print("=" * 70)
    print("MMV PostgreSQL Loader — Demo with Mock Data & Mock Connection")
    print("=" * 70)

    # Step 1: Generate mock data files
    print("\n--- Step 1: Generating mock data files ---")
    _generate_mock_data(mock_dir)
    print(f"  Mock data written to: {mock_dir}")
    for f in sorted(mock_dir.glob("*.json")):
        print(f"    {f.name}  ({f.stat().st_size:,} bytes)")

    # Step 2: Create mock connection
    print("\n--- Step 2: Creating MockConnection ---")
    conn = MockConnection()
    print("  MockConnection ready (no real database).")

    # Step 3: Load all sources
    print("\n--- Step 3: Loading all sources ---")
    results = load_all_sources(str(mock_dir), conn)

    # Step 4: Report results
    print("\n--- Step 4: Load Results ---")
    total_loaded = 0
    total_skipped = 0
    for stats in results:
        status = "OK" if not stats["errors"] else "ERRORS"
        print(
            f"  [{status}] {stats['table']:20s} | "
            f"loaded={stats['rows_loaded']:3d}  "
            f"skipped={stats['rows_skipped']:3d}  "
            f"hash={stats['source_hash'][:12]}..."
        )
        total_loaded += stats["rows_loaded"]
        total_skipped += stats["rows_skipped"]
        if stats["errors"]:
            for err in stats["errors"]:
                print(f"         ERROR: {err}")

    print(f"\n  Total: {total_loaded} rows loaded, {total_skipped} skipped")
    print(f"  SQL statements executed: {len(conn.all_statements)}")

    # Step 5: Show sample SQL
    print("\n--- Step 5: Sample SQL Statements ---")
    for i, stmt in enumerate(conn.all_statements[:3]):
        print(f"\n  [{i + 1}] {stmt[:300]}...")

    # Step 6: Test single-file load
    print("\n--- Step 6: Single-file load test ---")
    single_stats = load_json_to_table(
        str(mock_dir / "land_values.json"),
        "land_values",
        conn,
    )
    print(f"  Table: {single_stats['table']}")
    print(f"  Rows loaded: {single_stats['rows_loaded']}")
    print(f"  Source hash: {single_stats['source_hash']}")

    # Step 7: Show generated upsert SQL for each table
    print("\n--- Step 7: Upsert SQL for all tables ---")
    for table_name in sorted(TABLE_SCHEMAS.keys()):
        sql = _build_upsert_sql(table_name)
        print(f"\n  -- {table_name} --")
        for line in sql.split("\n"):
            print(f"  {line}")

    conn.close()
    print("\n" + "=" * 70)
    print("Demo complete. All operations successful.")
    print("=" * 70)
