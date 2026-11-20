# Synthetic agency CRT-style valuation

Generate 20,000 synthetic mortgages, project pool and mezzanine cash flows, and compare deterministic scenarios using discounted cash flow.
No network access or external datasets are used. All data is **SYNTHETIC**.

## Run

Required: Python 3, numpy, pandas. Optional: matplotlib for the diagnostic chart. No packages were installed during review.
The reviewed runtime is Python 3.12.14, numpy 2.3.5, pandas 3.0.1.
Matplotlib and pytest are missing in that runtime. The runner reports the skipped chart and runs plain assertion tests without pytest.

PowerShell, from this folder:

```powershell
python run_all.py
```

The runner regenerates data, tables, the memo, and monthly cash flows, then discovers every `test_*` function in `tests/test_*.py`.
Each test file also runs directly as a plain script. Tests of exported numbers require generated CSVs, so run the runner first.
The test suite needs no pytest dependency. All user inputs and column names live in `python/config.py`; test-specific inputs sit at the top of each test file.

## Files

| Path | Contents |
| :--- | :--- |
| `python/config.py` | Seed, distributions, thresholds, scenario assumptions, column names, paths |
| `python/pool_generator.py` | Independent clipped attributes and amortized current balance |
| `python/cohort_model.py` | FICO/LTV default buckets, LTV severity, CPR incentive and burnout |
| `python/cashflow_engine.py` | Monthly pool principal, recoveries, interest, and three-tier principal/loss ledger |
| `python/pricing_engine.py` | DCF, bisection yield solver, fixed-cashflow risk, tables, memo, optional chart |
| `tests/` | Conservation, loss bounds, monotonicity, regression and independent arithmetic checks |
| `data/synthetic_loans.csv` | Seed 42, 20,000 synthetic loan records |
| `outputs/cashflows_1.csv` through `cashflows_4.csv` | Base, rates up, rates down, home price stress, in that order |
| `outputs/scenario_results.csv` | Four scenario valuations and risk metrics |
| `outputs/price_yield_table.csv` | 16 model prices from 90 through 105, with solved yield and spread |
| `outputs/sensitivity_grid.csv` | 30 CPR/CDR combinations, model price, yield, WAL and loss |
| `outputs/valuation_memo.md` | Computed tables, assumptions, units and limits |
| `outputs/pricing_curves.png` | Optional chart, unavailable in the reviewed runtime |
| `REVIEW.md` | Review evidence, fixes, SPEC checklist and numerical cross-checks |

## Computed results

Current UPB: $6,362,267,183.11; initial mezzanine: $190,868,015.49.
WAC: 6.203302%; weighted FICO: 745.21; weighted original LTV: 74.9090%.
WALA: 20.8863 months; WARM: 339.1137 months; projection horizon: 340 months.
Initial attachment: 1.00%; detachment: 4.00%.
Yield and loss columns below are percentages. Spread is in basis points; WAL and duration are in years; price is percent of initial par.

| scenario | par_yield_pct | par_spread_bps | wal_years | modified_duration | convexity | pool_cum_loss_pct | mezz_cum_loss_pct | model_price_pct |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Base Case | 7.500000 | 250.000000 | 5.017466 | 3.631114 | 26.954767 | 0.342972 | 0.000000 | 100.000000 |
| Rates Up 100bp | 8.500000 | 250.000000 | 5.202487 | 3.597285 | 26.352205 | 0.385803 | 0.000000 | 100.000000 |
| Rates Down 100bp | 6.500000 | 250.000000 | 4.844028 | 3.666490 | 27.591902 | 0.301941 | 0.000000 | 100.000000 |
| Home Price Down 10pct | 7.500000 | 250.000000 | 4.960668 | 3.598377 | 26.527099 | 0.876420 | 0.000000 | 100.000000 |

Rate increases modestly extend WAL; rate decreases shorten it under the assumed incentive curve.
The home price stress raises pool losses but does not exhaust initial junior protection.
All four standard scenarios return mezzanine principal without write-down, so par yields equal their coupons and model prices equal 100.
Stronger CDR and slower CPR combinations in the sensitivity grid produce positive mezzanine losses and lower prices.
These results replace the unsupported numerical examples originally in the documentation.

## Assumptions and limits

All data is SYNTHETIC. No real borrower records, clients, employers, or observed market calibration are used.
Attributes are sampled independently from clipped normal distributions with assumed plausible ranges; categorical fields are sampled separately.
The model compresses loans into a homogeneous pool using weighted coupon, age, maturity, bucket CDR, and default-weighted LTV severity.
The monthly horizon is the ceiling of weighted remaining maturity, not each loan's contractual schedule.
DTI, state, occupancy, and property type are descriptive; they do not drive cash flows.
Severity uses cutoff amortized LTV, the scenario home price shock, and an assumed 0.60 net property recovery factor, bounded from 5% to 80%.
It does not update loan equity as the pool pays down. Default and prepayment composition do not migrate across cohorts.
Recoveries settle immediately. There are no recovery lags, servicing fees, delinquency states, or stochastic paths.
Junior credit protection is retained until senior principal is repaid. Mezzanine receives a pro rata share of available cash principal based on surviving claims.
Residual principal pays senior before junior. Losses hit junior, mezzanine, then senior. Only mezzanine interest is modeled in the capital structure.
Mezzanine coupons use a flat assumed benchmark plus 250 bps; the benchmark is not an observed SOFR fixing.
Duration and convexity bump the discount yield while holding cash flows and coupons fixed. They are not effective floating-rate sensitivities.
WAL weights only principal returned and excludes write-downs. Par yield is a break-even discount rate, not a forecast return.
Spread is par yield minus a flat benchmark, not OAS or a fitted market spread. Model price uses benchmark plus the 250 bp note margin as the discount yield.
Replay ignores market liquidity, bid ask spreads, repo costs, and transaction-specific agency triggers.
This is an educational CRT-style model, not a replication of a Fannie Mae or Freddie Mac transaction. It is not production validated.
