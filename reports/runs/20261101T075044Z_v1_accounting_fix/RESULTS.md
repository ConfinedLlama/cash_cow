# Initial historical screening results

Research date: 2026-11-01. Run: `20261101T075044Z_v1_accounting_fix`. **No strategy is approved for live trading.**

Executed 10 candidate strategies × 10 scenarios = 100 validation simulations, plus 30 matched benchmark simulations and 13 full-history diagnostics. The scenarios overlap and are **not independent replications**. All trials are retained, including losing ones.

Validation: 2016-01-04 through 2024-12-31; 108 calendar months. Full-history diagnostics begin in 2008. 2025 onward was not fetched. These are historical rules chosen today, so the validation interval is a retrospective screen, not genuinely future evidence. No parameter optimization was performed.

Each candidate has its own USD 2,000 research account. Base target risky allocation is at most 25% at rebalances; prices can push realized exposure above the target between rebalances. This is not a 25% maximum-loss guarantee. `spy_25` is a matched-exposure equity benchmark; `bills_100` buys 99% BIL once with a fee buffer and holds cash distributions. Idle cash earns zero.

| strategy | mean_month | mean_month_usd_at_2000 | positive_month_fraction | worst_month | max_drawdown | orders |
|---|---|---|---|---|---|---|
| spy_25 | 0.30% | 5.94 | 69.44% | -3.17% | -9.10% | 36 |
| vol_target | 0.25% | 5.02 | 69.44% | -3.17% | -9.10% | 38 |
| ma_cross | 0.21% | 4.20 | 58.33% | -3.18% | -9.67% | 39 |
| absolute_momentum | 0.21% | 4.14 | 61.11% | -3.09% | -9.11% | 28 |
| sma200 | 0.17% | 3.48 | 60.19% | -2.65% | -7.21% | 35 |
| relative_momentum | 0.15% | 2.96 | 56.48% | -2.51% | -10.31% | 125 |
| bills_100 | 0.14% | 2.73 | 74.07% | -0.07% | -0.20% | 1 |
| dual_momentum | 0.13% | 2.50 | 54.63% | -3.10% | -11.31% | 39 |
| donchian | 0.11% | 2.23 | 47.22% | -2.16% | -5.03% | 52 |
| inverse_vol_trend | 0.07% | 1.41 | 58.33% | -1.00% | -3.25% | 82 |
| bollinger | 0.02% | 0.40 | 18.52% | -2.09% | -3.50% | 60 |
| cash | 0.00% | 0.00 | 0.00% | 0.00% | 0.00% | 0 |
| rsi2 | -0.01% | -0.24 | 32.41% | -2.34% | -5.17% | 144 |

`mean_month_usd_at_2000` multiplies historical average monthly percentage by $2,000 for scale. It is **not** a forecast, withdrawal income, or actual average monthly P&L in the compounding simulation. Flat months are not counted as profitable. NAV includes unrealized gains/losses and dividend/sale receivables. Final positions are marked, not liquidated.

## Screening checks

Within provisional historical risk limits (drawdown ≤5%, worst month ≥−2%): inverse_vol_trend.

Positive monthly excess over the bill benchmark passing the approximate one-sided block-bootstrap test after Holm correction across ten candidates: none.

This bootstrap uses paired monthly excess returns, 3-month circular blocks, 5,000 samples and a fixed seed. It is an exploratory estimate conditional on this history, not a guarantee. It does not cure data revisions, universe selection, prior knowledge of history, or future regime change. Changing blocks or adding strategies counts as further research trials.

## Important limits

- Research data from one unofficial vendor; not yet cross-checked against broker/issuer data.
- Next-session open with assumed slippage, no quote/queue/partial-fill/auction reconstruction. Delays are session-scale robustness tests, not measured network latency.
- $0.40 flat charge per order in the base case is a screening assumption, not an exact IBKR invoice. Higher fees and $10/month operating costs have separate scenarios.
- Three exchange-session sale settlement buffer throughout history; not an exact historical or current broker settlement calendar. Dividend cash is delayed 30 sessions; actual payable dates are not available. NAV recognizes entitlement on ex-date.
- Equity distributions are haircut 30%; Treasury ETF distributions assume zero withholding in base, with 30% on all distributions in tax stress. Fund-specific classifications and broker implementation are unverified.
- Fractional shares assumed in base; whole-share stress included. Reverse-split fractional entitlements are retained rather than broker-specific cash-in-lieu processing.
- No FX changes, conversion/remittance charges, Singapore personal income tax determination, or full infrastructure budget in base. USD results can differ substantially in SGD.
- ETF universe was selected today; it is not a survivorship-free whole-US-stock-market study. Several candidates share the same trend/equity exposure and are not independent sources of profit.

Read `docs/RESEARCH.md` and `docs/METHODOLOGY.md` before interpreting the CSVs. Forward paper trading has not started.
