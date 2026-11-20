# Valuation memo: SYNTHETIC CRT-style model

All records are synthetic. No real loan data or observed market calibration is used.
Current pool balance: $6,362,267,183.11; loan count: 20,000.
Initial mezzanine balance is (detachment minus attachment) times current pool balance.

Yields are nominal annual rates compounded monthly, in decimal units. Spreads are yield minus the assumed flat benchmark, in basis points.
Loss columns are percentages. WAL uses principal actually returned, excluding write-downs.
Duration and convexity hold projected cash flows fixed, with a 25 bp yield bump. They do not measure effective floating-rate risk.

| scenario | benchmark_rate | mortgage_rate | par_yield | par_spread_bps | wal_years | modified_duration | convexity | pool_cum_loss_pct | mezz_cum_loss_pct | mezz_principal_paid | mezz_writedown | discount_yield | model_price_pct |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Base Case | 0.050000 | 0.062500 | 0.075000 | 250.000000 | 5.017466 | 3.631114 | 26.954767 | 0.342972 | 0.000000 | 190868015.493300 | 0.000000 | 0.075000 | 100.000000 |
| Rates Up 100bp | 0.060000 | 0.072500 | 0.085000 | 250.000000 | 5.202487 | 3.597285 | 26.352205 | 0.385803 | 0.000000 | 190868015.493300 | 0.000000 | 0.085000 | 100.000000 |
| Rates Down 100bp | 0.040000 | 0.052500 | 0.065000 | 250.000000 | 4.844028 | 3.666490 | 27.591902 | 0.301941 | 0.000000 | 190868015.493300 | 0.000000 | 0.065000 | 100.000000 |
| Home Price Down 10pct | 0.050000 | 0.062500 | 0.075000 | 250.000000 | 4.960668 | 3.598377 | 26.527099 | 0.876420 | 0.000000 | 190868015.493300 | 0.000000 | 0.075000 | 100.000000 |

Prices are percent of initial mezzanine par. These are model prices, not market indications.

| dollar_price | yield_pct | spread_bps | modified_duration | convexity |
| :--- | :--- | :--- | :--- | :--- |
| 90 | 10.568087 | 556.808679 | 3.251105 | 21.690560 |
| 91 | 10.230152 | 523.015197 | 3.289126 | 22.195833 |
| 92 | 9.899752 | 489.975180 | 3.327150 | 22.706051 |
| 93 | 9.576637 | 457.663723 | 3.365175 | 23.221124 |
| 94 | 9.260570 | 426.056978 | 3.403197 | 23.740961 |
| 95 | 8.951321 | 395.132098 | 3.441215 | 24.265468 |
| 96 | 8.648672 | 364.867188 | 3.479223 | 24.794554 |
| 97 | 8.352413 | 335.241255 | 3.517221 | 25.328122 |
| 98 | 8.062342 | 306.234164 | 3.555204 | 25.866077 |
| 99 | 7.778266 | 277.826594 | 3.593169 | 26.408325 |
| 100 | 7.500000 | 250.000000 | 3.631114 | 26.954767 |
| 101 | 7.227366 | 222.736572 | 3.669036 | 27.505308 |
| 102 | 6.960192 | 196.019203 | 3.706932 | 28.059850 |
| 103 | 6.698315 | 169.831453 | 3.744798 | 28.618295 |
| 104 | 6.441575 | 144.157518 | 3.782633 | 29.180546 |
| 105 | 6.189822 | 118.982200 | 3.820434 | 29.746506 |


