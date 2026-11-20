"""Recompute exported metrics with scalar arithmetic independent of pricing code."""

import csv
import math
import os
import sys

# CONFIG: standalone paths and numerical acceptance tolerances.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONEY_TOLERANCE = 0.0001
RATE_TOLERANCE = 1e-10
WAL_TOLERANCE = 1e-10
DURATION_TOLERANCE = 0.001
CONVEXITY_TOLERANCE = 0.02
TABLE_TOLERANCE = 1e-8

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from python.config import *
from python.pool_generator import compute_pool_summary
from python.cohort_model import compute_baseline_pool_cdr
import pandas as pd


def read_records(path):
    """Read CSV records without pandas reduction or pricing helpers."""
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def test_independent_collateral_numbers():
    """Recompute UPB, WAC, and bucket CDR using scalar weighted sums."""
    records = read_records(LOANS_CSV_PATH)
    assert len(records) == TOTAL_LOANS
    assert len({row[COL_LOAN_ID] for row in records}) == TOTAL_LOANS
    upb = math.fsum(float(row[COL_CURRENT_BALANCE]) for row in records)
    wac = math.fsum(float(row[COL_CURRENT_BALANCE]) * float(row[COL_COUPON]) for row in records) / upb
    defaults = []
    for row in records:
        fico = float(row[COL_FICO])
        high_ltv = float(row[COL_ORIG_LTV]) > LTV_BUCKET_THRESHOLD
        for upper, low_rate, high_rate in DEFAULT_BUCKETS:
            if fico < upper:
                defaults.append(float(row[COL_CURRENT_BALANCE]) * (high_rate if high_ltv else low_rate))
                break
    cdr = math.fsum(defaults) / upb
    frame = pd.read_csv(LOANS_CSV_PATH)
    summary = compute_pool_summary(frame)
    assert abs(upb - summary['total_current_upb']) < MONEY_TOLERANCE
    assert abs(wac - summary['wac']) < RATE_TOLERANCE
    assert abs(cdr - compute_baseline_pool_cdr(frame)) < RATE_TOLERANCE
    print(f"Independent UPB ${upb:,.2f}; WAC {wac:.10%}; annual CDR {cdr:.10%}.")


def test_independent_exported_valuation():
    """Cross-check all scenario WAL, DCF, and analytic yield derivatives."""
    loans = read_records(LOANS_CSV_PATH)
    upb = math.fsum(float(row[COL_CURRENT_BALANCE]) for row in loans)
    mezz = upb * (DETACHMENT_POINT - ATTACHMENT_POINT)
    scenarios = read_records(SCENARIOS_CSV_PATH)
    for index, result in enumerate(scenarios, start=1):
        flows = read_records(os.path.join(OUTPUTS_DIR, CASHFLOW_FILE_TEMPLATE.format(index=index)))
        principal = math.fsum(float(row[COL_MEZZ_PRIN]) for row in flows)
        wal = math.fsum(float(row[COL_MONTH]) * float(row[COL_MEZZ_PRIN]) for row in flows) / principal / MONTHS_PER_YEAR
        y = float(result[COL_PAR_YIELD])
        q = 1.0 + y / MONTHS_PER_YEAR
        pv = math.fsum(float(row[COL_MEZZ_TOTAL_CF]) * q ** (-int(row[COL_MONTH])) for row in flows)
        d1 = math.fsum(-int(row[COL_MONTH]) / MONTHS_PER_YEAR * float(row[COL_MEZZ_TOTAL_CF]) * q ** (-int(row[COL_MONTH]) - 1) for row in flows)
        d2 = math.fsum(int(row[COL_MONTH]) * (int(row[COL_MONTH]) + 1) / MONTHS_PER_YEAR ** 2 * float(row[COL_MEZZ_TOTAL_CF]) * q ** (-int(row[COL_MONTH]) - 2) for row in flows)
        assert abs(wal - float(result[COL_WAL_YEARS])) < WAL_TOLERANCE
        assert abs(pv - mezz) < MONEY_TOLERANCE
        assert abs(-d1 / pv - float(result[COL_MODIFIED_DURATION])) < DURATION_TOLERANCE
        assert abs(d2 / pv - float(result[COL_CONVEXITY])) < CONVEXITY_TOLERANCE
        assert abs((y - float(result[COL_BENCHMARK_RATE])) * BASIS_POINTS - float(result[COL_PAR_SPREAD_BPS])) < RATE_TOLERANCE
        discount_q = 1.0 + float(result[COL_DISCOUNT_YIELD]) / MONTHS_PER_YEAR
        model_price = PRICE_PAR * math.fsum(float(row[COL_MEZZ_TOTAL_CF]) * discount_q ** (-int(row[COL_MONTH])) for row in flows) / mezz
        assert abs(model_price - float(result[COL_MODEL_PRICE])) < RATE_TOLERANCE
        print(f"Independent {result[COL_SCENARIO]}: WAL {wal:.10f}; par PV ${pv:,.6f}; duration {-d1/pv:.10f}; convexity {d2/pv:.10f}.")


