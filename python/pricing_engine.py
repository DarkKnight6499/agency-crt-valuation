"""DCF valuation, yield solving, risk analytics, sensitivity grids, and reporting."""

import os
import numpy as np
import pandas as pd
from python.config import *

# CONFIG: shared inputs and named columns are imported from python.config.


def compute_present_value(cashflows, annual_yield):
    """Discount monthly cash flows to present value at annualized yield."""
    if not np.isfinite(annual_yield) or annual_yield <= -MONTHS_PER_YEAR:
        raise ValueError("Yield must be finite and greater than -1200 percent")
    months = np.arange(1, len(cashflows) + 1)
    monthly_discount_factor = (1.0 + annual_yield / MONTHS_PER_YEAR) ** months
    pv = np.sum(cashflows / monthly_discount_factor)
    return float(pv)


def solve_yield_for_price(cashflows, target_price_pct, initial_balance):
    """Find internal rate of return matching discounted cash flows to target price."""
    if not np.isfinite(target_price_pct) or not np.isfinite(initial_balance):
        raise ValueError("Price and balance must be finite")
    cashflows = np.asarray(cashflows, dtype=float)
    if cashflows.ndim != 1 or not np.all(np.isfinite(cashflows)) or np.any(cashflows < 0):
        raise ValueError("Yield solver requires finite nonnegative cash flows")
    target_pv = (target_price_pct / PRICE_PAR) * initial_balance

    low = YIELD_LOWER_BOUND
    high = YIELD_UPPER_BOUND

    f_low = compute_present_value(cashflows, low) - target_pv
    f_high = compute_present_value(cashflows, high) - target_pv

    if target_pv <= 0 or initial_balance <= 0 or f_low * f_high > 0:
        raise ValueError("Target price has no yield within configured bracket")
    if abs(f_low) <= SOLVER_TOLERANCE:
        return float(low)
    if abs(f_high) <= SOLVER_TOLERANCE:
        return float(high)

    for _ in range(MAX_SOLVER_ITERATIONS):
        mid = 0.5 * (low + high)
        f_mid = compute_present_value(cashflows, mid) - target_pv
        if abs(f_mid) < SOLVER_TOLERANCE or (high - low) < YIELD_BRACKET_TOLERANCE:
            return float(mid)
        if f_low * f_mid <= 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid

    return float(0.5 * (low + high))


def compute_wal(principal_cashflows):
    """Compute weighted average life of returned principal in years."""
    total_principal = np.sum(principal_cashflows)
    if total_principal <= SMALL_CASHFLOW:
        return 0.0
    months = np.arange(1, len(principal_cashflows) + 1)
    wal_months = np.sum(months * principal_cashflows) / total_principal
    return float(wal_months / MONTHS_PER_YEAR)


def compute_duration_and_convexity(cashflows, base_yield, dy=DELTA_YIELD):
    """Estimate fixed-cashflow modified duration and convexity by finite differences."""
    if dy <= 0:
        raise ValueError("Yield bump must be positive")
    pv_0 = compute_present_value(cashflows, base_yield)
    if pv_0 <= SMALL_CASHFLOW:
        return 0.0, 0.0

    pv_up = compute_present_value(cashflows, base_yield + dy)
    pv_down = compute_present_value(cashflows, base_yield - dy)

    duration = - (pv_up - pv_down) / (2.0 * pv_0 * dy)
    convexity = (pv_up + pv_down - 2.0 * pv_0) / (pv_0 * (dy ** 2))
    return float(duration), float(convexity)


def run_scenario_valuation(pool_summary, base_pool_cdr):
    """Evaluate mezzanine tranche valuation across standard scenario suite."""
    from python.cohort_model import get_scenario_definitions
    from python.cashflow_engine import simulate_monthly_cashflows

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    scenarios = get_scenario_definitions()
    results = []
    cf_dict = {}

    for name, params in scenarios.items():
        df_cf, summary = simulate_monthly_cashflows(pool_summary, params, base_pool_cdr)
        cf_dict[name] = df_cf
        df_cf.to_csv(os.path.join(OUTPUTS_DIR, CASHFLOW_FILE_TEMPLATE.format(index=len(cf_dict))), index=False)

        mezz_cfs = df_cf[COL_MEZZ_TOTAL_CF].to_numpy()
        mezz_prins = df_cf[COL_MEZZ_PRIN].to_numpy()
        mezz_0 = summary["initial_mezz_balance"]

        par_yield = solve_yield_for_price(mezz_cfs, TARGET_PAR_PRICE, mezz_0)
        spread_bps = (par_yield - params[COL_BENCHMARK_RATE]) * 10000.0
        wal = compute_wal(mezz_prins)
        duration, convexity = compute_duration_and_convexity(mezz_cfs, par_yield)
        discount_yield = params[COL_BENCHMARK_RATE] + TRANCHE_MARGIN

        row = {
            COL_SCENARIO: name,
            COL_BENCHMARK_RATE: params[COL_BENCHMARK_RATE],
            COL_MORTGAGE_RATE: params[COL_MORTGAGE_RATE],
            COL_PAR_YIELD: par_yield,
            COL_PAR_SPREAD_BPS: spread_bps,
            COL_WAL_YEARS: wal,
            COL_MODIFIED_DURATION: duration,
            COL_CONVEXITY: convexity,
            COL_POOL_CUM_LOSS_PCT: summary["pool_loss_pct"] * 100.0,
            COL_MEZZ_CUM_LOSS_PCT: summary[COL_MEZZ_LOSS_PCT] * 100.0,
            COL_MEZZ_PRINCIPAL_PAID: summary["total_mezz_principal_paid"],
            COL_MEZZ_WRITEDOWN: summary["total_mezz_writedown"],
            COL_DISCOUNT_YIELD: discount_yield,
            COL_MODEL_PRICE: PRICE_PAR * compute_present_value(mezz_cfs, discount_yield) / mezz_0,
        }
        results.append(row)

    df_results = pd.DataFrame(results)
    df_results.to_csv(SCENARIOS_CSV_PATH, index=False)
    print(f"Scenario valuation table written to: {SCENARIOS_CSV_PATH}")
    return df_results, cf_dict


