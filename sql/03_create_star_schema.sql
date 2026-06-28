-- 03_create_star_schema.sql
-- Project: Actuarial Motor Insurance Risk Analysis
-- Purpose:
--   Create the dimensional/star-schema warehouse tables in DuckDB.
--
-- Notes:
--   This script creates empty warehouse tables only.
--   The next script will populate them from the staging tables.

-- ============================================================
-- 1. Create warehouse schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ============================================================
-- 2. Drop tables so script can be rerun during development
--    Drop fact tables before dimensions because facts depend on dims.
-- ============================================================

DROP TABLE IF EXISTS warehouse.fact_inflation_scenario;
DROP TABLE IF EXISTS warehouse.fact_economic_assumption;
DROP TABLE IF EXISTS warehouse.fact_claim;
DROP TABLE IF EXISTS warehouse.fact_policy_exposure;

DROP TABLE IF EXISTS warehouse.dim_economic_scenario;
DROP TABLE IF EXISTS warehouse.dim_region;
DROP TABLE IF EXISTS warehouse.dim_driver;
DROP TABLE IF EXISTS warehouse.dim_vehicle;
DROP TABLE IF EXISTS warehouse.dim_policy;

-- ============================================================
-- 3. Dimension tables
-- ============================================================

CREATE TABLE warehouse.dim_policy (
    policy_key INTEGER PRIMARY KEY,
    policy_id BIGINT NOT NULL UNIQUE,
    bonus_malus INTEGER NOT NULL
);

CREATE TABLE warehouse.dim_vehicle (
    vehicle_key INTEGER PRIMARY KEY,
    vehicle_power INTEGER NOT NULL,
    vehicle_age INTEGER NOT NULL,
    vehicle_brand VARCHAR NOT NULL,
    vehicle_gas VARCHAR NOT NULL
);

CREATE TABLE warehouse.dim_driver (
    driver_key INTEGER PRIMARY KEY,
    driver_age INTEGER NOT NULL
);

CREATE TABLE warehouse.dim_region (
    region_key INTEGER PRIMARY KEY,
    area_code VARCHAR NOT NULL,
    region_code VARCHAR NOT NULL,
    density INTEGER NOT NULL
);

CREATE TABLE warehouse.dim_economic_scenario (
    scenario_key INTEGER PRIMARY KEY,
    scenario_id VARCHAR NOT NULL UNIQUE,
    scenario_name VARCHAR NOT NULL
);

-- ============================================================
-- 4. Fact tables
-- ============================================================

-- Grain: one row per policy exposure record from freMTPL2freq
CREATE TABLE warehouse.fact_policy_exposure (
    policy_exposure_key INTEGER PRIMARY KEY,

    policy_key INTEGER NOT NULL,
    vehicle_key INTEGER NOT NULL,
    driver_key INTEGER NOT NULL,
    region_key INTEGER NOT NULL,

    exposure DOUBLE NOT NULL,
    claim_count INTEGER NOT NULL,

    FOREIGN KEY (policy_key) REFERENCES warehouse.dim_policy(policy_key),
    FOREIGN KEY (vehicle_key) REFERENCES warehouse.dim_vehicle(vehicle_key),
    FOREIGN KEY (driver_key) REFERENCES warehouse.dim_driver(driver_key),
    FOREIGN KEY (region_key) REFERENCES warehouse.dim_region(region_key)
);

-- Grain: one row per claim payment row from freMTPL2sev
CREATE TABLE warehouse.fact_claim (
    claim_key INTEGER PRIMARY KEY,

    policy_key INTEGER,
    policy_id BIGINT NOT NULL,

    claim_amount DOUBLE NOT NULL,

    -- Nullable policy_key is intentional:
    -- profiling found some severity rows whose IDpol does not appear in freMTPL2freq.
    FOREIGN KEY (policy_key) REFERENCES warehouse.dim_policy(policy_key)
);

-- Grain: one row per scenario / assumption year
CREATE TABLE warehouse.fact_economic_assumption (
    assumption_key INTEGER PRIMARY KEY,

    scenario_key INTEGER NOT NULL,

    assumption_year INTEGER NOT NULL,
    annual_claim_inflation_rate DOUBLE NOT NULL,
    annual_expense_inflation_rate DOUBLE NOT NULL,
    annual_premium_trend_rate DOUBLE NOT NULL,
    risk_free_discount_rate DOUBLE NOT NULL,
    portfolio_growth_rate DOUBLE NOT NULL,
    frequency_trend_rate DOUBLE NOT NULL,
    severity_trend_rate DOUBLE NOT NULL,

    FOREIGN KEY (scenario_key) REFERENCES warehouse.dim_economic_scenario(scenario_key)
);

-- Grain: one row per scenario / projection year / claim type
CREATE TABLE warehouse.fact_inflation_scenario (
    inflation_key INTEGER PRIMARY KEY,

    scenario_key INTEGER NOT NULL,

    projection_year INTEGER NOT NULL,
    claim_type VARCHAR NOT NULL,
    annual_inflation_rate DOUBLE NOT NULL,
    base_scenario_inflation_rate DOUBLE NOT NULL,
    cumulative_base_inflation_factor DOUBLE NOT NULL,

    FOREIGN KEY (scenario_key) REFERENCES warehouse.dim_economic_scenario(scenario_key)
);

-- ============================================================
-- 5. Schema check
-- ============================================================

SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = 'warehouse'
ORDER BY table_name;
