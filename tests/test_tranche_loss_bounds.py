"""Unit test for mezzanine tranche loss bounds and non-negativity."""

import os
import sys

# CONFIG: standalone paths and test inputs.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

TEST_SEED = 42
EXTREME_CDR_MULT = 5.0
STRESS_CPR_MULTIPLIER = 0.5
TOLERANCE_EPSILON = 1e-4


if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from python.config import *


def test_tranche_loss_bounds():
    """Verify that credit write-downs are strictly bounded by initial tranche thickness."""
    from python.pool_generator import generate_loan_pool, compute_pool_summary
    from python.cohort_model import get_scenario_definitions, compute_baseline_pool_cdr
    from python.cashflow_engine import simulate_monthly_cashflows

    pool_df = generate_loan_pool(seed=TEST_SEED, save_csv=False)
    summary = compute_pool_summary(pool_df)
    base_cdr = compute_baseline_pool_cdr(pool_df, COL_FICO, COL_ORIG_LTV, COL_CURRENT_BALANCE)

    scenarios = get_scenario_definitions()
    stress_params = scenarios[SCENARIO_HPA_DOWN]

    df_cf, cf_summary = simulate_monthly_cashflows(
        summary, stress_params, base_cdr, cpr_mult=STRESS_CPR_MULTIPLIER, cdr_mult=EXTREME_CDR_MULT
    )

    initial_mezz_bal = cf_summary["initial_mezz_balance"]
    total_mezz_writedown = cf_summary["total_mezz_writedown"]

    assert total_mezz_writedown <= initial_mezz_bal + TOLERANCE_EPSILON, (
        f"Mezzanine loss {total_mezz_writedown} exceeded tranche size {initial_mezz_bal}"
    )

    min_ending_bal = df_cf[COL_MEZZ_END_BAL].min()
    assert min_ending_bal >= -TOLERANCE_EPSILON, (
        f"Found negative tranche balance: {min_ending_bal}"
    )

    sub_dollar_threshold = summary["total_current_upb"] * ATTACHMENT_POINT
    pre_exhaustion_rows = df_cf[df_cf[COL_CUM_POOL_LOSS] <= sub_dollar_threshold]

    if len(pre_exhaustion_rows) > 0:
        max_mezz_loss_before_exhaustion = pre_exhaustion_rows[COL_CUM_MEZZ_LOSS].max()
        assert max_mezz_loss_before_exhaustion <= TOLERANCE_EPSILON, (
            f"Premature tranche write-down before equity exhaustion: {max_mezz_loss_before_exhaustion}"
        )

    print("Tranche loss boundary tests passed successfully.")
    print(f"  Initial tranche size: ${initial_mezz_bal:,.2f}")
    print(f"  Stress write-down: ${total_mezz_writedown:,.2f} ({total_mezz_writedown/initial_mezz_bal*100:.2f}%)")
    print(f"  Minimum tranche balance: ${min_ending_bal:.2f}")
    print(f"  Subordination threshold protected: ${sub_dollar_threshold:,.2f}")


if __name__ == "__main__":
    test_tranche_loss_bounds()

