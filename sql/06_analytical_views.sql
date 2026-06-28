-- 06_analytical_views.sql
-- Project: Actuarial Motor Insurance Risk Analysis
-- Purpose:
--   Create reusable analytical views for Python, Power BI, and reporting.
--
-- Notes:
--   These views intentionally aggregate measures before combining fact tables.
--   This avoids incorrect many-to-many joins between policy exposure facts
--   and claim payment facts.

CREATE SCHEMA IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_portfolio_summary;
DROP VIEW IF EXISTS analytics.vw_region_summary;
DROP VIEW IF EXISTS analytics.vw_driver_age_summary;
DROP VIEW IF EXISTS analytics.vw_driver_age_band_summary;
DROP VIEW IF EXISTS analytics.vw_vehicle_brand_summary;
DROP VIEW IF EXISTS analytics.vw_vehicle_fuel_summary;
DROP VIEW IF EXISTS analytics.vw_bonus_malus_summary;
DROP VIEW IF EXISTS analytics.vw_claim_severity_summary;
DROP VIEW IF EXISTS analytics.vw_claim_amount_distribution;
DROP VIEW IF EXISTS analytics.vw_economic_scenarios;

-- ============================================================
-- 1. Portfolio-level summary
-- ============================================================

CREATE VIEW analytics.vw_portfolio_summary AS
WITH exposure_summary AS (
    SELECT
        COUNT(*) AS policy_count,
        SUM(exposure) AS total_exposure,
        SUM(claim_count) AS total_claim_count,
        SUM(claim_count) / SUM(exposure) AS claim_frequency
    FROM warehouse.fact_policy_exposure
),
claim_summary AS (
    SELECT
        COUNT(*) AS claim_payment_count,
        SUM(claim_amount) AS total_claim_amount,
        AVG(claim_amount) AS average_claim_payment,
        MEDIAN(claim_amount) AS median_claim_payment,
        STDDEV_SAMP(claim_amount) AS claim_payment_stddev,
        MIN(claim_amount) AS min_claim_payment,
        MAX(claim_amount) AS max_claim_payment
    FROM warehouse.fact_claim
)
SELECT
    e.policy_count,
    e.total_exposure,
    e.total_claim_count,
    e.claim_frequency,
    c.claim_payment_count,
    c.total_claim_amount,
    c.average_claim_payment,
    c.median_claim_payment,
    c.claim_payment_stddev,
    c.min_claim_payment,
    c.max_claim_payment,
    c.total_claim_amount / e.total_exposure AS loss_cost_per_exposure
FROM exposure_summary e
CROSS JOIN claim_summary c;

-- ============================================================
-- 2. Region summary
-- ============================================================

CREATE VIEW analytics.vw_region_summary AS
WITH exposure_by_region AS (
    SELECT
        r.region_code,
        r.area_code,
        COUNT(*) AS policy_count,
        SUM(f.exposure) AS exposure,
        SUM(f.claim_count) AS claim_count,
        SUM(f.claim_count) / SUM(f.exposure) AS claim_frequency
    FROM warehouse.fact_policy_exposure f
    JOIN warehouse.dim_region r
        ON f.region_key = r.region_key
    GROUP BY
        r.region_code,
        r.area_code
),
claim_by_region AS (
    SELECT
        r.region_code,
        r.area_code,
        COUNT(*) AS claim_payment_count,
        SUM(c.claim_amount) AS total_claim_amount,
        AVG(c.claim_amount) AS average_claim_payment,
        MEDIAN(c.claim_amount) AS median_claim_payment
    FROM warehouse.fact_claim c
    JOIN warehouse.dim_policy p
        ON c.policy_key = p.policy_key
    JOIN warehouse.fact_policy_exposure f
        ON p.policy_key = f.policy_key
    JOIN warehouse.dim_region r
        ON f.region_key = r.region_key
    GROUP BY
        r.region_code,
        r.area_code
)
SELECT
    e.region_code,
    e.area_code,
    e.policy_count,
    e.exposure,
    e.claim_count,
    e.claim_frequency,
    COALESCE(c.claim_payment_count, 0) AS claim_payment_count,
    COALESCE(c.total_claim_amount, 0) AS total_claim_amount,
    c.average_claim_payment,
    c.median_claim_payment,
    COALESCE(c.total_claim_amount, 0) / e.exposure AS loss_cost_per_exposure
FROM exposure_by_region e
LEFT JOIN claim_by_region c
    ON e.region_code = c.region_code
   AND e.area_code = c.area_code;

-- ============================================================
-- 3. Driver age summaries
-- ============================================================

CREATE VIEW analytics.vw_driver_age_summary AS
SELECT
    d.driver_age,
    COUNT(*) AS policy_count,
    SUM(f.exposure) AS exposure,
    SUM(f.claim_count) AS claim_count,
    SUM(f.claim_count) / SUM(f.exposure) AS claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_driver d
    ON f.driver_key = d.driver_key
GROUP BY d.driver_age;

