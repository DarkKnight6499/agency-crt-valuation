"""Assumed credit buckets, refinancing response, and LTV loss severity."""

import numpy as np
from python.config import *

# CONFIG: shared model inputs and named columns are imported from python.config.


def loan_default_rates(df):
    """Assign mutually exclusive FICO and LTV default assumptions."""
    rates = np.zeros(len(df))
    lower = -np.inf
    for upper, low_ltv_rate, high_ltv_rate in DEFAULT_BUCKETS:
        mask = (df[COL_FICO] >= lower) & (df[COL_FICO] < upper)
        rates[mask] = np.where(df.loc[mask, COL_ORIG_LTV] > LTV_BUCKET_THRESHOLD,
                               high_ltv_rate, low_ltv_rate)
        lower = upper
    return rates


def compute_baseline_pool_cdr(df, col_fico=COL_FICO, col_ltv=COL_ORIG_LTV,
                              col_bal=COL_CURRENT_BALANCE):
    """Balance-weight the assumed annual risk bucket rates."""
    renamed = df.rename(columns={col_fico: COL_FICO, col_ltv: COL_ORIG_LTV,
                                  col_bal: COL_CURRENT_BALANCE})
    return float(np.average(loan_default_rates(renamed), weights=renamed[COL_CURRENT_BALANCE]))


def compute_pool_severity(df, home_price_change=NO_HOME_PRICE_CHANGE):
    """Default-weight loan severity using amortized LTV and assumed sale haircut."""
    ltv = df[COL_ORIG_LTV] * df[COL_CURRENT_BALANCE] / df[COL_ORIG_BALANCE] / (1.0 + home_price_change)
    severity = np.clip(1.0 - NET_PROPERTY_RECOVERY / ltv, SEVERITY_FLOOR, SEVERITY_CAP)
    weights = df[COL_CURRENT_BALANCE] * loan_default_rates(df)
    return float(np.average(severity, weights=weights))


def get_scenario_definitions(base_benchmark=BASE_BENCHMARK_RATE,
                             base_mortgage_rate=BASE_MORTGAGE_RATE):
    """Return deterministic assumptions, without observed market calibration."""
    return {name: {"name": name, "benchmark_rate": base_benchmark + shift,
                   "mortgage_rate": base_mortgage_rate + shift,
                   "cdr_multiplier": multiplier, "home_price_change": hpa}
            for name, shift, multiplier, hpa in SCENARIO_INPUTS}


def compute_cpr_vector(wac, market_rate, wala, horizon_months, cum_refi_fraction):
    """Apply incentive, seasoning, and realized refinancing burnout."""
    incentive = wac - market_rate
    response = (MAX_CPR - BASE_CPR_TURNOVER) / (1.0 + np.exp(np.clip(-INCENTIVE_SLOPE * incentive, -EXP_LIMIT, EXP_LIMIT)))
    age = wala + np.arange(1, horizon_months + 1)
    ramp = np.minimum(1.0, age / PSA_RAMP_MONTHS)
    burnout = np.exp(-BURNOUT_DECAY * np.asarray(cum_refi_fraction))
    return np.clip(ramp * (BASE_CPR_TURNOVER + response * burnout), MIN_CPR, MAX_CPR)


def compute_cdr_vector(base_cdr, cdr_mult, wala, horizon_months):
    """Use an assumed hump-shaped seasoning profile for defaults."""
    age = wala + np.arange(1, horizon_months + 1)
    normalized = age / TIMING_PEAK_MONTH
    timing = normalized ** TIMING_ALPHA * np.exp(-TIMING_ALPHA * (normalized - 1.0))
    return np.clip(base_cdr * cdr_mult * timing, 0.0, CDR_CAP)
