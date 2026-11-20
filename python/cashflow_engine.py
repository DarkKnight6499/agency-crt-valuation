"""Monthly synthetic pool cash flows and a stylized three-tier waterfall."""

import numpy as np
import pandas as pd
from python.config import *
from python.cohort_model import compute_cpr_vector, compute_cdr_vector

# CONFIG: shared inputs and named columns are imported from python.config.


def simulate_monthly_cashflows(pool_summary, scenario_params, base_pool_cdr,
                              cpr_mult=DEFAULT_CPR_MULTIPLIER, cdr_mult=DEFAULT_CDR_MULTIPLIER):
    """Allocate losses junior first and cash principal to mezzanine then senior."""
    if cpr_mult < 0 or cdr_mult < 0:
        raise ValueError("CPR and CDR multipliers must be nonnegative")
    upb_0 = pool_summary["total_current_upb"]
    wac = pool_summary["wac"]
    wala = pool_summary["wala"]
    warm = int(np.ceil(pool_summary["warm"]))
    severity = pool_summary["severity_by_home_price"][scenario_params["home_price_change"]]
    mezz_0 = upb_0 * (DETACHMENT_POINT - ATTACHMENT_POINT)
    pool_bal, mezz_bal = upb_0, mezz_0
    sub_bal = upb_0 * ATTACHMENT_POINT
    senior_bal = upb_0 - mezz_bal - sub_bal
    cumulative_loss = cumulative_mezz_loss = cumulative_prepay = 0.0
    cdr = compute_cdr_vector(base_pool_cdr, scenario_params[COL_CDR_MULTIPLIER] * cdr_mult, wala, warm)
    records = []
    for m in range(warm):
        month = m + 1
        pool_beg, mezz_beg = pool_bal, mezz_bal
        # Realized prepayments suppress subsequent refinancing demand.
        cpr = compute_cpr_vector(wac, scenario_params[COL_MORTGAGE_RATE], wala + m,
                                 1, np.array([cumulative_prepay / upb_0]))[0]
        cpr = np.clip(cpr * cpr_mult, 0.0, CPR_CAP)
        smm = 1.0 - (1.0 - cpr) ** (1.0 / MONTHS_PER_YEAR)
        mdr = 1.0 - (1.0 - cdr[m]) ** (1.0 / MONTHS_PER_YEAR)
        rem = warm - m
        monthly_rate = wac / MONTHS_PER_YEAR
        interest = pool_beg * monthly_rate
        payment = pool_beg / rem if monthly_rate == 0 else pool_beg * monthly_rate / (1.0 - (1.0 + monthly_rate) ** (-rem))
        scheduled = min(pool_beg, max(0.0, payment - interest))
        prepay = (pool_beg - scheduled) * smm
        default = max(0.0, pool_beg - scheduled - prepay) * mdr
        loss = default * severity
        recovery = default - loss
        principal = scheduled + prepay + recovery
        pool_end = max(0.0, pool_beg - scheduled - prepay - default)
        junior_loss = min(sub_bal, loss)
        junior_post = sub_bal - junior_loss
        mezz_loss = min(mezz_beg, loss - junior_loss)
        mezz_post = mezz_beg - mezz_loss
        senior_loss = loss - junior_loss - mezz_loss
        senior_post = max(0.0, senior_bal - senior_loss)
        # Junior principal stays locked while senior claims remain outstanding.
        surviving_claims = pool_beg - loss
        mezz_prin = min(mezz_post, principal * mezz_post / surviving_claims) if surviving_claims > 0 else 0.0
        senior_prin = min(senior_post, max(0.0, principal - mezz_prin))
        junior_prin = min(junior_post, max(0.0, principal - mezz_prin - senior_prin))
        mezz_bal = max(0.0, mezz_post - mezz_prin)
        senior_bal = max(0.0, senior_post - senior_prin)
        sub_bal = max(0.0, junior_post - junior_prin)
        mezz_interest = mezz_beg * (scenario_params[COL_BENCHMARK_RATE] + TRANCHE_MARGIN) / MONTHS_PER_YEAR
        cumulative_loss += loss
        cumulative_mezz_loss += mezz_loss
        cumulative_prepay += prepay
        records.append({
            COL_MONTH: month, COL_POOL_BEG_BAL: pool_beg,
            COL_POOL_SCHED_PRIN: scheduled, COL_POOL_PREPAY_PRIN: prepay,
            COL_POOL_DEFAULT_BAL: default, COL_POOL_REALIZED_LOSS: loss,
            COL_POOL_RECOVERY: recovery, COL_POOL_PRIN: principal,
            COL_POOL_INTEREST: interest, COL_POOL_TOTAL_CF: principal + interest,
            COL_POOL_END_BAL: pool_end, COL_MEZZ_BEG_BAL: mezz_beg,
            COL_MEZZ_WRITEDOWN: mezz_loss, COL_MEZZ_PRIN: mezz_prin,
            COL_MEZZ_INTEREST: mezz_interest, COL_MEZZ_TOTAL_CF: mezz_prin + mezz_interest,
            COL_MEZZ_END_BAL: mezz_bal, COL_CUM_POOL_LOSS: cumulative_loss,
            COL_CUM_MEZZ_LOSS: cumulative_mezz_loss, COL_CPR: cpr, COL_CDR: cdr[m],
            COL_SEVERITY: severity, COL_JUNIOR_PRIN: junior_prin,
            COL_SENIOR_PRIN: senior_prin, COL_JUNIOR_END: sub_bal,
            COL_SENIOR_END: senior_bal, COL_JUNIOR_LOSS: junior_loss,
            COL_SENIOR_LOSS: senior_loss,
        })
        pool_bal = pool_end
    df = pd.DataFrame(records)
    summary = {
        "scenario_name": scenario_params["name"], "initial_pool_balance": upb_0,
        "initial_mezz_balance": mezz_0,
        "total_pool_scheduled_prin": float(df[COL_POOL_SCHED_PRIN].sum()),
        "total_pool_prepay_prin": float(df[COL_POOL_PREPAY_PRIN].sum()),
        "total_pool_default_bal": float(df[COL_POOL_DEFAULT_BAL].sum()),
        "total_pool_realized_loss": cumulative_loss,
        "total_mezz_principal_paid": float(df[COL_MEZZ_PRIN].sum()),
        "total_mezz_writedown": cumulative_mezz_loss,
        "total_mezz_interest_paid": float(df[COL_MEZZ_INTEREST].sum()),
        "total_mezz_cashflow": float(df[COL_MEZZ_TOTAL_CF].sum()),
        "pool_loss_pct": cumulative_loss / upb_0,
        "mezz_loss_pct": cumulative_mezz_loss / mezz_0,
    }
    print(f"Synthetic {scenario_params['name']}: {warm} months, pool loss {summary['pool_loss_pct']:.4%}, mezz loss {summary[COL_MEZZ_LOSS_PCT]:.4%}")
    return df, summary
