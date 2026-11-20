"""Regenerate synthetic data, cash flows, valuations, memo, and all plain tests."""

import importlib
import inspect
import os
from pathlib import Path
from python.config import *
from python.pool_generator import generate_loan_pool, compute_pool_summary
from python.cohort_model import compute_baseline_pool_cdr
from python.pricing_engine import (
    run_scenario_valuation, generate_price_yield_table, generate_sensitivity_grid,
    plot_pricing_curves, write_valuation_memo,
)

# CONFIG: shared model inputs are imported from python.config.
TEST_DIRECTORY = Path(BASE_DIR) / "tests"
TEST_PATTERN = "test_*.py"


def run_tests():
    """Discover every plain assertion test, including future regression files."""
    count = 0
    for path in sorted(TEST_DIRECTORY.glob(TEST_PATTERN)):
        module = importlib.import_module(f"tests.{path.stem}")
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("test_") and function.__module__ == module.__name__:
                print(f"Running {path.name}:{name}")
                function()
                count += 1
    print(f"Passed {count} tests.")
    return count


def main():
    """Execute the deterministic synthetic valuation pipeline."""
    print("SYNTHETIC CRT-style valuation. No real loan or market data.")
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    pool = generate_loan_pool(seed=SEED, save_csv=True)
    summary = compute_pool_summary(pool)
    print(f"Pool UPB ${summary['total_current_upb']:,.2f}; WAC {summary['wac']:.6%}")
    base_cdr = compute_baseline_pool_cdr(pool)
    print(f"Assumed weighted annual CDR {base_cdr:.6%}")
    scenarios, cashflows = run_scenario_valuation(summary, base_cdr)
    print(scenarios.to_string(index=False))
    base_cashflows = cashflows[SCENARIO_BASE][COL_MEZZ_TOTAL_CF].to_numpy()
    initial_mezz = summary['total_current_upb'] * (DETACHMENT_POINT - ATTACHMENT_POINT)
    price_yield = generate_price_yield_table(base_cashflows, initial_mezz, BASE_BENCHMARK_RATE)
    grid = generate_sensitivity_grid(summary, base_cdr)
    plot_pricing_curves(price_yield, cashflows, grid)
    write_valuation_memo(scenarios, price_yield, grid, summary)
    run_tests()
    print("Synthetic outputs regenerated; all discovered tests passed.")


if __name__ == "__main__":
    main()
