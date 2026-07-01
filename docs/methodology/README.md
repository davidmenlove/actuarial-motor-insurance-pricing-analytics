# Methodology: Actuarial Pricing Pipeline

## Objective

The pricing phase estimates the expected annual claim cost for one insured exposure-year. This expected claim cost is the **pure premium**, before expenses, profit margin, taxes, commissions, reinsurance, or other business loads.

```text
Pure Premium = Expected Claim Frequency × Expected Claim Severity
```

The workflow combines data engineering, statistical modeling, and Monte Carlo simulation to produce both a point estimate and a distribution of possible annual losses.

---

## 1. Data Preparation

Raw motor insurance policy and claims data are loaded into DuckDB staging tables without modification. This preserves the original source data and separates ingestion from transformation.

The source data contains two main grains:

- `freMTPL2freq`: one row per policy exposure record
- `freMTPL2sev`: one row per claim payment

Additional assumption files provide economic and inflation scenarios for later pricing sensitivity analysis.

---

## 2. Data Warehouse

A dimensional warehouse is created in DuckDB using a star-schema design. The warehouse separates descriptive attributes from measurable insurance outcomes.

Key fact tables:

- `fact_policy_exposure`: policy exposure and claim count
- `fact_claim`: claim payment amount
- `fact_economic_assumption`: scenario-level economic assumptions
- `fact_inflation_scenario`: projected inflation assumptions

Key dimensions:

- `dim_policy`
- `dim_vehicle`
- `dim_driver`
- `dim_region`
- `dim_economic_scenario`

This structure supports reusable SQL analysis, Python modeling, and future Power BI reporting.

---

## 3. Frequency Modeling

Claim frequency is modeled using a Poisson distribution.

The frequency parameter is estimated as:

```text
λ = Total Claim Count / Total Exposure
```

This produces the expected number of claims per policy exposure-year.

The observed claim count distribution is compared against the fitted Poisson model to validate that the frequency assumption is reasonable for a low-frequency insurance portfolio.

---

## 4. Severity Modeling

Claim severity is modeled using observed claim payment amounts.

Candidate distributions:

- Gamma
- Lognormal

Each distribution is fitted to positive claim payments. The fitted models are evaluated using:

- Log-likelihood
- AIC
- BIC
- Diagnostic plots
- QQ plots

The selected severity model is saved as a model artifact and used by downstream Monte Carlo simulations.

### Severity Data Note

The freMTPL2 severity dataset contains several highly repeated claim amounts. These fixed amounts are a known feature of the dataset and arise from standardized French motor claims settlement conventions. As a result, the empirical severity histogram contains visible spikes.

Continuous Gamma and Lognormal severity distributions are fitted to approximate the overall severity distribution for pricing purposes, rather than to reproduce each discrete settlement amount exactly.

---

## 5. Monte Carlo Pricing Simulation

The pricing simulation models annual loss for one insured exposure-year.

For each simulation:

```text
1. Simulate claim count from the fitted Poisson frequency model.
2. Simulate claim severities from the selected severity distribution.
3. Sum claim severities to obtain annual aggregate loss.
```

This produces a simulated distribution of annual policy-level losses.

Outputs include:

- Expected annual loss
- Standard deviation
- Median loss
- Value-at-Risk (VaR)
- Conditional Value-at-Risk (CVaR / TVaR)
- Probability of zero claims
- Probability of positive loss

The expected annual loss is interpreted as the model-indicated pure premium.

---

## 6. Scenario-Based Pricing

Scenario pricing extends the base pricing model by applying economic assumptions and claim inflation scenarios.

The scenario engine reads assumptions from CSV files rather than hard-coding values in Python. This allows pricing assumptions to be changed independently of model code.

For each scenario, the simulation adjusts:

- Claim frequency using the scenario frequency trend
- Claim severity using the scenario inflation factor

The result is a comparison of pure premium and tail-risk metrics under low, baseline, high, and stress inflation conditions.

---

## 7. Interpretation

The base pricing model estimates the expected loss for a single exposure-year. Scenario-based pricing then shows how sensitive that pure premium is to future economic assumptions.

This structure mirrors a practical actuarial pricing workflow:

```text
Historical Experience
      ↓
Frequency and Severity Models
      ↓
Economic Assumptions
      ↓
Pricing Indication
      ↓
Scenario Sensitivity
```

The model does not include expense loadings, profit margins, underwriting adjustments, or regulatory constraints. Those would be added after the pure premium indication in a full production pricing process.
