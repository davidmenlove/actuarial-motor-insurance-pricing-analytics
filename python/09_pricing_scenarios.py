"""
09_pricing_scenarios.py
Project: Actuarial Motor Insurance Risk Analysis

Purpose:
    Compare pure premium indications under multiple economic scenarios.

Inputs:
    models/selected_frequency_severity_model.csv
    assumptions/economic_assumptions.csv
    assumptions/inflation_scenarios.csv

Outputs:
    outputs/tables/pricing_scenario_summary.csv
    outputs/tables/pricing_scenario_percentiles.csv
    outputs/figures/pricing_expected_loss_by_scenario.png
    outputs/figures/pricing_var_by_scenario.png
    outputs/figures/pricing_cvar_by_scenario.png

Run from the project root:
    python python/09_pricing_scenarios.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ASSUMPTION_DIR = PROJECT_ROOT / "assumptions"
MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

SELECTED_MODEL_PATH = MODEL_DIR / "selected_frequency_severity_model.csv"
ECONOMIC_ASSUMPTIONS_PATH = ASSUMPTION_DIR / "economic_assumptions.csv"
INFLATION_SCENARIOS_PATH = ASSUMPTION_DIR / "inflation_scenarios.csv"

N_SIMULATIONS = 100_000
RANDOM_SEED = 42
VAR_LEVELS = [0.95, 0.99, 0.995]


def load_single_row_csv(path: Path) -> dict:
    """Load a one-row CSV as a dictionary."""
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_csv(path)

    if len(df) != 1:
        raise ValueError(f"Expected exactly one row in {path}, found {len(df)}.")

    return df.iloc[0].to_dict()


def calculate_cvar(losses: np.ndarray, var_value: float) -> float:
    """Calculate CVaR / TVaR as average loss at or above VaR."""
    tail_losses = losses[losses >= var_value]

    if len(tail_losses) == 0:
        return float("nan")

    return float(tail_losses.mean())


def simulate_losses(
    rng: np.random.Generator,
    n_simulations: int,
    lambda_per_exposure_year: float,
    severity_distribution: str,
    severity_param_1_name: str,
    severity_param_1_value: float,
    severity_param_2_name: str,
    severity_param_2_value: float,
    severity_multiplier: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate one-policy annual losses under a scenario."""
    claim_counts = rng.poisson(
        lam=lambda_per_exposure_year,
        size=n_simulations
    )

    losses = np.zeros(n_simulations, dtype=float)
    total_claims = int(claim_counts.sum())

    if total_claims == 0:
        return claim_counts, losses

    params = {
        severity_param_1_name: severity_param_1_value,
        severity_param_2_name: severity_param_2_value,
    }

    severity_distribution = severity_distribution.lower()

    if severity_distribution == "lognormal":
        sigma = float(params["sigma"])
        mu = float(params["mu"])
        severities = rng.lognormal(mean=mu, sigma=sigma, size=total_claims)

    elif severity_distribution == "gamma":
        alpha = float(params["shape_alpha"])
        theta = float(params["scale_theta"])
        severities = rng.gamma(shape=alpha, scale=theta, size=total_claims)

    else:
        raise ValueError(f"Unsupported severity distribution: {severity_distribution}")

    severities = severities * severity_multiplier

    start_idx = 0
    for i, count in enumerate(claim_counts):
        end_idx = start_idx + count
        if count > 0:
            losses[i] = severities[start_idx:end_idx].sum()
        start_idx = end_idx

    return claim_counts, losses


def get_general_inflation_scenarios(inflation_df: pd.DataFrame) -> pd.DataFrame:
    """
    Use the 'general' claim type as the default pricing inflation curve.

    This keeps the pricing scenario model simple and transparent.
    Later, this could be extended to claim-type-weighted inflation.
    """
    general = inflation_df[
        inflation_df["claim_type"].str.lower() == "general"
    ].copy()

    if general.empty:
        raise ValueError(
            "No claim_type='general' rows found in inflation_scenarios.csv."
        )

    return general


