# Simulation specification and audit guide

This specification describes the implemented v1 historical screen. Research assumptions must not be mistaken for observed execution behavior.

## Reproduce

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m cash_cow.run --fetch --label v1
```

For an existing local data cache, omit `--fetch`. Raw files are personal research data, intentionally not tracked. The fixed package versions reflect the runtime installed during this study; the run manifest records Python and hashes. A future download may have vendor revisions, so a matching configuration does not imply matching input data.

`reports/LATEST.txt` identifies the latest completed run. Each run saves its exact configuration, source-file hashes and data hashes before simulation. Prior run directories are never overwritten. Check `manifest.json` and `data/manifest.json` before comparing results. The registry records that rules and scenarios were written before the first aggregate strategy report was read; this is a local research record, not independent preregistration.

In v1 the `fixed_parameters` JSON object documents the rules implemented in `strategies.py`; it is not a hyperparameter-tuning interface. Changing a rule requires changing that implementation, its registered specification and tests together. Scenario settings are read from JSON at runtime.

## Data and universe

Nine US-listed ETFs: SPY, QQQ, IWM, EFA, IEF, TLT, GLD, SHY, BIL. Download range begins 2006-01-01 and ends before 2025-01-01. BIL starts later; all required simulation sessions from 2008 must exist for every asset. Early rows are warm-up history. No missing tradable sessions are forward-filled. Check positive finite OHLC, OHLC consistency, duplicate dates, required sessions, reserved-date boundary, and unsupported capital-gain distributions.

Historical `Close` from Yahoo is split-adjusted, while `Adj Close` also adjusts for distributions. The engine does **not** add dividends to `Adj Close`. Signals use a forward total-return index formed from `(Close_t + dividend_t) / Close_(t-1)` in consistent split-adjusted units. Each daily observation only affects that day onward.

For share sizing, multiply prior OHLC and distributions by subsequent split ratios inside the downloaded range to restore nominal units. On a split day, holdings and pending desired quantities multiply by that ratio; no trading P&L is created. BIL's 2017 reverse split exercises this path. Fractional cash-in-lieu specifics and splits outside the fetched window are not independently audited. The data source's conventions remain an external assumption, not established by unit tests alone.

This is not a full point-in-time US-equity database. There is no delisted-stock universe, historical index membership, fundamental revision history or tick-level consolidated feed. Do not use this dataset to claim stock-selection alpha, options profitability or intraday execution quality.

## Signal and execution timing

- A close observation on session `t` may first influence a fill at the open of `t+1`.
- Delay stress adds one or three complete sessions to the information lag. Monthly and weekly strategies still rebalance on their calendar cadence, using the older observation; this tests stale signals, not rescheduling an order by measured milliseconds.
- Calendar boundaries are derived from observed exchange sessions. The initial simulation opens its account at the window start using previously available signals; it does not inherit a pre-existing live position.
- Monthly rules rebalance at the first observed session of a new month; weekly crossover at the first session of a new week. Donchian/RSI/Bollinger rebalance on state changes.
- Position budget is based on previous marked NAV, then quantity uses the simulated open plus slippage. That is an idealized next-open sizing/fill convention; actual fractional and auction orders may not support it exactly.
- Buys execute above the open and sells below it by the configured one-way basis points. A basis point is 0.01%. No assumption of spread capture is made.
- Orders under $25 are skipped, except full exits can be smaller. Nonzero target changes below $25 keep current holdings. This avoids expensive micro-rebalances but creates tracking error.
- Cash-limited purchases can remain pending and fill later as cash settles. Pending quantity is fixed until the next strategy rebalance and is canceled/replaced when its target changes. No short position or borrowing is allowed.
- Quantity precision is 0.000001 in fractional mode; whole-share mode rounds initial target/buy quantities down. Corporate-action fractions may remain in whole-share mode.
- Allocation caps apply at rebalance. Price movements can increase actual exposure afterward; this is not a continuous exposure enforcement system.

## Cash, distributions, costs

Cash starts at $2,000 in each independent candidate account. The half-capital stress uses $1,000. The ten simulated accounts are not ten simultaneous sleeves sharing the user's $2,000. Combining candidates would need a separate portfolio run and aggregate exposure limits.

Sale proceeds enter a receivable ledger and become spendable three observed exchange sessions later throughout the historical window. This deliberately simple buffer avoids same-day reuse of sale proceeds. It is not a precise historical settlement calendar and is more restrictive than current T+1 in ordinary cases. Exact historical T+3/T+2/T+1 transitions and bank holidays need an upgraded settlement adapter before execution validation.

Dividend entitlement accrues before trades at the ex-date open, so a new buyer on that date does not receive it. The net distribution is a receivable immediately and spendable after 30 sessions. This is a conservative cash-availability convention, not actual issuer payable-date accounting. Receivables remain in NAV throughout.

The base applies 30% withholding to equity ETF distributions (SPY/QQQ/IWM/EFA); it applies zero to Treasury ETFs, pending verification of fund classifications. Tax stress applies 30% to all distributions. There is no automatic dividend reinvestment: cash may be redeployed at later rebalances; the buy-and-hold bill benchmark retains distributions as cash.

All idle cash earns zero. Fund expenses already reflected in observed fund prices/distributions are not deducted twice. Per-order fees are a flat research approximation, not the broker's full tiered fee calculator. Any partial purchase on a later day is a separate charged fill. Exchange/regulatory charges, GST, FX and remittance are not individually reconstructed; high-cost stress explores some of that uncertainty but does not prove the total budget complete.

Monthly overhead is recognized at each first simulated session of a month in its dedicated scenario. If settled cash is insufficient, an expense payable immediately reduces NAV, new buys stop, and sufficient holdings are sold to fund payment after settlement. The bill benchmark may therefore need small sales in this scenario. No interest is modeled on that short-lived expense payable. This is an operating-expense convention, not a broker credit facility. v1 has no paid data/model calls or subscription purchase. Future hosting, data and model spending must be budgeted against a small account's dollar profits.

Final positions remain open and marked to close, so ending NAV is not net liquidation proceeds. There is no fictitious final-session round trip. Trades and marked P&L are both exported.

## Ten scenarios per candidate

| Scenario | Change from base | Interpretation |
|---|---|---|
| 01 | $2,000; 25% cap; 5 bps one-way slippage; $0.40/order | Baseline screen |
| 02 | 10 bps and $1.10/order | Higher execution friction |
| 03 | 25 bps slippage | Severe friction relative to daily ETF scale |
| 04 | One extra stale-signal session | Timing robustness |
| 05 | Three extra stale-signal sessions | More severe timing robustness |
| 06 | $1,000 account | Fixed-cost sensitivity; not a currency conversion |
| 07 | Whole shares | Small-account granularity |
| 08 | $10 monthly overhead | Data/cloud/model budget sensitivity |
| 09 | 30% withholding on all distributions | Tax-classification sensitivity |
| 10 | 100% candidate exposure cap | Research-only illustration of the return/risk tradeoff |

Benchmarks keep their definitions: cash, monthly 25% SPY allocation, and once-purchased 99% BIL. Fees/delays/capital/tax/overhead apply consistently within each scenario, but the benchmark weights do not become 100% SPY in scenario 10. These are overlapping tests, not ten different market histories.

## Evaluation windows and inference

Validation: 2016-01-04 to 2024-12-31, with a fresh account per run and earlier bars for indicators. Full-history diagnostic: 2008-01-02 to 2024-12-31. Those windows overlap and are not independent evidence. Crisis-year summaries mark performance in 2008, 2011, 2018, 2020 and 2022 along the full-history path, without resetting the account within each year. 2025 onward is reserved and not downloaded in v1.

Monthly returns use last marked NAV in the month divided by prior month-end NAV. For the first month, the denominator is starting capital, so first-entry fees and P&L are included. Report arithmetic mean, median, positive/negative months, best/worst month, compounded annual growth, largest peak-to-trough drawdown (including initial capital), worst day, annualized volatility, zero-cash Sharpe, order count, costs and average exposure. The zero-cash Sharpe is explicitly not a Treasury-excess Sharpe.

Primary comparison is paired monthly excess against `bills_100`. Use a circular moving-block bootstrap, block length three months, 5,000 draws and fixed seed; estimate a centered one-sided null p-value for positive mean excess and ordinary 95% bootstrap intervals. Apply Holm step-down correction to the ten candidate p-values. Confidence intervals remain marginal, not simultaneous. Serial dependence beyond the chosen blocks and regime shifts can invalidate nominal coverage; small samples and strongly correlated candidates reduce what we can conclude.

A sample passing both the provisional 5% drawdown/−2% worst-month limits and the corrected excess-return test is only an initial research screen. It has not passed future paper testing, independent data verification, risk-budget approval or production execution checks. No automatic live-promotion code exists. DSR, PBO, purged ML validation and strategy-parameter optimization are not implemented; do not label the bootstrap as any of them.

## Test coverage and remaining execution work

Automated tests exercise causal signal invariance under future-data changes, next-open timing and added delay, costs on both sides, nonnegative settled cash, sale settlement, ex-dividend entitlement/withholding, delayed dividend cash, split NAV preservation, whole-share rounding, initial-month accounting, Holm correction and deterministic zero-excess inference.

These tests validate specified behavior on constructed examples, not market profitability. Required later work includes exact broker fee/fill reconciliation, independent data QA, stale-feed detection, session holiday/early-close behavior, duplicate-order prevention, restart state recovery, pending-order expiry, partial/rejected fills, corporate cash-in-lieu, broker outage handling and live loss controls. None of those capabilities should be inferred from a successful historical run.
