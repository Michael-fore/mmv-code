-- MMV Real Estate Underwriting Platform — PostgreSQL DDL
-- All tables follow the pattern:
--   * Composite primary key per data source
--   * loaded_at TIMESTAMPTZ DEFAULT NOW() for audit trail
--   * source_hash TEXT for GCS content-hash dedup tracking
--   * Designed for INSERT ... ON CONFLICT DO UPDATE upserts
--
-- Target: Cloud SQL (PostgreSQL 15+) in project mmv-cloud

BEGIN;

-- ============================================================
-- USDA NASS: Agricultural land values by state and year
-- ============================================================
CREATE TABLE IF NOT EXISTS land_values (
    state               TEXT        NOT NULL,
    year                INTEGER     NOT NULL,
    value_per_acre      NUMERIC     NOT NULL,
    change_pct          NUMERIC,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (state, year)
);

-- ============================================================
-- USDA NASS: Cash rents (cropland & pasture) by state and year
-- ============================================================
CREATE TABLE IF NOT EXISTS cash_rents (
    state               TEXT        NOT NULL,
    year                INTEGER     NOT NULL,
    cropland_rent       NUMERIC     NOT NULL,
    pasture_rent        NUMERIC,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (state, year)
);

-- ============================================================
-- FRED: General economic time series (interest rates, farm income, etc.)
-- ============================================================
CREATE TABLE IF NOT EXISTS fred_series (
    series_id           TEXT        NOT NULL,
    date                DATE        NOT NULL,
    value               NUMERIC     NOT NULL,
    units               TEXT,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (series_id, date)
);

-- ============================================================
-- EIA: Electricity generation by state, year, and source
-- ============================================================
CREATE TABLE IF NOT EXISTS eia_generation (
    state               TEXT        NOT NULL,
    year                INTEGER     NOT NULL,
    source              TEXT        NOT NULL,
    generation_mwh      NUMERIC     NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (state, year, source)
);

-- ============================================================
-- NOAA: Monthly climate observations by state
-- ============================================================
CREATE TABLE IF NOT EXISTS noaa_climate (
    state               TEXT        NOT NULL,
    year                INTEGER     NOT NULL,
    month               INTEGER     NOT NULL CHECK (month BETWEEN 1 AND 12),
    avg_temp_f          NUMERIC,
    total_precip_inches NUMERIC,
    heating_degree_days NUMERIC,
    cooling_degree_days NUMERIC,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (state, year, month)
);

-- ============================================================
-- US Drought Monitor: Weekly drought percentages by state
-- ============================================================
CREATE TABLE IF NOT EXISTS drought_monitor (
    state               TEXT        NOT NULL,
    date                DATE        NOT NULL,
    none_pct            NUMERIC,
    d0_pct              NUMERIC,
    d1_pct              NUMERIC,
    d2_pct              NUMERIC,
    d3_pct              NUMERIC,
    d4_pct              NUMERIC,
    dominant_category   TEXT,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (state, date)
);

-- ============================================================
-- USDA FAS: Export data by commodity, year, and country
-- ============================================================
CREATE TABLE IF NOT EXISTS usda_exports (
    commodity           TEXT        NOT NULL,
    year                INTEGER     NOT NULL,
    country             TEXT        NOT NULL,
    volume_mt           NUMERIC,
    value_usd           NUMERIC,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (commodity, year, country)
);

-- ============================================================
-- USDA FSA: Conservation Reserve Program enrollment by state
-- ============================================================
CREATE TABLE IF NOT EXISTS crp_enrollment (
    state               TEXT        NOT NULL,
    year                INTEGER     NOT NULL,
    enrolled_acres      NUMERIC,
    annual_rental_payment NUMERIC,
    avg_cost_per_acre   NUMERIC,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (state, year)
);

-- ============================================================
-- SSURGO: Soil survey data by state, county, and map unit
-- ============================================================
CREATE TABLE IF NOT EXISTS ssurgo_soils (
    state               TEXT        NOT NULL,
    county              TEXT        NOT NULL,
    map_unit            TEXT        NOT NULL,
    soil_type           TEXT,
    drainage_class      TEXT,
    farmland_class      TEXT,
    slope_pct           NUMERIC,
    organic_matter_pct  NUMERIC,
    ph                  NUMERIC,
    cation_exchange     NUMERIC,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (state, county, map_unit)
);

-- ============================================================
-- Census Bureau: Population demographics by state and year
-- ============================================================
CREATE TABLE IF NOT EXISTS census_population (
    state               TEXT        NOT NULL,
    year                INTEGER     NOT NULL,
    total_population    INTEGER,
    rural_population    INTEGER,
    urban_population    INTEGER,
    median_age          NUMERIC,
    median_household_income NUMERIC,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (state, year)
);

-- ============================================================
-- FRED: Farm debt series (e.g. FARMDBT) — separate from
-- general fred_series for domain-specific queries
-- ============================================================
CREATE TABLE IF NOT EXISTS fred_farm_debt (
    series_id           TEXT        NOT NULL,
    date                DATE        NOT NULL,
    value               NUMERIC     NOT NULL,
    units               TEXT,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_hash         TEXT,
    PRIMARY KEY (series_id, date)
);

COMMIT;
