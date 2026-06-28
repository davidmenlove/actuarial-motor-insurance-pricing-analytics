-- 04_load_star_schema.sql
-- Project: Actuarial Motor Insurance Risk Analysis
-- Purpose:
--   Populate the warehouse star schema from staging tables.

-- ============================================================
-- 1. Clear warehouse tables so script can be rerun
-- ============================================================

DELETE FROM warehouse.fact_inflation_scenario;
DELETE FROM warehouse.fact_economic_assumption;
DELETE FROM warehouse.fact_claim;
DELETE FROM warehouse.fact_policy_exposure;

DELETE FROM warehouse.dim_economic_scenario;
DELETE FROM warehouse.dim_region;
DELETE FROM warehouse.dim_driver;
DELETE FROM warehouse.dim_vehicle;
DELETE FROM warehouse.dim_policy;

-- ============================================================
-- 2. Load dimensions
-- ============================================================

-- Policy dimension
-- Grain: one row per source policy ID
INSERT INTO warehouse.dim_policy (
    policy_key,
    policy_id,
    bonus_malus
)
SELECT
    ROW_NUMBER() OVER (ORDER BY IDpol) AS policy_key,
    IDpol AS policy_id,
    BonusMalus AS bonus_malus
FROM staging.stg_fremtpl2freq;

-- Vehicle dimension
-- Grain: one row per unique vehicle attribute combination
INSERT INTO warehouse.dim_vehicle (
    vehicle_key,
    vehicle_power,
    vehicle_age,
    vehicle_brand,
    vehicle_gas
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY VehPower, VehAge, VehBrand, VehGas
    ) AS vehicle_key,
    VehPower AS vehicle_power,
    VehAge AS vehicle_age,
    VehBrand AS vehicle_brand,
    VehGas AS vehicle_gas
FROM (
    SELECT DISTINCT
        VehPower,
        VehAge,
        VehBrand,
        VehGas
    FROM staging.stg_fremtpl2freq
) v;

-- Driver dimension
-- Grain: one row per unique driver age
INSERT INTO warehouse.dim_driver (
    driver_key,
    driver_age
)
SELECT
    ROW_NUMBER() OVER (ORDER BY DrivAge) AS driver_key,
    DrivAge AS driver_age
FROM (
    SELECT DISTINCT
        DrivAge
    FROM staging.stg_fremtpl2freq
) d;

-- Region dimension
-- Grain: one row per unique area / region / density combination
INSERT INTO warehouse.dim_region (
    region_key,
    area_code,
    region_code,
    density
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY Area, Region, Density
    ) AS region_key,
    Area AS area_code,
    Region AS region_code,
    Density AS density
FROM (
    SELECT DISTINCT
        Area,
        Region,
        Density
    FROM staging.stg_fremtpl2freq
) r;

-- Economic scenario dimension
-- Grain: one row per scenario
INSERT INTO warehouse.dim_economic_scenario (
    scenario_key,
    scenario_id,
    scenario_name
)
SELECT
    ROW_NUMBER() OVER (ORDER BY scenario_id) AS scenario_key,
    scenario_id,
    scenario_name
FROM (
    SELECT DISTINCT
        scenario_id,
        scenario_name
    FROM staging.stg_economic_assumptions

    UNION

    SELECT DISTINCT
        scenario_id,
        scenario_name
    FROM staging.stg_inflation_scenarios
) s;

-- ============================================================
-- 3. Load fact tables
-- ============================================================

-- Policy exposure fact
-- Grain: one row per policy exposure record
INSERT INTO warehouse.fact_policy_exposure (
    policy_exposure_key,
    policy_key,
    vehicle_key,
    driver_key,
    region_key,
    exposure,
    claim_count
)
SELECT
    ROW_NUMBER() OVER (ORDER BY freq.IDpol) AS policy_exposure_key,
    pol.policy_key,
    veh.vehicle_key,
    drv.driver_key,
    reg.region_key,
    freq.Exposure AS exposure,
    freq.ClaimNb AS claim_count
FROM staging.stg_fremtpl2freq freq
JOIN warehouse.dim_policy pol
    ON freq.IDpol = pol.policy_id
JOIN warehouse.dim_vehicle veh
    ON freq.VehPower = veh.vehicle_power
   AND freq.VehAge = veh.vehicle_age
   AND freq.VehBrand = veh.vehicle_brand
   AND freq.VehGas = veh.vehicle_gas
JOIN warehouse.dim_driver drv
    ON freq.DrivAge = drv.driver_age
JOIN warehouse.dim_region reg
    ON freq.Area = reg.area_code
   AND freq.Region = reg.region_code
   AND freq.Density = reg.density;

