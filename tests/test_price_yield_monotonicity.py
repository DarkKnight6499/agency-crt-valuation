"""Unit test for price and yield inverse monotonicity and duration positivity."""

import os
import sys

# CONFIG: standalone paths and test inputs.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

TEST_SEED = 42
TEST_YIELDS = [0.040, 0.055, 0.070, 0.085, 0.100, 0.120]
MAX_PERMITTED_WAL_YEARS = 30.0
TEST_BASE_YIELD = 0.075


if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from python.config import *


def test_price_yield_monotonicity():
    """Verify that bond price falls strictly monotonically as discount yield increases."""
    from python.pool_generator import generate_loan_pool, compute_pool_summary
    from python.cohort_model import get_scenario_definitions, compute_baseline_pool_cdr
    from python.cashflow_engine import simulate_monthly_cashflows
    from python.pricing_engine import compute_present_value, compute_wal, compute_duration_and_convexity

    pool_df = generate_loan_pool(seed=TEST_SEED, save_csv=False)
    summary = compute_pool_summary(pool_df)
    base_cdr = compute_baseline_pool_cdr(pool_df, COL_FICO, COL_ORIG_LTV, COL_CURRENT_BALANCE)

    scenarios = get_scenario_definitions()
    base_params = scenarios[SCENARIO_BASE]

    df_cf, cf_summary = simulate_monthly_cashflows(summary, base_params, base_cdr)
    cfs = df_cf[COL_MEZZ_TOTAL_CF].to_numpy()
    prins = df_cf[COL_MEZZ_PRIN].to_numpy()

    pv_previous = float("inf")
    for yld in TEST_YIELDS:
        pv_current = compute_present_value(cfs, yld)
        assert pv_current < pv_previous, (
            f"Price failed to fall: yield {yld:.3f} gave PV {pv_current} vs previous {pv_previous}"
        )
        pv_previous = pv_current

    duration, convexity = compute_duration_and_convexity(cfs, TEST_BASE_YIELD)
    assert duration > 0.0, f"Modified duration must be positive, got {duration}"
    assert convexity > 0.0, f"Convexity for positive cash flows must be positive, got {convexity}"

    wal = compute_wal(prins)
    assert 0.0 < wal <= MAX_PERMITTED_WAL_YEARS, (
        f"WAL out of bounds: {wal} years"
    )

    print("Price yield monotonicity and duration tests passed successfully.")
    print(f"  Duration: {duration:.2f} years, Convexity: {convexity:.2f}")
    print(f"  Weighted Average Life: {wal:.2f} years")


if __name__ == "__main__":
    test_price_yield_monotonicity()

