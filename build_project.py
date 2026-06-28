"""
build_project.py
Project: Actuarial Motor Insurance Pricing Analytics

Purpose:
    Orchestrate the full analytics pipeline from source data through
    Power BI-ready dataset exports.

Run from the project root:
    python build_project.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "database" / "actuarial_risk.duckdb"
POWERBI_DATASET_DIR = PROJECT_ROOT / "powerbi" / "datasets"
POWERBI_DASHBOARD_DIR = PROJECT_ROOT / "powerbi" / "dashboards"


@dataclass
class PipelineStep:
    """One command-line step in the build pipeline."""
    name: str
    command: list[str]


def run_step(step_number: int, total_steps: int, step: PipelineStep) -> None:
    """Run one pipeline step and stop the build if it fails."""
    print()
    print("=" * 72)
    print(f"Step {step_number}/{total_steps}: {step.name}")
    print("=" * 72)
    print("Command:")
    print(" ".join(step.command))
    print()

    start_time = time.perf_counter()

    try:
        subprocess.run(
            step.command,
            cwd=PROJECT_ROOT,
            check=True,
        )
    except FileNotFoundError as exc:
        print()
        print(f"ERROR: Command not found: {step.command[0]}")
        print("Make sure the required program is installed and available on PATH.")
        raise SystemExit(1) from exc
    except subprocess.CalledProcessError as exc:
        print()
        print(f"ERROR: Step failed with exit code {exc.returncode}.")
        print(f"Failed step: {step.name}")
        raise SystemExit(exc.returncode) from exc

    elapsed = time.perf_counter() - start_time
    print()
    print(f"Completed: {step.name} ({elapsed:.2f} seconds)")


def main() -> None:
    """Run the full project pipeline."""
    POWERBI_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    POWERBI_DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    pipeline_steps = [
        PipelineStep(
            name="Build DuckDB warehouse and analytical views",
            command=[
                "duckdb",
                str(DB_PATH),
                "-c",
                ".read sql/build_actuarial_risk_model.sql",
            ],
        ),
        PipelineStep(
            name="Run frequency/severity modeling",
            command=[
                sys.executable,
                "python/07_frequency_severity_modeling.py",
            ],
        ),
        PipelineStep(
            name="Run Monte Carlo pricing simulation",
            command=[
                sys.executable,
                "python/08_annual_loss_simulation.py",
            ],
        ),
        PipelineStep(
            name="Run scenario-based pricing",
            command=[
                sys.executable,
                "python/09_pricing_scenarios.py",
            ],
        ),
        PipelineStep(
            name="Prepare curated results catalog",
            command=[
                sys.executable,
                "python/10_prepare_results_catalog.py",
            ],
        ),
        PipelineStep(
            name="Build Power BI mart inside DuckDB",
            command=[
                "duckdb",
                str(DB_PATH),
                "-c",
                ".read sql/07_create_powerbi_mart.sql",
            ],
        ),
        PipelineStep(
            name="Export Power BI datasets",
            command=[
                sys.executable,
                "python/11_export_powerbi_datasets.py",
            ],
        ),
    ]

    print()
    print("Actuarial Motor Insurance Risk Analysis")
    print("Full Project Build")
    print("-" * 72)
    print(f"Project root:        {PROJECT_ROOT}")
    print(f"DuckDB file:         {DB_PATH}")
    print(f"Power BI datasets:   {POWERBI_DATASET_DIR}")
    print(f"Power BI dashboards: {POWERBI_DASHBOARD_DIR}")

    total_start = time.perf_counter()

    for index, step in enumerate(pipeline_steps, start=1):
        run_step(index, len(pipeline_steps), step)

    total_elapsed = time.perf_counter() - total_start

    print()
    print("=" * 72)
    print("Build completed successfully.")
    print(f"Total runtime: {total_elapsed:.2f} seconds")
    print("=" * 72)
    print()
    print("Generated assets:")
    print("  DuckDB database:   database/actuarial_risk.duckdb")
    print("  Working outputs:   outputs/")
    print("  Model artifacts:   models/")
    print("  Curated results:   results/")
    print("  Power BI mart:     mart schema inside database/actuarial_risk.duckdb")
    print("  Power BI datasets: powerbi/datasets/")
    print("  Power BI reports:  powerbi/dashboards/")


if __name__ == "__main__":
    main()
