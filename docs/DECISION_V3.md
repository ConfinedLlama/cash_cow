# Intraday pilot decision — 2 November 2026

**The tested intraday rules do not support a 10%-monthly strategy.** We acquired real SPY minute data, implemented eight declared paper-based variants and completed 236 simulations, including benchmarks, costs, delays and account diagnostics. Every run is retained. The multi-year authenticated test remains pending local Alpaca credentials; no live trading is connected.

## What the data supports

Data: [HistoricalData.net free sample](https://historicaldata.net/samples.html), July–December 2022. July is warm-up; results below cover **August–December 2022, only five months**. We validated 49,350 regular-session bars against an independent exchange calendar, identified the early close, verified vendor hashes and cross-checked daily closes with an independent provider. Minute-level external accuracy is not independently certified.

All returns below start with USD 2,000 and include the declared base costs. Cash accounts are long-only with historical T+2 settlement, while hypothetical margin accounts allow shorts, capital reuse and rule-specific leverage without asserting actual $2,000 eligibility. Drawdowns are measured at minute closes.

| Rule | Cash T+2: compounded month | Hypothetical margin: compounded month | Margin worst month | Margin drawdown |
|---|---:|---:|---:|---:|
| gao_first_half | -0.77% | -1.84% | -3.72% | -9.04% |
| gao_agreement | -0.66% | -1.12% | -2.19% | -5.85% |
| gao_high_volume | -0.52% | -1.30% | -3.57% | -6.40% |
| noise_opposite_band | 0.22% | 0.69% | -3.67% | -5.65% |
| noise_current_vwap | 0.32% | 0.04% | -2.57% | -3.86% |
| noise_vol_target | 0.32% | 0.72% | -2.30% | -3.81% |
| rest_of_day_fixed | -0.66% | -1.41% | -2.10% | -7.05% |
| rest_of_day_vol_target | -0.66% | -1.57% | -2.70% | -8.01% |

The cash results for fixed and volatility-scaled versions sometimes coincide because the long-only account caps exposure before whole-share rounding. These are not independent successes.

## Target and cost findings

- Best **base** cash candidate: current-band/VWAP noise rule, 0.32% compounded monthly, worst month −0.61%, drawdown −1.69%.
- Best **base** hypothetical margin candidate: volatility-sized noise rule, 0.72% compounded monthly, worst month −2.30%, drawdown −3.81%.
- Best $2,000 result anywhere in the declared scenario matrix: opposite-band noise rule with fractional sizing under hypothetical margin, 0.83% compounded monthly. Choosing that winner after seeing all scenarios is selection, not a validated operating policy.
- Applying modern T+1 cash settlement counterfactually to 2022 prices, the strongest rule was opposite-band noise at 0.64% monthly, worst month −1.18%, drawdown −3.38%. This is explicitly a different account assumption, not how settlement worked in 2022.
- The $100,000 diagnostic with paper-style low slippage and no minimum commission reached 2.65% compounded monthly for volatility-sized noise. It is not a $2,000 result. Cost and position-rounding differences matter substantially.
- No candidate, benchmark or diagnostic generated a single ≥10% month in this five-month evaluation. This is evidence about this sample only, not a proof such returns are impossible elsewhere.

The Gao variants and the separately added whole-day-momentum rules lost money under the small-account base assumptions. Several noise variants were positive, but five months cannot establish their expected return or tolerable future drawdown. Apparent risk is particularly understated by a single short market episode. The results are historical simulations, not observed forward-paper executions.

## Research and validation

Primary mechanisms come from Gao/Han/Li/Zhou (2018), Zarattini/Aziz/Barbon (2025 revision), and Baltussen/Da/Lammers/Martens (2021). The [protocol](INTRADAY_V3.md) cites the papers and spells out each adaptation. The rest-of-day follow-up was registered **after** the first pilot results; it reuses the same history and is marked adaptive research.

The execution model observes completed bars, waits the configured delay and fills at a later minute's open with adverse slippage. It charges both sides, enforces settled cash, preserves zero-trade days and closes every position before the end of the session. The vendor's missing trade-VWAP field requires a disclosed HLC3 volume proxy. Short availability, broker house margin, quote spreads, order-book impact and exact tax/FX/exchange fees remain unverified.

**63 automated tests passed.** All 236 paths reconcile against 28,096 orders, with maximum dollar-level numerical discrepancy below $0.000000002. Tests cover future-information leakage, session completeness, short restrictions, costs, settlement, signal timing, pagination, bounded API retries and protected credentials. Unit and ledger checks validate implementation behavior; they do not establish profitability or certify external data.

## Multi-year run: prepared, not executed

The user agreed to arrange Alpaca data access. A private, Git-ignored `.env` template exists at the repository root. At the final check both key fields were still empty. Save the paper/data account's `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` there; do not put them in chat or Git. The importer only uses market-data GET endpoints.

[Alpaca's documented historical SIP access](https://docs.alpaca.markets/us/docs/market-data-faq) requires authenticated keys; requests ending at least 15 minutes ago can access historical SIP without the live SIP subscription, subject to actual entitlement. No data subscription or account funding was purchased.

The frozen [v4 specification](../configs/experiment_v4.json) retains all eight candidates. It uses 2016 warm-up, 2017–2020 diagnostics and 2021–2024 later evaluation. These are retrospective windows and include already-seen history, not a pristine holdout. 2025+ price bars remain reserved.

```sh
.venv/bin/python -m cash_cow.intraday.multiyear --fetch
.venv/bin/python -m cash_cow.intraday.multiyear --full
```

The first command validates the data and runs 44 base combinations; the second runs the full 440-combination matrix. Failures or missing minutes stop the run rather than generate invented prices. The actual authenticated import and long-history performance have not been tested yet. No rule is promoted to live funds from this pilot.

## Saved evidence

- [Initial intraday report](../reports/runs/20261102T060145Z_v3_intraday_pilot/RESULTS.md)
- [Whole-day follow-up report](../reports/runs/20261102T060520Z_v3b_rest_of_day/RESULTS.md)
- [Initial ledger verification](../reports/runs/20261102T060145Z_v3_intraday_pilot/VERIFICATION.json)
- [Follow-up ledger verification](../reports/runs/20261102T060520Z_v3b_rest_of_day/VERIFICATION.json)
- [All initial monthly returns](../reports/runs/20261102T060145Z_v3_intraday_pilot/monthly_returns.csv)
- [All follow-up monthly returns](../reports/runs/20261102T060520Z_v3b_rest_of_day/monthly_returns.csv)

Both run folders contain hash-verified source snapshots. Raw vendor data and detailed execution paths stay local.
