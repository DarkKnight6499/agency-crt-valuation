"""Synthetic mortgage loan pool generator for Agency CRT valuation."""

import os
import sys
import numpy as np
import pandas as pd

# CONFIG: standalone import path; model inputs are in python.config.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from python.config import *
from python.cohort_model import compute_pool_severity


def calculate_amortized_balance(orig_bal, coupon, term, age):
    """Compute remaining principal balance after scheduled amortization."""
    monthly_rate = coupon / MONTHS_PER_YEAR
    factor_term = (1.0 + monthly_rate) ** term
    factor_age = (1.0 + monthly_rate) ** age
    numerator = orig_bal * (factor_term - factor_age)
    balance = np.divide(numerator, factor_term - 1.0, out=np.asarray(orig_bal * (1.0 - age / term), dtype=float), where=monthly_rate != 0)
    return np.maximum(balance, 0.0)


def generate_loan_pool(seed=SEED, save_csv=True):
    """Generate deterministic synthetic mortgage pool with assumed plausible ranges."""
    rng = np.random.RandomState(seed)
    os.makedirs(DATA_DIR, exist_ok=True)

    ficos = rng.normal(MEAN_FICO, STD_FICO, TOTAL_LOANS)
    ficos = np.clip(np.round(ficos), MIN_FICO, MAX_FICO).astype(int)

    ltvs = rng.normal(MEAN_LTV, STD_LTV, TOTAL_LOANS)
    ltvs = np.clip(np.round(ltvs, LTV_PRECISION), MIN_LTV, MAX_LTV)

    dtis = rng.normal(MEAN_DTI, STD_DTI, TOTAL_LOANS)
    dtis = np.clip(np.round(dtis, DTI_PRECISION), MIN_DTI, MAX_DTI)

    coupons = rng.normal(MEAN_COUPON, STD_COUPON, TOTAL_LOANS)
    coupons = np.clip(np.round(coupons, COUPON_PRECISION), MIN_COUPON, MAX_COUPON)

    balances = rng.normal(MEAN_BALANCE, STD_BALANCE, TOTAL_LOANS)
    balances = np.clip(np.round(balances, BALANCE_PRECISION), MIN_BALANCE, MAX_BALANCE)

    ages = rng.randint(MIN_AGE, MAX_AGE + 1, TOTAL_LOANS)
    remaining_terms = LOAN_TERM - ages

    current_balances = calculate_amortized_balance(balances, coupons, LOAN_TERM, ages)
    current_balances = np.round(current_balances, BALANCE_PRECISION)

    states = rng.choice(STATE_NAMES, size=TOTAL_LOANS, p=STATE_PROBS)
    occupancies = rng.choice(OCCUPANCY_NAMES, size=TOTAL_LOANS, p=OCCUPANCY_PROBS)
    prop_types = rng.choice(PROPERTY_NAMES, size=TOTAL_LOANS, p=PROPERTY_PROBS)

    loan_ids = [f"SYNTH_LN_{i+1:06d}" for i in range(TOTAL_LOANS)]

    df = pd.DataFrame()
    df[COL_LOAN_ID] = loan_ids
    df[COL_ORIG_BALANCE] = balances
    df[COL_CURRENT_BALANCE] = current_balances
    df[COL_COUPON] = coupons
    df[COL_FICO] = ficos
    df[COL_ORIG_LTV] = ltvs
    df[COL_ORIG_DTI] = dtis
    df[COL_LOAN_AGE] = ages
    df[COL_ORIG_TERM] = LOAN_TERM
    df[COL_REMAINING_TERM] = remaining_terms
    df[COL_STATE] = states
    df[COL_OCCUPANCY] = occupancies
    df[COL_PROPERTY_TYPE] = prop_types

    if save_csv:
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"Saved {TOTAL_LOANS} synthetic loans to: {OUTPUT_CSV}")

    return df


def compute_pool_summary(df):
    """Aggregate pool level weighted statistics for cash flow simulation."""
    total_upb = float(df[COL_CURRENT_BALANCE].sum())
    total_orig_upb = float(df[COL_ORIG_BALANCE].sum())
    weights = df[COL_CURRENT_BALANCE] / total_upb

    wac = float((df[COL_COUPON] * weights).sum())
    wala = float((df[COL_LOAN_AGE] * weights).sum())
    warm = float((df[COL_REMAINING_TERM] * weights).sum())
    weighted_fico = float((df[COL_FICO] * weights).sum())
    weighted_ltv = float((df[COL_ORIG_LTV] * weights).sum())
    weighted_dti = float((df[COL_ORIG_DTI] * weights).sum())

    summary = {
        "loan_count": len(df),
        "total_current_upb": total_upb,
        "total_orig_upb": total_orig_upb,
        "wac": wac,
        "wala": wala,
        "warm": warm,
        "weighted_fico": weighted_fico,
        "weighted_ltv": weighted_ltv,
        "weighted_dti": weighted_dti,
        "severity_base": compute_pool_severity(df),
        "severity_stress": compute_pool_severity(df, HOME_PRICE_STRESS),
        "severity_by_home_price": {hpa: compute_pool_severity(df, hpa)
                                   for _, _, _, hpa in SCENARIO_INPUTS},
    }
    return summary


if __name__ == "__main__":
    print("Generating synthetic loan pool...")
    pool_df = generate_loan_pool(seed=SEED, save_csv=True)
    summary = compute_pool_summary(pool_df)
    print("Synthetic Pool Summary Metrics:")
    print(f"  Loan Count: {summary['loan_count']:,}")
    print(f"  Total Current UPB: ${summary['total_current_upb']:,.2f}")
    print(f"  Weighted Average Coupon (WAC): {summary['wac']*100:.3f}%")
    print(f"  Weighted Average Loan Age (WALA): {summary['wala']:.1f} months")
    print(f"  Weighted Average Remaining Maturity (WARM): {summary['warm']:.1f} months")
    print(f"  Weighted Average FICO: {summary['weighted_fico']:.1f}")
    print(f"  Weighted Average Original LTV: {summary['weighted_ltv']*100:.2f}%")
    print(f"  Weighted Average Original DTI: {summary['weighted_dti']*100:.2f}%")