def test_exported_tables_and_ranges():
    """Validate delivered table dimensions, parameter ranges, and base grid cell."""
    frame = pd.read_csv(LOANS_CSV_PATH)
    for column, low, high in ((COL_FICO, MIN_FICO, MAX_FICO), (COL_ORIG_LTV, MIN_LTV, MAX_LTV),
                              (COL_ORIG_DTI, MIN_DTI, MAX_DTI), (COL_COUPON, MIN_COUPON, MAX_COUPON),
                              (COL_ORIG_BALANCE, MIN_BALANCE, MAX_BALANCE), (COL_LOAN_AGE, MIN_AGE, MAX_AGE)):
        assert frame[column].between(low, high).all()
    assert (frame[COL_CURRENT_BALANCE] <= frame[COL_ORIG_BALANCE]).all()
    assert (frame[COL_CURRENT_BALANCE] > 0).all()
    scenarios = pd.read_csv(SCENARIOS_CSV_PATH).set_index(COL_SCENARIO)
    grid = pd.read_csv(SENSITIVITY_CSV_PATH)
    price_yield = pd.read_csv(PRICE_YIELD_CSV_PATH)
    assert len(scenarios) == len(SCENARIO_INPUTS)
    assert len(grid) == len(CPR_MULTIPLIERS) * len(CDR_MULTIPLIERS)
    assert not grid.duplicated([COL_CPR_MULTIPLIER, COL_CDR_MULTIPLIER]).any()
    assert len(price_yield) == len(PRICE_GRID)
    assert price_yield[COL_DOLLAR_PRICE].is_monotonic_increasing
    assert (price_yield[COL_YIELD_PCT].diff().dropna() < 0).all()
    for record in grid.to_dict('records'):
        assert all(math.isfinite(value) for value in record.values())
    base_grid = grid.loc[(grid[COL_CPR_MULTIPLIER] == 1.0) & (grid[COL_CDR_MULTIPLIER] == 1.0)]
    assert len(base_grid) == 1
    assert abs(float(base_grid[COL_WAL_YEARS].item()) - scenarios.loc[SCENARIO_BASE, COL_WAL_YEARS]) < TABLE_TOLERANCE
    assert scenarios.loc[SCENARIO_RATES_UP, COL_WAL_YEARS] > scenarios.loc[SCENARIO_BASE, COL_WAL_YEARS] > scenarios.loc[SCENARIO_RATES_DOWN, COL_WAL_YEARS]
    assert scenarios.loc[SCENARIO_HPA_DOWN, COL_POOL_CUM_LOSS_PCT] > scenarios.loc[SCENARIO_BASE, COL_POOL_CUM_LOSS_PCT]
    assert grid[COL_MEZZ_LOSS_PCT].max() > 0
    print(f"Ranges, {len(scenarios)} scenarios, {len(price_yield)} prices, and {len(grid)} grid cells passed.")


if __name__ == '__main__':
    test_independent_collateral_numbers()
    test_independent_exported_valuation()
    test_exported_tables_and_ranges()
