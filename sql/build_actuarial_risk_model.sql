-- build_actuarial_risk_model.sql
-- Project: Actuarial Motor Insurance Risk Analysis
-- Purpose:
--   Rebuild the DuckDB staging and warehouse layers from source CSV files.
--
-- Run from the project root with:
--   duckdb database/actuarial_risk.duckdb -c ".read sql/build_actuarial_risk_model.sql"

.read sql/01_create_staging.sql
.read sql/03_create_star_schema.sql
.read sql/04_load_star_schema.sql
.read sql/06_analytical_views.sql