def generate_price_yield_table(cashflows, initial_balance, benchmark_rate):
    """Construct price, yield, spread, and duration profile across dollar prices."""
    prices = PRICE_GRID
    rows = []

    for price in prices:
        yld = solve_yield_for_price(cashflows, price, initial_balance)
        spread = (yld - benchmark_rate) * 10000.0
        dur, conv = compute_duration_and_convexity(cashflows, yld)

        rows.append({
            COL_DOLLAR_PRICE: price,
            COL_YIELD_PCT: yld * 100.0,
            COL_SPREAD_BPS: spread,
            COL_MODIFIED_DURATION: dur,
            COL_CONVEXITY: conv,
        })

    df_py = pd.DataFrame(rows)
    df_py.to_csv(PRICE_YIELD_CSV_PATH, index=False)
    print(f"Price yield table written to: {PRICE_YIELD_CSV_PATH}")
    return df_py


def generate_sensitivity_grid(pool_summary, base_pool_cdr):
    """Compute sensitivity matrix over varying CPR and CDR stress multipliers."""
    from python.cohort_model import get_scenario_definitions
    from python.cashflow_engine import simulate_monthly_cashflows

    cpr_multipliers = CPR_MULTIPLIERS
    cdr_multipliers = CDR_MULTIPLIERS

    scenarios = get_scenario_definitions()
    base_params = scenarios[SCENARIO_BASE]
    mezz_0 = pool_summary["total_current_upb"] * (DETACHMENT_POINT - ATTACHMENT_POINT)

    grid_records = []
    for cpr_m in cpr_multipliers:
        for cdr_m in cdr_multipliers:
            df_cf, summary = simulate_monthly_cashflows(
                pool_summary, base_params, base_pool_cdr, cpr_mult=cpr_m, cdr_mult=cdr_m
            )
            cfs = df_cf[COL_MEZZ_TOTAL_CF].to_numpy()
            prins = df_cf[COL_MEZZ_PRIN].to_numpy()

            yld = solve_yield_for_price(cfs, TARGET_PAR_PRICE, mezz_0)
            wal = compute_wal(prins)
            loss_pct = summary[COL_MEZZ_LOSS_PCT] * 100.0
            model_price = PRICE_PAR * compute_present_value(cfs, BASE_BENCHMARK_RATE + TRANCHE_MARGIN) / mezz_0

            grid_records.append({
                COL_CPR_MULTIPLIER: cpr_m,
                COL_CDR_MULTIPLIER: cdr_m,
                COL_PAR_YIELD_PCT: yld * 100.0,
                COL_WAL_YEARS: wal,
                COL_MEZZ_LOSS_PCT: loss_pct,
                COL_MODEL_PRICE: model_price,
            })

    df_grid = pd.DataFrame(grid_records)
    df_grid.to_csv(SENSITIVITY_CSV_PATH, index=False)
    print(f"Sensitivity grid written to: {SENSITIVITY_CSV_PATH}")
    return df_grid


