-- 05_business_analysis.sql
-- Project: Actuarial Motor Insurance Risk Analysis
-- Purpose:
--   Example analytical queries against the dimensional warehouse.

-- ============================================================
-- 1. Portfolio Summary
-- ============================================================

SELECT
    COUNT(*) AS policies,
    SUM(exposure) AS total_exposure,
    SUM(claim_count) AS total_claims,
    ROUND(SUM(claim_count) / SUM(exposure),4) AS claims_per_exposure
FROM warehouse.fact_policy_exposure;

SELECT
    COUNT(*) AS claim_payments,
    SUM(claim_amount) AS total_paid,
    AVG(claim_amount) AS avg_claim,
    MEDIAN(claim_amount) AS median_claim,
    MAX(claim_amount) AS largest_claim
FROM warehouse.fact_claim;

-- ============================================================
-- 2. Region Analysis
-- ============================================================

SELECT
    r.region_code,
    COUNT(*) AS policies,
    SUM(f.exposure) AS exposure,
    SUM(f.claim_count) AS claims,
    ROUND(SUM(f.claim_count)/SUM(f.exposure),4) AS claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_region r
  ON f.region_key=r.region_key
GROUP BY r.region_code
ORDER BY claim_frequency DESC;

-- ============================================================
-- 3. Driver Age
-- ============================================================

SELECT
    d.driver_age,
    COUNT(*) policies,
    SUM(f.exposure) exposure,
    SUM(f.claim_count) claims,
    ROUND(SUM(f.claim_count)/SUM(f.exposure),4) claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_driver d
  ON f.driver_key=d.driver_key
GROUP BY d.driver_age
ORDER BY d.driver_age;

-- ============================================================
-- 4. Vehicle Characteristics
-- ============================================================

SELECT
    v.vehicle_brand,
    COUNT(*) policies,
    SUM(f.exposure) exposure,
    SUM(f.claim_count) claims,
    ROUND(SUM(f.claim_count)/SUM(f.exposure),4) claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_vehicle v
  ON f.vehicle_key=v.vehicle_key
GROUP BY v.vehicle_brand
ORDER BY claim_frequency DESC;

SELECT
    v.vehicle_gas,
    COUNT(*) policies,
    SUM(f.exposure) exposure,
    SUM(f.claim_count) claims,
    ROUND(SUM(f.claim_count)/SUM(f.exposure),4) claim_frequency
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_vehicle v
  ON f.vehicle_key=v.vehicle_key
GROUP BY v.vehicle_gas;

-- ============================================================
-- 5. Bonus-Malus Distribution
-- ============================================================

SELECT
    p.bonus_malus,
    COUNT(*) policies,
    SUM(f.claim_count) claims,
    SUM(f.exposure) exposure
FROM warehouse.fact_policy_exposure f
JOIN warehouse.dim_policy p
  ON f.policy_key=p.policy_key
GROUP BY p.bonus_malus
ORDER BY p.bonus_malus;

-- ============================================================
-- 6. Top 20 Largest Claims
-- ============================================================

SELECT
    claim_key,
    policy_id,
    claim_amount
FROM warehouse.fact_claim
ORDER BY claim_amount DESC
LIMIT 20;

-- ============================================================
-- 7. Portfolio KPIs
-- ============================================================

SELECT
    ROUND(SUM(fc.claim_amount)/SUM(fp.exposure),2) AS loss_cost_per_exposure,
    ROUND(AVG(fc.claim_amount),2) AS average_claim_severity,
    ROUND(SUM(fp.claim_count)/SUM(fp.exposure),4) AS claim_frequency
FROM warehouse.fact_policy_exposure fp
CROSS JOIN warehouse.fact_claim fc;
