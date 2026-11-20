"""Regression checks for cash allocation, behavioral models, and solver failures."""

import os
import sys
import numpy as np

# CONFIG: standalone import path and test tolerances.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABS_TOLERANCE = 0.0001
REL_TOLERANCE = 1e-12
EXTREME_CDR_MULTIPLIER = 20.0
ZERO_RATE_BALANCE = 1200.0
ZERO_RATE_TERM = 12
ZERO_RATE_AGE = 3
EXPECTED_ZERO_RATE_BALANCE = 900.0
INVALID_TARGET_PRICE = 1e20
INVALID_FLOW = [float("nan")]

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from python.config import *
from python.pool_generator import generate_loan_pool, compute_pool_summary, calculate_amortized_balance
from python.cohort_model import compute_baseline_pool_cdr, get_scenario_definitions, compute_cpr_vector, compute_cdr_vector, compute_pool_severity
from python.cashflow_engine import simulate_monthly_cashflows
from python.pricing_engine import solve_yield_for_price


def test_monthly_conservation_all_scenarios():
    """Verify cash principal plus loss, and all three capital tiers, every month."""
    pool = generate_loan_pool(save_csv=False)
    summary = compute_pool_summary(pool)
    cdr = compute_baseline_pool_cdr(pool)
    scenarios = list(get_scenario_definitions().values())
    scenarios.append(dict(scenarios[-1], cdr_multiplier=EXTREME_CDR_MULTIPLIER))
    maximum_error = 0.0
    for params in scenarios:
        flows, result = simulate_monthly_cashflows(summary, params, cdr)
        actual_reduction = flows[COL_POOL_BEG_BAL] - flows[COL_POOL_END_BAL]
        expected_reduction = flows[COL_POOL_PRIN] + flows[COL_POOL_REALIZED_LOSS]
        np.testing.assert_allclose(actual_reduction, expected_reduction, rtol=REL_TOLERANCE, atol=ABS_TOLERANCE)
        allocated = flows[COL_MEZZ_PRIN] + flows[COL_SENIOR_PRIN] + flows[COL_JUNIOR_PRIN]
        np.testing.assert_allclose(allocated, flows[COL_POOL_PRIN], rtol=REL_TOLERANCE, atol=ABS_TOLERANCE)
        balances = flows[COL_MEZZ_END_BAL] + flows[COL_SENIOR_END] + flows[COL_JUNIOR_END]
        np.testing.assert_allclose(balances, flows[COL_POOL_END_BAL], rtol=REL_TOLERANCE, atol=ABS_TOLERANCE)
        np.testing.assert_allclose(flows[COL_POOL_RECOVERY] + flows[COL_POOL_REALIZED_LOSS], flows[COL_POOL_DEFAULT_BAL], atol=ABS_TOLERANCE)
        np.testing.assert_allclose(flows[COL_POOL_TOTAL_CF], flows[COL_POOL_PRIN] + flows[COL_POOL_INTEREST], atol=ABS_TOLERANCE)
        np.testing.assert_allclose(flows[COL_POOL_INTEREST], flows[COL_POOL_BEG_BAL] * summary['wac'] / MONTHS_PER_YEAR, atol=ABS_TOLERANCE)
        assert np.all(np.isfinite(flows.to_numpy()))
        assert flows.to_numpy().min() >= -ABS_TOLERANCE
        error = abs(float(expected_reduction.sum()) - result['initial_pool_balance'])
        maximum_error = max(maximum_error, error)
        assert error < ABS_TOLERANCE
        assert abs(float(flows[COL_MEZZ_PRIN].sum() + flows[COL_MEZZ_WRITEDOWN].sum()) - result['initial_mezz_balance']) < ABS_TOLERANCE
    print(f"Five scenario conservation checks passed; largest lifetime error ${maximum_error:.9f}.")


def test_burnout_severity_and_reproducibility():
    """Check implemented behavior rather than documentation claims."""
    first = generate_loan_pool(save_csv=False)
    second = generate_loan_pool(save_csv=False)
    assert first.equals(second)
    summary = compute_pool_summary(first)
    warm = int(np.ceil(summary['warm']))
    params = get_scenario_definitions()[SCENARIO_BASE]
    flows, _ = simulate_monthly_cashflows(summary, params, compute_baseline_pool_cdr(first))
    prior_prepay = (flows[COL_POOL_PREPAY_PRIN].cumsum() - flows[COL_POOL_PREPAY_PRIN]) / summary['total_current_upb']
    expected = compute_cpr_vector(summary['wac'], params[COL_MORTGAGE_RATE], summary['wala'], warm, prior_prepay.to_numpy())
    static = compute_cpr_vector(summary['wac'], params[COL_MORTGAGE_RATE], summary['wala'], warm, np.zeros(warm))
    np.testing.assert_allclose(flows[COL_CPR], expected)
    assert np.any(expected < static)
    assert compute_pool_severity(first, HOME_PRICE_STRESS) > compute_pool_severity(first)
    higher_ltv = first.copy()
    higher_ltv[COL_ORIG_LTV] = higher_ltv[COL_ORIG_LTV] / (1.0 + HOME_PRICE_STRESS)
    assert compute_pool_severity(higher_ltv) > compute_pool_severity(first)
    assert np.all(compute_cdr_vector(1.0, EXTREME_CDR_MULTIPLIER, summary['wala'], warm) <= CDR_CAP)
    print("Reproducibility, live burnout, LTV severity, and CDR cap passed.")


def test_zero_rates_and_solver_rejection():
    """Reject silent solver bounds and support zero-coupon amortization."""
    balance = calculate_amortized_balance(np.array([ZERO_RATE_BALANCE]), np.array([0.0]), ZERO_RATE_TERM, np.array([ZERO_RATE_AGE]))
    np.testing.assert_allclose(balance, EXPECTED_ZERO_RATE_BALANCE)
    pool = generate_loan_pool(save_csv=False)
    summary = compute_pool_summary(pool)
    flows, result = simulate_monthly_cashflows(summary, get_scenario_definitions()[SCENARIO_BASE],
                                               compute_baseline_pool_cdr(pool), cpr_mult=0.0, cdr_mult=0.0)
    assert float(flows[COL_POOL_PREPAY_PRIN].sum()) == 0.0
    assert float(flows[COL_POOL_DEFAULT_BAL].sum()) == 0.0
    assert abs(float(flows[COL_POOL_PRIN].sum()) - result['initial_pool_balance']) < ABS_TOLERANCE
    for cashflows, target in (([ZERO_RATE_BALANCE], INVALID_TARGET_PRICE), (INVALID_FLOW, PRICE_PAR), ([0.0], PRICE_PAR)):
        try:
            solve_yield_for_price(cashflows, target, ZERO_RATE_BALANCE)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid or unbracketed yield silently accepted")
    print("Zero-coupon amortization and invalid yield rejection passed.")


if __name__ == '__main__':
    test_monthly_conservation_all_scenarios()
    test_burnout_severity_and_reproducibility()
    test_zero_rates_and_solver_rejection()