def plot_pricing_curves(df_py, cf_dict, df_grid):
    """Plot multi-panel visual diagnostics for cash flows, pricing, and sensitivities."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as error:
        if error.name != "matplotlib":
            raise
        print("Optional matplotlib missing: chart skipped; no packages installed.")
        return
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=CHART_SIZE)

    ax1 = axes[0, 0]
    ax1.plot(df_py[COL_YIELD_PCT], df_py[COL_DOLLAR_PRICE], color="#1f77b4", lw=2, marker="o", markersize=4)
    ax1.axhline(100.0, color="gray", linestyle=":", alpha=0.7)
    ax1.set_title("Price vs Yield Curve (Base Case)")
    ax1.set_xlabel("Annualized Yield (%)")
    ax1.set_ylabel("Dollar Price (% Par)")
    ax1.grid(True, alpha=0.3)

    ax2 = axes[0, 1]
    for name, df_cf in cf_dict.items():
        sub_df = df_cf.loc[df_cf[COL_MONTH] <= CHART_MONTHS]
        ax2.plot(sub_df[COL_MONTH], sub_df[COL_MEZZ_TOTAL_CF] / 1e6, label=name, lw=1.8)
    ax2.set_title("Mezzanine Total Monthly Cash Flows (First 10 Yrs)")
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Monthly Cash Flow ($ Millions)")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.3)

    ax3 = axes[1, 0]
    for name, df_cf in cf_dict.items():
        ax3.plot(df_cf[COL_MONTH], df_cf[COL_CUM_POOL_LOSS] / 1e6, label=name, lw=1.8)
    ax3.set_title("Cumulative Collateral Pool Losses ($ Millions)")
    ax3.set_xlabel("Month")
    ax3.set_ylabel("Cumulative Loss ($ Millions)")
    ax3.legend(loc="upper left", fontsize=8)
    ax3.grid(True, alpha=0.3)

    ax4 = axes[1, 1]
    pivot_wal = df_grid.pivot(index=COL_CDR_MULTIPLIER, columns=COL_CPR_MULTIPLIER, values=COL_WAL_YEARS)
    im = ax4.imshow(pivot_wal.values, cmap="YlGnBu", aspect="auto", origin="lower")
    ax4.set_xticks(range(len(pivot_wal.columns)))
    ax4.set_xticklabels([f"{c}x" for c in pivot_wal.columns])
    ax4.set_yticks(range(len(pivot_wal.index)))
    ax4.set_yticklabels([f"{r}x" for r in pivot_wal.index])
    ax4.set_title("WAL Sensitivity (Years) to CPR and CDR Multipliers")
    ax4.set_xlabel("CPR Multiplier")
    ax4.set_ylabel("CDR Multiplier")
    cbar = fig.colorbar(im, ax=ax4)
    cbar.set_label("WAL (Years)")

    plt.tight_layout()
    plt.savefig(PRICING_CHART_PATH, dpi=CHART_DPI)
    plt.close()
    print(f"Diagnostic chart saved to: {PRICING_CHART_PATH}")


def markdown_table(frame):
    """Render a table without optional formatting dependencies."""
    lines = ["| " + " | ".join(frame.columns) + " |",
             "| " + " | ".join(":---" for _ in frame.columns) + " |"]
    for record in frame.to_dict("records"):
        lines.append("| " + " | ".join(f"{record[column]:.6f}" if isinstance(record[column], float) else str(record[column]) for column in frame.columns) + " |")
    return "\n".join(lines)


def write_valuation_memo(df_scenarios, df_py, df_grid, pool_summary):
    """Write computed results and explicit model limits."""
    text = f"""# Valuation memo: SYNTHETIC CRT-style model

All records are synthetic. No real loan data or observed market calibration is used.
Current pool balance: ${pool_summary['total_current_upb']:,.2f}; loan count: {pool_summary['loan_count']:,}.
Initial mezzanine balance is (detachment minus attachment) times current pool balance.

Yields are nominal annual rates compounded monthly, in decimal units. Spreads are yield minus the assumed flat benchmark, in basis points.
Loss columns are percentages. WAL uses principal actually returned, excluding write-downs.
Duration and convexity hold projected cash flows fixed, with a {DELTA_YIELD * BASIS_POINTS:g} bp yield bump. They do not measure effective floating-rate risk.

{markdown_table(df_scenarios)}

Prices are percent of initial mezzanine par. These are model prices, not market indications.

{markdown_table(df_py)}


{markdown_table(df_grid)}

Independent clipped normal attributes use assumed plausible ranges, not fitted distributions.
The pool is compressed to weighted coupon, age, and remaining term, rounded up to a monthly horizon.
FICO/LTV bucket CDR and default-weighted loan LTV severity are aggregated at cutoff and held homogeneous afterward.
Severity is clip(1 minus {NET_PROPERTY_RECOVERY:.2f} / adjusted LTV, {SEVERITY_FLOOR:.2f}, {SEVERITY_CAP:.2f}). Adjusted LTV uses amortized balance and the scenario home price change.
The net property recovery factor is an assumption, not an observed recovery estimate.
The home price stress is {HOME_PRICE_STRESS:.0%}; scenario CDR multipliers are separate assumptions defined in python/config.py.
CPR responds to rate incentive, seasoning, and realized cumulative prepayments. CDR follows an assumed seasoning hump.
Defaults follow scheduled principal and voluntary prepayments. Recoveries settle immediately; pool interest accrues on beginning balance.
Losses hit junior, mezzanine, then senior. Mezzanine receives a pro rata share of cash principal based on surviving claims.
Remaining cash principal pays senior before junior. Mezzanine interest accrues on beginning balance at benchmark plus {TRANCHE_MARGIN * BASIS_POINTS:g} bps.
This stylized funded waterfall is not a replication of an agency transaction. Senior and junior interest are not modeled.
Benchmark rates remain flat within each scenario. Replay ignores market liquidity, fees, repo costs, recovery delays, and stochastic paths.
Par yields are break-even discount rates for projected cash flows, not investment returns or quoted market yields.
"""
    with open(VALUATION_MEMO_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"Synthetic valuation memo written to: {VALUATION_MEMO_PATH}")
