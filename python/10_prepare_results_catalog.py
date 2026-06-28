"""
10_prepare_results_catalog.py
Project: Actuarial Motor Insurance Risk Analysis

Purpose:
    Create a polished results folder with numbered figures, copied result tables,
    and a Markdown catalog of captions for GitHub documentation.

Inputs:
    outputs/figures/
    outputs/tables/
    models/

Outputs:
    results/figures/
    results/tables/
    results/model_artifacts/
    results/results_catalog.md

Run from the project root:
    python python/10_prepare_results_catalog.py
"""

from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_FIGURES = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_TABLES = PROJECT_ROOT / "outputs" / "tables"
MODELS_DIR = PROJECT_ROOT / "models"

RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_FIGURES = RESULTS_DIR / "figures"
RESULTS_TABLES = RESULTS_DIR / "tables"
RESULTS_MODELS = RESULTS_DIR / "model_artifacts"

for folder in [RESULTS_FIGURES, RESULTS_TABLES, RESULTS_MODELS]:
    folder.mkdir(parents=True, exist_ok=True)


FIGURE_CATALOG = [
    {
        "source": "frequency_observed_vs_poisson.png",
        "target": "figure_01_observed_vs_poisson_frequency.png",
        "title": "Figure 1. Observed vs. Poisson Claim Frequency",
        "caption": (
            "Comparison of observed claim counts per policy exposure-year against "
            "expected counts from the fitted Poisson frequency model."
        ),
    },
    {
        "source": "severity_histogram_log_bins.png",
        "target": "figure_02_claim_severity_histogram.png",
        "title": "Figure 2. Claim Severity Distribution",
        "caption": (
            "Distribution of observed claim payments using log-spaced bins. "
            "The distribution is highly right-skewed, which is typical of insurance severity data."
        ),
    },
    {
        "source": "severity_fitted_distributions.png",
        "target": "figure_03_severity_fitted_distributions.png",
        "title": "Figure 3. Observed Severity vs. Fitted Distributions",
        "caption": (
            "Observed claim severity compared with fitted Gamma and Lognormal probability density functions."
        ),
    },
    {
        "source": "severity_empirical_cdf.png",
        "target": "figure_04_severity_empirical_cdf.png",
        "title": "Figure 4. Empirical CDF of Claim Severity",
        "caption": (
            "Empirical cumulative distribution of claim payments, showing the concentration "
            "of smaller claims and the long right tail of large losses."
        ),
    },
    {
        "source": "severity_qq_lognormal.png",
        "target": "figure_05_lognormal_qq_plot.png",
        "title": "Figure 5. Lognormal Severity QQ Plot",
        "caption": (
            "QQ plot comparing observed claim payments with the fitted Lognormal severity model."
        ),
    },
    {
        "source": "severity_qq_gamma.png",
        "target": "figure_06_gamma_qq_plot.png",
        "title": "Figure 6. Gamma Severity QQ Plot",
        "caption": (
            "QQ plot comparing observed claim payments with the fitted Gamma severity model."
        ),
    },
    {
        "source": "simulated_annual_loss_distribution.png",
        "target": "figure_07_simulated_policy_loss_distribution.png",
        "title": "Figure 7. Simulated Annual Loss Distribution",
        "caption": (
            "Monte Carlo distribution of annual aggregate loss for one insured exposure-year."
        ),
    },
    {
        "source": "simulated_annual_loss_ecdf.png",
        "target": "figure_08_simulated_policy_loss_ecdf.png",
        "title": "Figure 8. Simulated Annual Loss ECDF",
        "caption": (
            "Empirical CDF of simulated annual losses for one insured exposure-year. "
            "The large jump at zero reflects the high probability of no claims."
        ),
    },
    {
        "source": "pricing_expected_loss_by_scenario.png",
        "target": "figure_09_expected_pure_premium_by_scenario.png",
        "title": "Figure 9. Expected Pure Premium by Economic Scenario",
        "caption": (
            "Scenario-based pricing comparison showing how expected pure premium changes "
            "under different inflation and trend assumptions."
        ),
    },
    {
        "source": "pricing_var_by_scenario.png",
        "target": "figure_10_pricing_var_by_scenario.png",
        "title": "Figure 10. Pricing VaR by Economic Scenario",
        "caption": (
            "Comparison of 99.5% Value-at-Risk across economic scenarios for one insured exposure-year."
        ),
    },
    {
        "source": "pricing_cvar_by_scenario.png",
        "target": "figure_11_pricing_cvar_by_scenario.png",
        "title": "Figure 11. Pricing CVaR by Economic Scenario",
        "caption": (
            "Comparison of 99.5% Conditional Value-at-Risk across economic scenarios, "
            "showing expected loss severity in the extreme tail."
        ),
    },
]