-- Claim fact
-- Grain: one row per claim payment row
-- policy_key is nullable because some severity IDs were not present in freMTPL2freq.
INSERT INTO warehouse.fact_claim (
    claim_key,
    policy_key,
    policy_id,
    claim_amount
)
SELECT
    ROW_NUMBER() OVER (ORDER BY sev.IDpol, sev.ClaimAmount) AS claim_key,
    pol.policy_key,
    sev.IDpol AS policy_id,
    sev.ClaimAmount AS claim_amount
FROM staging.stg_fremtpl2sev sev
LEFT JOIN warehouse.dim_policy pol
    ON sev.IDpol = pol.policy_id;

-- Economic assumptions fact
-- Grain: one row per scenario / assumption year
INSERT INTO warehouse.fact_economic_assumption (
    assumption_key,
    scenario_key,
    assumption_year,
    annual_claim_inflation_rate,
    annual_expense_inflation_rate,
    annual_premium_trend_rate,
    risk_free_discount_rate,
    portfolio_growth_rate,
    frequency_trend_rate,
    severity_trend_rate
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY econ.scenario_id, econ.assumption_year
    ) AS assumption_key,
    scen.scenario_key,
    econ.assumption_year,
    econ.annual_claim_inflation_rate,
    econ.annual_expense_inflation_rate,
    econ.annual_premium_trend_rate,
    econ.risk_free_discount_rate,
    econ.portfolio_growth_rate,
    econ.frequency_trend_rate,
    econ.severity_trend_rate
FROM staging.stg_economic_assumptions econ
JOIN warehouse.dim_economic_scenario scen
    ON econ.scenario_id = scen.scenario_id;

-- Inflation scenario fact
-- Grain: one row per scenario / projection year / claim type
INSERT INTO warehouse.fact_inflation_scenario (
    inflation_key,
    scenario_key,
    projection_year,
    claim_type,
    annual_inflation_rate,
    base_scenario_inflation_rate,
    cumulative_base_inflation_factor
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY inf.scenario_id, inf.projection_year, inf.claim_type
    ) AS inflation_key,
    scen.scenario_key,
    inf.projection_year,
    inf.claim_type,
    inf.annual_inflation_rate,
    inf.base_scenario_inflation_rate,
    inf.cumulative_base_inflation_factor
FROM staging.stg_inflation_scenarios inf
JOIN warehouse.dim_economic_scenario scen
    ON inf.scenario_id = scen.scenario_id;

-- ============================================================
-- 4. Row-count checks
-- ============================================================

SELECT 'dim_policy' AS table_name, COUNT(*) AS row_count FROM warehouse.dim_policy
UNION ALL
SELECT 'dim_vehicle' AS table_name, COUNT(*) AS row_count FROM warehouse.dim_vehicle
UNION ALL
SELECT 'dim_driver' AS table_name, COUNT(*) AS row_count FROM warehouse.dim_driver
UNION ALL
SELECT 'dim_region' AS table_name, COUNT(*) AS row_count FROM warehouse.dim_region
UNION ALL
SELECT 'dim_economic_scenario' AS table_name, COUNT(*) AS row_count FROM warehouse.dim_economic_scenario
UNION ALL
SELECT 'fact_policy_exposure' AS table_name, COUNT(*) AS row_count FROM warehouse.fact_policy_exposure
UNION ALL
SELECT 'fact_claim' AS table_name, COUNT(*) AS row_count FROM warehouse.fact_claim
UNION ALL
SELECT 'fact_economic_assumption' AS table_name, COUNT(*) AS row_count FROM warehouse.fact_economic_assumption
UNION ALL
SELECT 'fact_inflation_scenario' AS table_name, COUNT(*) AS row_count FROM warehouse.fact_inflation_scenario;

-- ============================================================
-- 5. Referential integrity / load quality checks
-- ============================================================

-- Policy exposure fact should match frequency staging row count.
SELECT
    (SELECT COUNT(*) FROM staging.stg_fremtpl2freq) AS staging_policy_rows,
    (SELECT COUNT(*) FROM warehouse.fact_policy_exposure) AS fact_policy_exposure_rows;

-- Claim fact should match severity staging row count.
SELECT
    (SELECT COUNT(*) FROM staging.stg_fremtpl2sev) AS staging_claim_rows,
    (SELECT COUNT(*) FROM warehouse.fact_claim) AS fact_claim_rows;

-- Count claim rows without matching policy dimension.
SELECT
    COUNT(*) AS claim_rows_without_policy_key
FROM warehouse.fact_claim
WHERE policy_key IS NULL;

-- Basic portfolio totals from warehouse.
SELECT
    SUM(exposure) AS total_exposure,
    SUM(claim_count) AS total_claim_count
FROM warehouse.fact_policy_exposure;

SELECT
    COUNT(*) AS claim_payment_rows,
    SUM(claim_amount) AS total_claim_amount,
    AVG(claim_amount) AS avg_claim_amount,
    MAX(claim_amount) AS max_claim_amount
FROM warehouse.fact_claim;