| cpr_multiplier | cdr_multiplier | par_yield_pct | wal_years | mezz_loss_pct | model_price_pct |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0.500000 | 0.500000 | 7.500000 | 8.319649 | 0.000000 | 100.000000 |
| 0.500000 | 1.000000 | 7.500000 | 8.239453 | 0.000000 | 100.000000 |
| 0.500000 | 1.500000 | 7.500000 | 8.160120 | 0.000000 | 100.000000 |
| 0.500000 | 2.000000 | 7.500000 | 8.081641 | 0.000000 | 100.000000 |
| 0.500000 | 3.000000 | 6.121506 | 7.205402 | 10.498610 | 93.581932 |
| 0.750000 | 0.500000 | 7.500000 | 6.354113 | 0.000000 | 100.000000 |
| 0.750000 | 1.000000 | 7.500000 | 6.297420 | 0.000000 | 100.000000 |
| 0.750000 | 1.500000 | 7.500000 | 6.241334 | 0.000000 | 100.000000 |
| 0.750000 | 2.000000 | 7.500000 | 6.185849 | 0.000000 | 100.000000 |
| 0.750000 | 3.000000 | 6.803961 | 5.699422 | 4.832920 | 97.230584 |
| 1.000000 | 0.500000 | 7.500000 | 5.058799 | 0.000000 | 100.000000 |
| 1.000000 | 1.000000 | 7.500000 | 5.017466 | 0.000000 | 100.000000 |
| 1.000000 | 1.500000 | 7.500000 | 4.976566 | 0.000000 | 100.000000 |
| 1.000000 | 2.000000 | 7.500000 | 4.936091 | 0.000000 | 100.000000 |
| 1.000000 | 3.000000 | 7.474357 | 4.829293 | 0.225546 | 99.909572 |
| 1.250000 | 0.500000 | 7.500000 | 4.154160 | 0.000000 | 100.000000 |
| 1.250000 | 1.000000 | 7.500000 | 4.123283 | 0.000000 | 100.000000 |
| 1.250000 | 1.500000 | 7.500000 | 4.092715 | 0.000000 | 100.000000 |
| 1.250000 | 2.000000 | 7.500000 | 4.062452 | 0.000000 | 100.000000 |
| 1.250000 | 3.000000 | 7.500000 | 4.002830 | 0.000000 | 100.000000 |
| 1.500000 | 0.500000 | 7.500000 | 3.493589 | 0.000000 | 100.000000 |
| 1.500000 | 1.000000 | 7.500000 | 3.470042 | 0.000000 | 100.000000 |
| 1.500000 | 1.500000 | 7.500000 | 3.446719 | 0.000000 | 100.000000 |
| 1.500000 | 2.000000 | 7.500000 | 3.423616 | 0.000000 | 100.000000 |
| 1.500000 | 3.000000 | 7.500000 | 3.378063 | 0.000000 | 100.000000 |
| 2.000000 | 0.500000 | 7.500000 | 2.603182 | 0.000000 | 100.000000 |
| 2.000000 | 1.000000 | 7.500000 | 2.588777 | 0.000000 | 100.000000 |
| 2.000000 | 1.500000 | 7.500000 | 2.574492 | 0.000000 | 100.000000 |
| 2.000000 | 2.000000 | 7.500000 | 2.560325 | 0.000000 | 100.000000 |
| 2.000000 | 3.000000 | 7.500000 | 2.532341 | 0.000000 | 100.000000 |

Independent clipped normal attributes use assumed plausible ranges, not fitted distributions.
The pool is compressed to weighted coupon, age, and remaining term, rounded up to a monthly horizon.
FICO/LTV bucket CDR and default-weighted loan LTV severity are aggregated at cutoff and held homogeneous afterward.
Severity is clip(1 minus 0.60 / adjusted LTV, 0.05, 0.80). Adjusted LTV uses amortized balance and the scenario home price change.
The net property recovery factor is an assumption, not an observed recovery estimate.
The home price stress is -10%; scenario CDR multipliers are separate assumptions defined in python/config.py.
CPR responds to rate incentive, seasoning, and realized cumulative prepayments. CDR follows an assumed seasoning hump.
Defaults follow scheduled principal and voluntary prepayments. Recoveries settle immediately; pool interest accrues on beginning balance.
Losses hit junior, mezzanine, then senior. Mezzanine receives a pro rata share of cash principal based on surviving claims.
Remaining cash principal pays senior before junior. Mezzanine interest accrues on beginning balance at benchmark plus 250 bps.
This stylized funded waterfall is not a replication of an agency transaction. Senior and junior interest are not modeled.
Benchmark rates remain flat within each scenario. Replay ignores market liquidity, fees, repo costs, recovery delays, and stochastic paths.
Par yields are break-even discount rates for projected cash flows, not investment returns or quoted market yields.