CREATE VIEW analytics.vw_driver_age_band_summary AS
SELECT
    CASE
        WHEN d.driver_age BETWEEN 18 AND 24 THEN '18-24'
        WHEN d.driver_age BETWEEN 25 AND 34 THEN '25-34'
        WHEN d.driver_age BETWEEN 35 AND 44 THEN '35-44'
        WHEN d.driver_age BETWEEN 45 AND 54 THEN '45-54'
        WHEN d.driver_age BETWEEN 55 AND 64 THEN '55-64'
        WHEN d.driver_age BETWEEN 65 AND 74 THEN '65-74'
        ELSE '75+'
    END AS driver_age_band,
    COUNT(*) AS policy_count,
    SUM(f.exposure) AS exposure,
    SUM(f.claim_count) AS claim_count,
    SUM(f.claim_count) / SUM(f.exposure) AS claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_driver d
    ON f.driver_key = d.driver_key
GROUP BY driver_age_band;

-- ============================================================
-- 4. Vehicle summaries
-- ============================================================

CREATE VIEW analytics.vw_vehicle_brand_summary AS
SELECT
    v.vehicle_brand,
    COUNT(*) AS policy_count,
    SUM(f.exposure) AS exposure,
    SUM(f.claim_count) AS claim_count,
    SUM(f.claim_count) / SUM(f.exposure) AS claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_vehicle v
    ON f.vehicle_key = v.vehicle_key
GROUP BY v.vehicle_brand;

CREATE VIEW analytics.vw_vehicle_fuel_summary AS
SELECT
    v.vehicle_gas,
    COUNT(*) AS policy_count,
    SUM(f.exposure) AS exposure,
    SUM(f.claim_count) AS claim_count,
    SUM(f.claim_count) / SUM(f.exposure) AS claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_vehicle v
    ON f.vehicle_key = v.vehicle_key
GROUP BY v.vehicle_gas;

-- ============================================================
-- 5. Bonus-malus summary
-- ============================================================

CREATE VIEW analytics.vw_bonus_malus_summary AS
SELECT
    p.bonus_malus,
    COUNT(*) AS policy_count,
    SUM(f.exposure) AS exposure,
    SUM(f.claim_count) AS claim_count,
    SUM(f.claim_count) / SUM(f.exposure) AS claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_policy p
    ON f.policy_key = p.policy_key
GROUP BY p.bonus_malus;

-- ============================================================
-- 6. Claim severity views
-- ============================================================

CREATE VIEW analytics.vw_claim_severity_summary AS
SELECT
    COUNT(*) AS claim_payment_count,
    SUM(claim_amount) AS total_claim_amount,
    AVG(claim_amount) AS average_claim_payment,
    MEDIAN(claim_amount) AS median_claim_payment,
    STDDEV_SAMP(claim_amount) AS claim_payment_stddev,
    MIN(claim_amount) AS min_claim_payment,
    MAX(claim_amount) AS max_claim_payment,
    QUANTILE_CONT(claim_amount, 0.75) AS claim_payment_q75,
    QUANTILE_CONT(claim_amount, 0.90) AS claim_payment_q90,
    QUANTILE_CONT(claim_amount, 0.95) AS claim_payment_q95,
    QUANTILE_CONT(claim_amount, 0.99) AS claim_payment_q99
FROM warehouse.fact_claim;

CREATE VIEW analytics.vw_claim_amount_distribution AS
SELECT
    CASE
        WHEN claim_amount < 500 THEN 'Under 500'
        WHEN claim_amount < 1000 THEN '500-999'
        WHEN claim_amount < 2500 THEN '1,000-2,499'
        WHEN claim_amount < 5000 THEN '2,500-4,999'
        WHEN claim_amount < 10000 THEN '5,000-9,999'
        WHEN claim_amount < 50000 THEN '10,000-49,999'
        WHEN claim_amount < 100000 THEN '50,000-99,999'
        ELSE '100,000+'
    END AS claim_amount_band,
    COUNT(*) AS claim_payment_count,
    SUM(claim_amount) AS total_claim_amount,
    AVG(claim_amount) AS average_claim_payment
FROM warehouse.fact_claim
GROUP BY claim_amount_band;

-- ============================================================
-- 7. Economic scenarios
-- ============================================================

CREATE VIEW analytics.vw_economic_scenarios AS
SELECT
    s.scenario_id,
    s.scenario_name,
    e.assumption_year,
    e.annual_claim_inflation_rate,
    e.annual_expense_inflation_rate,
    e.annual_premium_trend_rate,
    e.risk_free_discount_rate,
    e.portfolio_growth_rate,
    e.frequency_trend_rate,
    e.severity_trend_rate
FROM warehouse.fact_economic_assumption e
JOIN warehouse.dim_economic_scenario s
    ON e.scenario_key = s.scenario_key;

-- ============================================================
-- 8. View checks
-- ============================================================

SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = 'analytics'
ORDER BY table_name;

SELECT *
FROM analytics.vw_portfolio_summary;
