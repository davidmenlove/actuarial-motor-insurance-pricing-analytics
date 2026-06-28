-- 02_data_profiling.sql
-- Purpose:
--   Explore and validate the raw staging tables before creating
--   the operational and dimensional data models.

-- ============================================================
-- 1. Inspect table schemas
-- ============================================================

DESCRIBE staging.stg_fremtpl2freq;
DESCRIBE staging.stg_fremtpl2sev;
DESCRIBE staging.stg_economic_assumptions;
DESCRIBE staging.stg_inflation_scenarios;

-- ============================================================
-- 2. Preview source data
-- ============================================================

SELECT *
FROM staging.stg_fremtpl2freq
LIMIT 10;

SELECT *
FROM staging.stg_fremtpl2sev
LIMIT 10;

SELECT *
FROM staging.stg_economic_assumptions
LIMIT 10;

SELECT *
FROM staging.stg_inflation_scenarios
LIMIT 10;

-- ============================================================
-- 3. Row counts and key uniqueness checks
-- ============================================================

SELECT
    COUNT(*) AS row_count,
    COUNT(DISTINCT IDpol) AS distinct_policy_ids,
    COUNT(*) - COUNT(DISTINCT IDpol) AS duplicate_policy_rows
FROM staging.stg_fremtpl2freq;

SELECT
    COUNT(*) AS row_count,
    COUNT(DISTINCT IDpol) AS distinct_policy_ids_with_claims
FROM staging.stg_fremtpl2sev;

-- Policies in severity table that do not exist in frequency table
SELECT
    COUNT(*) AS claim_rows_without_matching_policy
FROM staging.stg_fremtpl2sev sev
LEFT JOIN staging.stg_fremtpl2freq freq
    ON sev.IDpol = freq.IDpol
WHERE freq.IDpol IS NULL;

-- ============================================================
-- 4. Claim frequency / exposure checks
-- ============================================================

SELECT
    MIN(Exposure) AS min_exposure,
    MAX(Exposure) AS max_exposure,
    AVG(Exposure) AS avg_exposure,
    SUM(Exposure) AS total_exposure
FROM staging.stg_fremtpl2freq;

SELECT
    MIN(ClaimNb) AS min_claim_count,
    MAX(ClaimNb) AS max_claim_count,
    AVG(ClaimNb) AS avg_claim_count,
    SUM(ClaimNb) AS total_claim_count
FROM staging.stg_fremtpl2freq;

SELECT
    ClaimNb,
    COUNT(*) AS policy_count
FROM staging.stg_fremtpl2freq
GROUP BY ClaimNb
ORDER BY ClaimNb;

-- ============================================================
-- 5. Claim severity checks
-- ============================================================

SELECT
    COUNT(*) AS claim_rows,
    MIN(ClaimAmount) AS min_claim_amount,
    MAX(ClaimAmount) AS max_claim_amount,
    AVG(ClaimAmount) AS avg_claim_amount,
    SUM(ClaimAmount) AS total_claim_amount
FROM staging.stg_fremtpl2sev;

SELECT
    IDpol,
    COUNT(*) AS claim_payment_rows,
    SUM(ClaimAmount) AS total_claim_amount
FROM staging.stg_fremtpl2sev
GROUP BY IDpol
ORDER BY claim_payment_rows DESC, total_claim_amount DESC
LIMIT 20;

-- ============================================================
-- 6. Compare frequency claim counts to severity claim rows
-- ============================================================

WITH sev_by_policy AS (
    SELECT
        IDpol,
        COUNT(*) AS severity_rows,
        SUM(ClaimAmount) AS total_claim_amount
    FROM staging.stg_fremtpl2sev
    GROUP BY IDpol
)
SELECT
    freq.IDpol,
    freq.ClaimNb,
    COALESCE(sev.severity_rows, 0) AS severity_rows,
    COALESCE(sev.total_claim_amount, 0) AS total_claim_amount
FROM staging.stg_fremtpl2freq freq
LEFT JOIN sev_by_policy sev
    ON freq.IDpol = sev.IDpol
WHERE freq.ClaimNb <> COALESCE(sev.severity_rows, 0)
ORDER BY freq.ClaimNb DESC, severity_rows DESC
LIMIT 50;