TABLES_TO_COPY = [
    "frequency_model_summary.csv",
    "frequency_observed_vs_poisson.csv",
    "severity_summary.csv",
    "simulation_summary.csv",
    "simulation_percentiles.csv",
    "simulation_results_sample.csv",
    "pricing_scenario_summary.csv",
    "pricing_scenario_percentiles.csv",
]

MODELS_TO_COPY = [
    "candidate_models.csv",
    "selected_frequency_severity_model.csv",
]


def copy_if_exists(source: Path, target: Path) -> bool:
    """Copy a file if it exists. Return True if copied."""
    if not source.exists():
        return False

    shutil.copy2(source, target)
    return True


def main() -> None:
    catalog_lines = [
        "# Results Catalog",
        "",
        "This catalog summarizes the primary figures and tables generated by the actuarial pricing pipeline.",
        "",
        "## Figures",
        "",
    ]

    missing_figures = []

    for item in FIGURE_CATALOG:
        source = OUTPUT_FIGURES / item["source"]
        target = RESULTS_FIGURES / item["target"]

        copied = copy_if_exists(source, target)

        if not copied:
            missing_figures.append(item["source"])
            continue

        relative_path = target.relative_to(RESULTS_DIR).as_posix()

        catalog_lines.extend([
            f"### {item['title']}",
            "",
            f"![{item['title']}]({relative_path})",
            "",
            item["caption"],
            "",
        ])

    catalog_lines.extend([
        "## Tables",
        "",
    ])

    missing_tables = []

    for table_name in TABLES_TO_COPY:
        source = OUTPUT_TABLES / table_name
        target = RESULTS_TABLES / table_name

        copied = copy_if_exists(source, target)

        if copied:
            relative_path = target.relative_to(RESULTS_DIR).as_posix()
            catalog_lines.append(f"- `{relative_path}`")
        else:
            missing_tables.append(table_name)

    catalog_lines.extend([
        "",
        "## Model Artifacts",
        "",
    ])

    missing_models = []

    for model_name in MODELS_TO_COPY:
        source = MODELS_DIR / model_name
        target = RESULTS_MODELS / model_name

        copied = copy_if_exists(source, target)

        if copied:
            relative_path = target.relative_to(RESULTS_DIR).as_posix()
            catalog_lines.append(f"- `{relative_path}`")
        else:
            missing_models.append(model_name)

    catalog_lines.append("")

    if missing_figures or missing_tables or missing_models:
        catalog_lines.extend([
            "## Missing Files",
            "",
            "The following files were not found when preparing the results catalog:",
            "",
        ])

        for name in missing_figures:
            catalog_lines.append(f"- Missing figure: `{name}`")

        for name in missing_tables:
            catalog_lines.append(f"- Missing table: `{name}`")

        for name in missing_models:
            catalog_lines.append(f"- Missing model artifact: `{name}`")

        catalog_lines.append("")

    catalog_path = RESULTS_DIR / "results_catalog.md"
    catalog_path.write_text("\n".join(catalog_lines), encoding="utf-8")

    print("Prepared polished results folder:")
    print(f"  {RESULTS_DIR}")

    if missing_figures or missing_tables or missing_models:
        print("\nSome files were missing. See results/results_catalog.md for details.")
    else:
        print("All expected results were copied successfully.")


if __name__ == "__main__":
    main()