def main() -> None:
    selected_model = load_single_row_csv(SELECTED_MODEL_PATH)

    if not ECONOMIC_ASSUMPTIONS_PATH.exists():
        raise FileNotFoundError(f"Missing assumptions file: {ECONOMIC_ASSUMPTIONS_PATH}")

    if not INFLATION_SCENARIOS_PATH.exists():
        raise FileNotFoundError(f"Missing assumptions file: {INFLATION_SCENARIOS_PATH}")

    economic_df = pd.read_csv(ECONOMIC_ASSUMPTIONS_PATH)
    inflation_df = pd.read_csv(INFLATION_SCENARIOS_PATH)

    general_inflation = get_general_inflation_scenarios(inflation_df)

    max_projection_year = general_inflation["projection_year"].max()

    scenario_inputs = (
        general_inflation[general_inflation["projection_year"] == max_projection_year]
        .merge(
            economic_df,
            on=["scenario_id", "scenario_name"],
            how="left"
        )
        .copy()
    )

    if scenario_inputs["frequency_trend_rate"].isna().any():
        missing = scenario_inputs[scenario_inputs["frequency_trend_rate"].isna()]
        raise ValueError(
            "Some inflation scenarios do not match economic assumptions:\n"
            f"{missing[['scenario_id', 'scenario_name']].to_string(index=False)}"
        )

    base_scenario = "BASE"

    if base_scenario not in set(scenario_inputs["scenario_id"]):
        raise ValueError("BASE scenario not found. Expected scenario_id='BASE'.")

    frequency_distribution = str(selected_model["frequency_distribution"]).lower()
    severity_distribution = str(selected_model["severity_distribution"]).lower()

    if frequency_distribution != "poisson":
        raise ValueError(f"Unsupported frequency model: {frequency_distribution}")

    base_lambda = float(selected_model["lambda_per_exposure_year"])

    severity_param_1_name = str(selected_model["severity_param_1_name"])
    severity_param_1_value = float(selected_model["severity_param_1_value"])
    severity_param_2_name = str(selected_model["severity_param_2_name"])
    severity_param_2_value = float(selected_model["severity_param_2_value"])

    rng = np.random.default_rng(RANDOM_SEED)

    summary_rows = []
    percentile_rows = []

    for _, scenario in scenario_inputs.sort_values("scenario_id").iterrows():
        scenario_id = scenario["scenario_id"]
        scenario_name = scenario["scenario_name"]

        frequency_multiplier = 1 + float(scenario["frequency_trend_rate"])
        scenario_lambda = base_lambda * frequency_multiplier

        severity_multiplier = float(scenario["cumulative_base_inflation_factor"])

        claim_counts, losses = simulate_losses(
            rng=rng,
            n_simulations=N_SIMULATIONS,
            lambda_per_exposure_year=scenario_lambda,
            severity_distribution=severity_distribution,
            severity_param_1_name=severity_param_1_name,
            severity_param_1_value=severity_param_1_value,
            severity_param_2_name=severity_param_2_name,
            severity_param_2_value=severity_param_2_value,
            severity_multiplier=severity_multiplier,
        )

        expected_loss = float(losses.mean())
        std_loss = float(losses.std(ddof=1))
        median_loss = float(np.median(losses))
        probability_zero_claims = float(np.mean(claim_counts == 0))
        probability_positive_loss = float(np.mean(losses > 0))

        summary_row = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "projection_year": int(scenario["projection_year"]),
            "n_simulations": N_SIMULATIONS,
            "frequency_multiplier": frequency_multiplier,
            "severity_multiplier": severity_multiplier,
            "lambda_per_exposure_year": scenario_lambda,
            "annual_inflation_rate": float(scenario["annual_inflation_rate"]),
            "frequency_trend_rate": float(scenario["frequency_trend_rate"]),
            "severity_trend_rate": float(scenario["severity_trend_rate"]),
            "expected_loss": expected_loss,
            "std_loss": std_loss,
            "median_loss": median_loss,
            "probability_zero_claims": probability_zero_claims,
            "probability_positive_loss": probability_positive_loss,
        }

        for level in VAR_LEVELS:
            var_value = float(np.quantile(losses, level))
            cvar_value = calculate_cvar(losses, var_value)

            metric_suffix = f"{level * 100:g}".replace(".", "_")
            summary_row[f"var_{metric_suffix}"] = var_value
            summary_row[f"cvar_{metric_suffix}"] = cvar_value

            percentile_rows.append({
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "percentile": level,
                "var": var_value,
                "cvar": cvar_value,
                "tail_probability": 1 - level,
            })

        summary_rows.append(summary_row)

    scenario_summary = pd.DataFrame(summary_rows)

    base_expected_loss = float(
        scenario_summary.loc[
            scenario_summary["scenario_id"] == base_scenario,
            "expected_loss"
        ].iloc[0]
    )

    scenario_summary["expected_loss_change_from_base"] = (
        scenario_summary["expected_loss"] - base_expected_loss
    )

    scenario_summary["expected_loss_pct_change_from_base"] = (
        scenario_summary["expected_loss"] / base_expected_loss - 1
    )

    scenario_percentiles = pd.DataFrame(percentile_rows)

    scenario_summary.to_csv(
        TABLE_DIR / "pricing_scenario_summary.csv",
        index=False
    )

    scenario_percentiles.to_csv(
        TABLE_DIR / "pricing_scenario_percentiles.csv",
        index=False
    )

    plot_df = scenario_summary.sort_values("expected_loss")

    plt.figure(figsize=(10, 6))
    plt.bar(plot_df["scenario_name"], plot_df["expected_loss"])
    plt.xlabel("Scenario")
    plt.ylabel("Expected loss / pure premium")
    plt.title("Expected Pure Premium by Economic Scenario")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "pricing_expected_loss_by_scenario.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, 6))
    plt.bar(plot_df["scenario_name"], plot_df["var_99_5"])
    plt.xlabel("Scenario")
    plt.ylabel("99.5% VaR")
    plt.title("Pricing Tail Risk by Economic Scenario")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "pricing_var_by_scenario.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, 6))
    plt.bar(plot_df["scenario_name"], plot_df["cvar_99_5"])
    plt.xlabel("Scenario")
    plt.ylabel("99.5% CVaR")
    plt.title("Pricing Tail Severity by Economic Scenario")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "pricing_cvar_by_scenario.png", dpi=150)
    plt.close()

    display_cols = [
        "scenario_id",
        "scenario_name",
        "expected_loss",
        "expected_loss_pct_change_from_base",
        "var_99",
        "cvar_99",
        "var_99_5",
        "cvar_99_5",
    ]

    print("\n=== Scenario-Based Pricing Summary ===")
    print(scenario_summary[display_cols].to_string(index=False))

    print("\nSaved outputs to:")
    print(f"  Tables:  {TABLE_DIR}")
    print(f"  Figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