SELECT
    COUNT(*) AS policies_where_claimnb_differs_from_severity_rows
FROM (
    WITH sev_by_policy AS (
        SELECT
            IDpol,
            COUNT(*) AS severity_rows
        FROM staging.stg_fremtpl2sev
        GROUP BY IDpol
    )
    SELECT
        freq.IDpol,
        freq.ClaimNb,
        COALESCE(sev.severity_rows, 0) AS severity_rows
    FROM staging.stg_fremtpl2freq freq
    LEFT JOIN sev_by_policy sev
        ON freq.IDpol = sev.IDpol
    WHERE freq.ClaimNb <> COALESCE(sev.severity_rows, 0)
) mismatch;

-- ============================================================
-- 7. Dimension candidate profiling
-- ============================================================

SELECT
    Area,
    COUNT(*) AS policy_count,
    SUM(Exposure) AS total_exposure,
    SUM(ClaimNb) AS total_claim_count
FROM staging.stg_fremtpl2freq
GROUP BY Area
ORDER BY Area;

SELECT
    Region,
    COUNT(*) AS policy_count,
    SUM(Exposure) AS total_exposure,
    SUM(ClaimNb) AS total_claim_count
FROM staging.stg_fremtpl2freq
GROUP BY Region
ORDER BY Region;

SELECT
    VehGas,
    COUNT(*) AS policy_count,
    SUM(Exposure) AS total_exposure,
    SUM(ClaimNb) AS total_claim_count
FROM staging.stg_fremtpl2freq
GROUP BY VehGas
ORDER BY VehGas;

SELECT
    VehBrand,
    COUNT(*) AS policy_count,
    SUM(Exposure) AS total_exposure,
    SUM(ClaimNb) AS total_claim_count
FROM staging.stg_fremtpl2freq
GROUP BY VehBrand
ORDER BY policy_count DESC;

SELECT
    VehPower,
    COUNT(*) AS policy_count,
    SUM(Exposure) AS total_exposure,
    SUM(ClaimNb) AS total_claim_count
FROM staging.stg_fremtpl2freq
GROUP BY VehPower
ORDER BY VehPower;

-- ============================================================
-- 8. Driver / vehicle numeric range checks
-- ============================================================

SELECT
    MIN(VehAge) AS min_vehicle_age,
    MAX(VehAge) AS max_vehicle_age,
    AVG(VehAge) AS avg_vehicle_age,
    MIN(DrivAge) AS min_driver_age,
    MAX(DrivAge) AS max_driver_age,
    AVG(DrivAge) AS avg_driver_age,
    MIN(BonusMalus) AS min_bonus_malus,
    MAX(BonusMalus) AS max_bonus_malus,
    AVG(BonusMalus) AS avg_bonus_malus,
    MIN(Density) AS min_density,
    MAX(Density) AS max_density,
    AVG(Density) AS avg_density
FROM staging.stg_fremtpl2freq;

-- Possible outliers to inspect
SELECT *
FROM staging.stg_fremtpl2freq
WHERE VehAge < 0
   OR DrivAge < 18
   OR Exposure <= 0
   OR ClaimNb < 0
LIMIT 50;

-- ============================================================
-- 9. Economic assumptions checks
-- ============================================================

SELECT
    scenario_id,
    COUNT(*) AS assumption_year_count,
    MIN(assumption_year) AS min_year,
    MAX(assumption_year) AS max_year
FROM staging.stg_economic_assumptions
GROUP BY scenario_id
ORDER BY scenario_id;

SELECT
    scenario_id,
    projection_year,
    COUNT(*) AS rows_per_scenario_year
FROM staging.stg_inflation_scenarios
GROUP BY scenario_id, projection_year
ORDER BY scenario_id, projection_year;

SELECT
    scenario_id,
    claim_type,
    COUNT(*) AS row_count,
    MIN(annual_inflation_rate) AS min_inflation_rate,
    MAX(annual_inflation_rate) AS max_inflation_rate
FROM staging.stg_inflation_scenarios
GROUP BY scenario_id, claim_type
ORDER BY scenario_id, claim_type;
