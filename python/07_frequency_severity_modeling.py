"""
07_frequency_severity_modeling.py
Project: Actuarial Motor Insurance Risk Analysis

Purpose:
    Fit and evaluate actuarial frequency and severity models using the DuckDB warehouse.

    Frequency:
        - Estimate Poisson claim frequency per exposure-year
        - Compare observed claim counts with expected Poisson counts

    Severity:
        - Fit Gamma and Lognormal severity distributions
        - Compare model fit using log-likelihood, AIC, and BIC
        - Export selected model parameters for Monte Carlo simulation
        - Generate diagnostic plots

Run from the project root:
    python python/07_frequency_severity_modeling.py
"""

from pathlib import Path
from datetime import date
import math

import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "database" / "actuarial_risk.duckdb"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"
MODEL_DIR = PROJECT_ROOT / "models"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def calculate_aic_bic(log_likelihood: float, k: int, n: int) -> tuple[float, float]:
    """Return AIC and BIC for a fitted model."""
    aic = 2 * k - 2 * log_likelihood
    bic = k * math.log(n) - 2 * log_likelihood
    return aic, bic


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run the DuckDB build script before running this Python model."
        )

    con = duckdb.connect(str(DB_PATH), read_only=True)

    freq_df = con.execute("""
        SELECT
            exposure,
            claim_count
        FROM warehouse.fact_policy_exposure
        WHERE exposure > 0
    """).df()

    severity_df = con.execute("""
        SELECT
            claim_amount
        FROM warehouse.fact_claim
        WHERE claim_amount > 0
    """).df()

    con.close()

    claim_amounts = severity_df["claim_amount"].to_numpy()
    n_claims = len(claim_amounts)

    # ============================================================
    # 1. Frequency modeling
    # ============================================================

    total_exposure = freq_df["exposure"].sum()
    total_claim_count = freq_df["claim_count"].sum()
    lambda_per_exposure = total_claim_count / total_exposure

    frequency_summary = pd.DataFrame([{
        "total_policies": len(freq_df),
        "total_exposure": total_exposure,
        "total_claim_count": total_claim_count,
        "lambda_per_exposure_year": lambda_per_exposure
    }])

    frequency_summary.to_csv(TABLE_DIR / "frequency_model_summary.csv", index=False)

    # Observed claim-count distribution by policy
    observed_counts = (
        freq_df["claim_count"]
        .value_counts()
        .sort_index()
        .reset_index()
    )
    observed_counts.columns = ["claim_count", "observed_policy_count"]

    max_claim_count = int(freq_df["claim_count"].max())
    claim_count_grid = np.arange(0, max_claim_count + 1)

    # Simple expected counts using average exposure-adjusted lambda.
    # This is an approximation because policies have different exposures.
    expected_probs = stats.poisson.pmf(claim_count_grid, mu=lambda_per_exposure * freq_df["exposure"].mean())
    expected_counts = pd.DataFrame({
        "claim_count": claim_count_grid,
        "expected_policy_count": expected_probs * len(freq_df)
    })

    frequency_fit = observed_counts.merge(expected_counts, on="claim_count", how="outer").fillna(0)
    frequency_fit.to_csv(TABLE_DIR / "frequency_observed_vs_poisson.csv", index=False)

    plt.figure(figsize=(10, 6))
    plot_counts = frequency_fit[frequency_fit["claim_count"] <= 8]
    x = plot_counts["claim_count"].to_numpy()
    width = 0.4
    plt.bar(x - width/2, plot_counts["observed_policy_count"], width=width, label="Observed")
    plt.bar(x + width/2, plot_counts["expected_policy_count"], width=width, label="Poisson expected")
    plt.xlabel("Claim count per policy")
    plt.ylabel("Policy count")
    plt.title("Observed vs Poisson Claim Frequency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "frequency_observed_vs_poisson.png", dpi=150)
    plt.close()

    # ============================================================
    # 2. Severity modeling
    # ============================================================

    severity_summary = pd.DataFrame([{
        "claim_payment_count": n_claims,
        "mean_claim_amount": claim_amounts.mean(),
        "median_claim_amount": np.median(claim_amounts),
        "stddev_claim_amount": claim_amounts.std(ddof=1),
        "min_claim_amount": claim_amounts.min(),
        "max_claim_amount": claim_amounts.max(),
        "q75": np.quantile(claim_amounts, 0.75),
        "q90": np.quantile(claim_amounts, 0.90),
        "q95": np.quantile(claim_amounts, 0.95),
        "q99": np.quantile(claim_amounts, 0.99),
    }])
    severity_summary.to_csv(TABLE_DIR / "severity_summary.csv", index=False)

    # Fit distributions.
    # loc fixed at 0 because claim amounts are positive and insurance severity models
    # are usually modeled on positive support.
    gamma_shape, gamma_loc, gamma_scale = stats.gamma.fit(claim_amounts, floc=0)
    lognorm_shape, lognorm_loc, lognorm_scale = stats.lognorm.fit(claim_amounts, floc=0)

    gamma_loglik = np.sum(stats.gamma.logpdf(claim_amounts, gamma_shape, loc=gamma_loc, scale=gamma_scale))
    lognorm_loglik = np.sum(stats.lognorm.logpdf(claim_amounts, lognorm_shape, loc=lognorm_loc, scale=lognorm_scale))

    # Parameters:
    # Gamma: shape, scale = 2 parameters when loc fixed
    # Lognormal: sigma(shape), scale=exp(mu) = 2 parameters when loc fixed
    gamma_aic, gamma_bic = calculate_aic_bic(gamma_loglik, k=2, n=n_claims)
    lognorm_aic, lognorm_bic = calculate_aic_bic(lognorm_loglik, k=2, n=n_claims)

    candidate_models = pd.DataFrame([
        {
            "distribution": "gamma",
            "log_likelihood": gamma_loglik,
            "aic": gamma_aic,
            "bic": gamma_bic,
            "param_1_name": "shape_alpha",
            "param_1_value": gamma_shape,
            "param_2_name": "scale_theta",
            "param_2_value": gamma_scale,
            "loc_fixed": gamma_loc
        },
        {
            "distribution": "lognormal",
            "log_likelihood": lognorm_loglik,
            "aic": lognorm_aic,
            "bic": lognorm_bic,
            "param_1_name": "sigma",
            "param_1_value": lognorm_shape,
            "param_2_name": "mu",
            "param_2_value": math.log(lognorm_scale),
            "loc_fixed": lognorm_loc
        },
    ]).sort_values("aic").reset_index(drop=True)

    candidate_models["rank"] = candidate_models["aic"].rank(method="first").astype(int)

    # Dashboard-friendly fields for Power BI.
    # The selected severity model is the candidate with the lowest AIC.
    candidate_models["best_fit"] = (
        candidate_models["rank"] == 1
    ).map({True: "✓", False: ""})

    candidate_models["distribution"] = candidate_models["distribution"].str.title()

    candidate_models = candidate_models[
        [
            "best_fit",
            "rank",
            "distribution",
            "log_likelihood",
            "aic",
            "bic",
            "param_1_name",
            "param_1_value",
            "param_2_name",
            "param_2_value",
            "loc_fixed",
        ]
    ]

    candidate_models.to_csv(MODEL_DIR / "candidate_models.csv", index=False)

    selected = candidate_models.iloc[0]

    selected_model = pd.DataFrame([{
        "model_version": "1.0",
        "analysis_date": date.today().isoformat(),
        "selection_criterion": "lowest_aic",

        "frequency_distribution": "poisson",
        "lambda_per_exposure_year": lambda_per_exposure,

        "severity_distribution": str(selected["distribution"]).lower(),
        "severity_log_likelihood": selected["log_likelihood"],
        "severity_aic": selected["aic"],
        "severity_bic": selected["bic"],
        "severity_param_1_name": selected["param_1_name"],
        "severity_param_1_value": selected["param_1_value"],
        "severity_param_2_name": selected["param_2_name"],
        "severity_param_2_value": selected["param_2_value"],
        "severity_loc_fixed": selected["loc_fixed"],
    }])

    selected_model.to_csv(MODEL_DIR / "selected_frequency_severity_model.csv", index=False)

    # ============================================================
    # 3. Diagnostic plots
    # ============================================================

    # Log-spaced histogram
    log_bins = np.logspace(
        np.log10(claim_amounts.min()),
        np.log10(claim_amounts.max()),
        75
    )

    plt.figure(figsize=(10, 6))
    plt.hist(claim_amounts, bins=log_bins)
    plt.xscale("log")
    plt.xlabel("Claim amount")
    plt.ylabel("Claim payment count")
    plt.title("Claim Severity Distribution with Log-Spaced Bins")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "severity_histogram_log_bins.png", dpi=150)
    plt.close()

    # Histogram with fitted PDFs on log x-axis.
    # Density=True scales histogram so fitted PDFs can be compared visually.
    x_grid = np.logspace(
        np.log10(np.quantile(claim_amounts, 0.001)),
        np.log10(np.quantile(claim_amounts, 0.999)),
        500
    )

    gamma_pdf = stats.gamma.pdf(x_grid, gamma_shape, loc=gamma_loc, scale=gamma_scale)
    lognorm_pdf = stats.lognorm.pdf(x_grid, lognorm_shape, loc=lognorm_loc, scale=lognorm_scale)

    plt.figure(figsize=(10, 6))
    plt.hist(claim_amounts, bins=log_bins, density=True, alpha=0.5, label="Observed")
    plt.plot(x_grid, gamma_pdf, label="Gamma fitted PDF")
    plt.plot(x_grid, lognorm_pdf, label="Lognormal fitted PDF")
    plt.xscale("log")
    plt.xlabel("Claim amount")
    plt.ylabel("Density")
    plt.title("Claim Severity: Observed vs Fitted Distributions")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "severity_fitted_distributions.png", dpi=150)
    plt.close()

    # Empirical CDF
    sorted_claims = np.sort(claim_amounts)
    ecdf = np.arange(1, n_claims + 1) / n_claims

    plt.figure(figsize=(10, 6))
    plt.plot(sorted_claims, ecdf)
    plt.xscale("log")
    plt.xlabel("Claim amount")
    plt.ylabel("Empirical cumulative probability")
    plt.title("Empirical CDF of Claim Severity")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "severity_empirical_cdf.png", dpi=150)
    plt.close()

    # QQ plots
    probs = (np.arange(1, n_claims + 1) - 0.5) / n_claims
    observed_quantiles = sorted_claims

    gamma_quantiles = stats.gamma.ppf(probs, gamma_shape, loc=gamma_loc, scale=gamma_scale)
    lognorm_quantiles = stats.lognorm.ppf(probs, lognorm_shape, loc=lognorm_loc, scale=lognorm_scale)

    plt.figure(figsize=(8, 8))
    plt.scatter(gamma_quantiles, observed_quantiles, s=4, alpha=0.4)
    max_q = np.quantile(observed_quantiles, 0.995)
    plt.plot([0, max_q], [0, max_q], linestyle="--")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Gamma theoretical quantiles")
    plt.ylabel("Observed quantiles")
    plt.title("QQ Plot: Gamma Severity Fit")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "severity_qq_gamma.png", dpi=150)
    plt.close()

    plt.figure(figsize=(8, 8))
    plt.scatter(lognorm_quantiles, observed_quantiles, s=4, alpha=0.4)
    max_q = np.quantile(observed_quantiles, 0.995)
    plt.plot([0, max_q], [0, max_q], linestyle="--")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Lognormal theoretical quantiles")
    plt.ylabel("Observed quantiles")
    plt.title("QQ Plot: Lognormal Severity Fit")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "severity_qq_lognormal.png", dpi=150)
    plt.close()

    # ============================================================
    # 4. Console output
    # ============================================================

    print("\n=== Frequency Model ===")
    print(f"Total exposure: {total_exposure:,.2f}")
    print(f"Total claim count: {total_claim_count:,.0f}")
    print(f"Poisson lambda per exposure-year: {lambda_per_exposure:.6f}")

    print("\n=== Severity Summary ===")
    print(severity_summary.to_string(index=False))

    print("\n=== Candidate Severity Models ===")
    print(candidate_models[["best_fit", "rank", "distribution", "log_likelihood", "aic", "bic"]].to_string(index=False))

    print("\n=== Selected Model ===")
    print(selected_model.to_string(index=False))

    print("\nSaved outputs to:")
    print(f"  Figures: {FIGURE_DIR}")
    print(f"  Tables:  {TABLE_DIR}")
    print(f"  Models:  {MODEL_DIR}")


if __name__ == "__main__":
    main()
