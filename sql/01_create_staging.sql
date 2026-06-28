-- 01_create_staging.sql
-- Project: Actuarial Motor Insurance Risk Analysis
-- Purpose: Create raw/staging tables in DuckDB and load source CSV files.
--
-- Run from the project root folder where your data/raw folder exists.
-- Example DuckDB command:
--   duckdb actuarial_risk.duckdb < sql/01_create_staging.sql

-- Optional: keep all raw tables in a separate schema
CREATE SCHEMA IF NOT EXISTS staging;

-- Drop staging tables so the script can be rerun safely during development
DROP TABLE IF EXISTS staging.stg_fremtpl2freq;
DROP TABLE IF EXISTS staging.stg_fremtpl2sev;
DROP TABLE IF EXISTS staging.stg_economic_assumptions;
DROP TABLE IF EXISTS staging.stg_inflation_scenarios;

-- Frequency / policy exposure source file
-- Grain: one row per policy exposure period
CREATE TABLE staging.stg_fremtpl2freq AS
SELECT *
FROM read_csv_auto('data/raw/freMTPL2freq.csv', header = true);

-- Severity / claims source file
-- Grain: one row per claim payment
CREATE TABLE staging.stg_fremtpl2sev AS
SELECT *
FROM read_csv_auto('data/raw/freMTPL2sev.csv', header = true);

-- Economic assumptions source file
-- Grain: one row per scenario / assumption year
CREATE TABLE staging.stg_economic_assumptions AS
SELECT *
FROM read_csv_auto('assumptions/economic_assumptions.csv', header = true);

-- Inflation scenarios source file
-- Grain: one row per scenario / projection year / claim type
CREATE TABLE staging.stg_inflation_scenarios AS
SELECT *
FROM read_csv_auto('assumptions/inflation_scenarios.csv', header = true);

-- Quick row-count checks
SELECT 'stg_fremtpl2freq' AS table_name, COUNT(*) AS row_count FROM staging.stg_fremtpl2freq
UNION ALL
SELECT 'stg_fremtpl2sev' AS table_name, COUNT(*) AS row_count FROM staging.stg_fremtpl2sev
UNION ALL
SELECT 'stg_economic_assumptions' AS table_name, COUNT(*) AS row_count FROM staging.stg_economic_assumptions
UNION ALL
SELECT 'stg_inflation_scenarios' AS table_name, COUNT(*) AS row_count FROM staging.stg_inflation_scenarios;