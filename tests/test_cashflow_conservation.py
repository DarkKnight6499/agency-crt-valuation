"""Unit test for collateral and tranche cash flow conservation identities."""

import os
import sys

# CONFIG: standalone paths and test inputs.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

TEST_SEED = 42
MAX_CONSERVATION_ERROR = 0.0001


if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from python.config import *


def test_cashflow_conservation():
    """Verify exact conservation of principal and credit write-downs across all months."""
    from python.pool_generator import generate_loan_pool, compute_pool_summary
    from python.cohort_model import get_scenario_definitions, compute_baseline_pool_cdr
    from python.cashflow_engine import simulate_monthly_cashflows

    pool_df = generate_loan_pool(seed=TEST_SEED, save_csv=False)
    summary = compute_pool_summary(pool_df)
    base_cdr = compute_baseline_pool_cdr(pool_df, COL_FICO, COL_ORIG_LTV, COL_CURRENT_BALANCE)

    scenarios = get_scenario_definitions()
    base_params = scenarios[SCENARIO_BASE]

    df_cf, cf_summary = simulate_monthly_cashflows(summary, base_params, base_cdr)

    total_pool_prin_reduction = (
        df_cf[COL_POOL_SCHED_PRIN].sum()
        + df_cf[COL_POOL_PREPAY_PRIN].sum()
        + df_cf[COL_POOL_RECOVERY].sum()
        + df_cf[COL_POOL_REALIZED_LOSS].sum()
    )
    initial_pool_upb = cf_summary["initial_pool_balance"]
    pool_diff = abs(total_pool_prin_reduction - initial_pool_upb)

    assert pool_diff < MAX_CONSERVATION_ERROR, (
        f"Pool cash flow mismatch: accounted {total_pool_prin_reduction} vs starting {initial_pool_upb}"
    )

    total_mezz_accounted = (
        df_cf[COL_MEZZ_PRIN].sum() + df_cf[COL_MEZZ_WRITEDOWN].sum()
    )
    initial_mezz_bal = cf_summary["initial_mezz_balance"]
    mezz_diff = abs(total_mezz_accounted - initial_mezz_bal)

    assert mezz_diff < MAX_CONSERVATION_ERROR, (
        f"Mezzanine tranche mismatch: accounted {total_mezz_accounted} vs starting {initial_mezz_bal}"
    )

    print("Cash flow conservation tests passed successfully.")
    print(f"  Pool balance accounted: ${total_pool_prin_reduction:,.2f} / ${initial_pool_upb:,.2f} (diff ${pool_diff:.4f})")
    print(f"  Mezz balance accounted: ${total_mezz_accounted:,.2f} / ${initial_mezz_bal:,.2f} (diff ${mezz_diff:.4f})")


if __name__ == "__main__":
    test_cashflow_conservation()

