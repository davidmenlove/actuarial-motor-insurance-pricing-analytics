"""
08_monte_carlo_portfolio_simulation.py
Project: Actuarial Motor Insurance Risk Analysis

Purpose:
    Simulate annual aggregate portfolio losses using the selected frequency
    and severity model from the prior modeling step.

Inputs:
    models/selected_frequency_severity_model.csv

Outputs:
    outputs/tables/simulation_summary.csv
    outputs/tables/simulation_percentiles.csv
    outputs/tables/simulation_results_sample.csv
    outputs/figures/simulated_annual_loss_distribution.png
    outputs/figures/simulated_annual_loss_ecdf.png

Run from the project root:
    python python/08_monte_carlo_portfolio_simulation.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "selected_frequency_severity_model.csv"

# Start with 100,000 for normal development.
# Increase to 1,000,000 for a higher-precision run.
N_SIMULATIONS = 100_000

# Set a seed for reproducibility.
RANDOM_SEED = 42

# Risk thresholds for VaR and CVaR / TVaR.
VAR_LEVELS = [0.95, 0.99, 0.995]

# Optional: save only a sample of simulation-level results to avoid large CSV files.
N_RESULTS_TO_SAVE = 10_000


# ============================================================
# Helper functions
# ============================================================

def load_selected_model(model_path: Path) -> dict:
    """Load selected frequency and severity model parameters."""
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file not found: {model_path}\n"
            "Run python/07_frequency_severity_modeling.py first."
        )

    model_df = pd.read_csv(model_path)

    if len(model_df) != 1:
        raise ValueError(
            "selected_frequency_severity_model.csv should contain exactly one row."
        )

    return model_df.iloc[0].to_dict()


def simulate_severities(
    rng: np.random.Generator,
    severity_distribution: str,
    n_claims: int,
    param_1_name: str,
    param_1_value: float,
    param_2_name: str,
    param_2_value: float,
) -> np.ndarray:
    """Simulate claim severities from the selected severity distribution."""
    if n_claims == 0:
        return np.array([], dtype=float)

    severity_distribution = severity_distribution.lower()

    if severity_distribution == "lognormal":
        # The selected model stores:
        #   param_1 = sigma
        #   param_2 = mu
        params = {
            param_1_name: param_1_value,
            param_2_name: param_2_value,
        }
        sigma = float(params["sigma"])
        mu = float(params["mu"])

        return rng.lognormal(mean=mu, sigma=sigma, size=n_claims)

    if severity_distribution == "gamma":
        # The selected model stores:
        #   param_1 = shape_alpha
        #   param_2 = scale_theta
        params = {
            param_1_name: param_1_value,
            param_2_name: param_2_value,
        }
        alpha = float(params["shape_alpha"])
        theta = float(params["scale_theta"])

        return rng.gamma(shape=alpha, scale=theta, size=n_claims)

    raise ValueError(f"Unsupported severity distribution: {severity_distribution}")


def calculate_cvar(losses: np.ndarray, var_value: float) -> float:
    """Calculate CVaR / TVaR as the mean loss above the VaR threshold."""
    tail_losses = losses[losses >= var_value]

    if len(tail_losses) == 0:
        return float("nan")

    return float(tail_losses.mean())


# ============================================================
# Main simulation
# ============================================================

def main() -> None:
    model = load_selected_model(MODEL_PATH)

    frequency_distribution = str(model["frequency_distribution"]).lower()
    severity_distribution = str(model["severity_distribution"]).lower()

    if frequency_distribution != "poisson":
        raise ValueError(
            f"Unsupported frequency distribution: {frequency_distribution}"
        )

    lambda_per_exposure_year = float(model["lambda_per_exposure_year"])

    severity_param_1_name = str(model["severity_param_1_name"])
    severity_param_1_value = float(model["severity_param_1_value"])
    severity_param_2_name = str(model["severity_param_2_name"])
    severity_param_2_value = float(model["severity_param_2_value"])

    rng = np.random.default_rng(RANDOM_SEED)

    # In this simulation, we model annual aggregate loss for one exposure-year.
    # Expected annual claim count = lambda per exposure-year.
    #
    # Later, we can extend this to simulate the entire observed portfolio by
    # multiplying lambda by total portfolio exposure.
    simulated_claim_counts = rng.poisson(
        lam=lambda_per_exposure_year,
        size=N_SIMULATIONS
    )

    simulated_losses = np.zeros(N_SIMULATIONS, dtype=float)

    # Efficiently simulate only the severities that are needed.
    # We do not store every individual claim; only annual aggregate losses.
    total_simulated_claims = int(simulated_claim_counts.sum())

    all_severities = simulate_severities(
        rng=rng,
        severity_distribution=severity_distribution,
        n_claims=total_simulated_claims,
        param_1_name=severity_param_1_name,
        param_1_value=severity_param_1_value,
        param_2_name=severity_param_2_name,
        param_2_value=severity_param_2_value,
    )

    start_idx = 0
    for i, claim_count in enumerate(simulated_claim_counts):
        end_idx = start_idx + claim_count
        if claim_count > 0:
            simulated_losses[i] = all_severities[start_idx:end_idx].sum()
        start_idx = end_idx

    # ============================================================
    # Risk metrics
    # ============================================================

    expected_loss = float(simulated_losses.mean())
    std_loss = float(simulated_losses.std(ddof=1))
    median_loss = float(np.median(simulated_losses))
    max_loss = float(simulated_losses.max())

    percentile_rows = []
    summary = {
        "n_simulations": N_SIMULATIONS,
        "random_seed": RANDOM_SEED,
        "frequency_distribution": frequency_distribution,
        "lambda_per_exposure_year": lambda_per_exposure_year,
        "severity_distribution": severity_distribution,
        "severity_param_1_name": severity_param_1_name,
        "severity_param_1_value": severity_param_1_value,
        "severity_param_2_name": severity_param_2_name,
        "severity_param_2_value": severity_param_2_value,
        "expected_loss": expected_loss,
        "std_loss": std_loss,
        "median_loss": median_loss,
        "max_loss": max_loss,
        "mean_simulated_claim_count": float(simulated_claim_counts.mean()),
        "probability_zero_claims": float(np.mean(simulated_claim_counts == 0)),
        "probability_positive_loss": float(np.mean(simulated_losses > 0)),
    }

    for level in VAR_LEVELS:
        var_value = float(np.quantile(simulated_losses, level))
        cvar_value = calculate_cvar(simulated_losses, var_value)

        summary[f"var_{int(level * 1000) / 10:g}"] = var_value
        summary[f"cvar_{int(level * 1000) / 10:g}"] = cvar_value

        percentile_rows.append({
            "percentile": level,
            "var": var_value,
            "cvar": cvar_value,
            "tail_probability": 1 - level
        })

    simulation_summary = pd.DataFrame([summary])
    simulation_percentiles = pd.DataFrame(percentile_rows)

    simulation_summary.to_csv(
        TABLE_DIR / "simulation_summary.csv",
        index=False
    )

    simulation_percentiles.to_csv(
        TABLE_DIR / "simulation_percentiles.csv",
        index=False
    )

    # Save only a sample of the individual simulation results.
    sample_size = min(N_RESULTS_TO_SAVE, N_SIMULATIONS)
    sample_indices = rng.choice(N_SIMULATIONS, size=sample_size, replace=False)

    simulation_sample = pd.DataFrame({
        "simulation_id": sample_indices + 1,
        "claim_count": simulated_claim_counts[sample_indices],
        "annual_loss": simulated_losses[sample_indices],
    }).sort_values("simulation_id")

    simulation_sample.to_csv(
        TABLE_DIR / "simulation_results_sample.csv",
        index=False
    )

    # ============================================================
    # Diagnostic plots
    # ============================================================

    positive_losses = simulated_losses[simulated_losses > 0]

    plt.figure(figsize=(10, 6))
    if len(positive_losses) > 0:
        bins = np.logspace(
            np.log10(max(positive_losses.min(), 1e-6)),
            np.log10(positive_losses.max()),
            75
        )
        plt.hist(positive_losses, bins=bins)
        plt.xscale("log")
    else:
        plt.hist(simulated_losses, bins=50)

    plt.xlabel("Annual aggregate loss")
    plt.ylabel("Simulation count")
    plt.title("Simulated Annual Loss Distribution")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "simulated_annual_loss_distribution.png", dpi=150)
    plt.close()

    sorted_losses = np.sort(simulated_losses)
    ecdf = np.arange(1, N_SIMULATIONS + 1) / N_SIMULATIONS

    plt.figure(figsize=(10, 6))
    plt.plot(sorted_losses, ecdf)
    plt.xlabel("Annual aggregate loss")
    plt.ylabel("Empirical cumulative probability")
    plt.title("Simulated Annual Loss ECDF")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "simulated_annual_loss_ecdf.png", dpi=150)
    plt.close()

    # ============================================================
    # Console output
    # ============================================================

    print("\n=== Monte Carlo Portfolio Simulation ===")
    print(f"Simulations: {N_SIMULATIONS:,}")
    print(f"Frequency model: {frequency_distribution}")
    print(f"Lambda per exposure-year: {lambda_per_exposure_year:.6f}")
    print(f"Severity model: {severity_distribution}")

    print("\n=== Simulation Results ===")
    print(f"Expected loss: {expected_loss:,.2f}")
    print(f"Standard deviation: {std_loss:,.2f}")
    print(f"Median loss: {median_loss:,.2f}")
    print(f"Maximum simulated loss: {max_loss:,.2f}")
    print(f"Mean simulated claim count: {simulated_claim_counts.mean():.6f}")
    print(f"Probability of zero claims: {np.mean(simulated_claim_counts == 0):.4%}")
    print(f"Probability of positive loss: {np.mean(simulated_losses > 0):.4%}")

    print("\n=== Tail Risk Metrics ===")
    print(simulation_percentiles.to_string(index=False))

    print("\nSaved outputs to:")
    print(f"  Figures: {FIGURE_DIR}")
    print(f"  Tables:  {TABLE_DIR}")


if __name__ == "__main__":
    main()
