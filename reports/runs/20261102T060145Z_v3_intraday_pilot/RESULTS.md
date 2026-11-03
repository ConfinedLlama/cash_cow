# Intraday pilot results

Run `20261102T060145Z_v3_intraday_pilot`. HistoricalData.net SPY sample. Evaluation **August–December 2022: five months**; July supplies warm-up. Availability-selected historical pilot, not fresh validation. No live approval.

Six candidate rules × ten scenarios × two account models = 120 candidate simulations. Three intraday/cash benchmarks × ten × two = 60 benchmarks. Six additional $100,000 paper-cost diagnostics and six modern T+1 cash-settlement counterfactuals. **192 completed runs**. Overlapping scenarios are not independent market histories. Hypothetical margin results cannot be treated as executable returns for the user's $2,000 account.

| Account / rule | Compounded month | Worst month | Minute-close drawdown | Orders |
|---|---:|---:|---:|---:|
| cash_long_only / noise_current_vwap | 0.32% | -0.61% | -1.69% | 60 |
| cash_long_only / noise_vol_target | 0.32% | -0.61% | -1.69% | 60 |
| cash_long_only / noise_opposite_band | 0.22% | -0.96% | -3.19% | 56 |
| cash_long_only / cash | 0.00% | 0.00% | 0.00% | 0 |
| cash_long_only / gao_high_volume | -0.52% | -1.46% | -2.71% | 40 |
| cash_long_only / gao_agreement | -0.66% | -1.77% | -3.43% | 52 |
| cash_long_only / gao_first_half | -0.77% | -2.10% | -4.02% | 78 |
| cash_long_only / intraday_always_long | -0.99% | -4.56% | -8.82% | 172 |
| cash_long_only / last_half_always_long | -1.32% | -2.38% | -6.47% | 162 |
| hypothetical_margin_long_short / noise_vol_target | 0.72% | -2.30% | -3.81% | 190 |
| hypothetical_margin_long_short / noise_opposite_band | 0.69% | -3.67% | -5.65% | 132 |
| hypothetical_margin_long_short / noise_current_vwap | 0.04% | -2.57% | -3.86% | 190 |
| hypothetical_margin_long_short / cash | 0.00% | 0.00% | 0.00% | 0 |
| hypothetical_margin_long_short / gao_agreement | -1.12% | -2.19% | -5.85% | 110 |
| hypothetical_margin_long_short / gao_high_volume | -1.30% | -3.57% | -6.40% | 100 |
| hypothetical_margin_long_short / gao_first_half | -1.84% | -3.72% | -9.04% | 212 |
| hypothetical_margin_long_short / last_half_always_long | -1.98% | -3.14% | -9.84% | 212 |
| hypothetical_margin_long_short / intraday_always_long | -2.59% | -5.45% | -15.47% | 212 |

## Mechanics and limits

- Raw minute OHLCV, New York timezone with DST, independently checked exchange calendar. All 49,350 regular bars across 127 input sessions passed coverage checks. One early-close day is deliberately flat. No forward-filled missing bars.
- Decisions use completed bars. Base execution waits one additional full minute: a 15:29 bar completes at 15:30 and fills at 15:31 open plus adverse slippage. End-of-day flatten is scheduled at 15:59 open, avoiding a fictional closing-auction fill.
- Gao first-half-hour direction includes the overnight move; penultimate-half-hour agreement and prior-20-session opening-volume median filters are declared adaptations. Noise rules use prior 14 same-clock moves, 30-minute decisions, opposite-band or current-band/VWAP exits. Volatility sizing uses previous 14 daily returns and a 2% daily target capped at 4× in the hypothetical account. No optimizer.
- VWAP uses cumulative HLC3×volume because the sample's minute VWAP field is blank. Both accounts are adaptations, not exact reproductions of published performance.
- Cash account: long-only, at most 95% target exposure, no proceeds reuse before settlement. Historical T+2 in this sample, with a conservative bank-holiday buffer. Whole shares in base. Margin diagnostic permits shorts and immediate capital reuse. Broker eligibility, PDT, locate, short-sale price restrictions and borrowing availability are not modeled. A 25% maintenance threshold triggers next-bar liquidation, not a broker-certified margin model.
- Base costs: one-way slippage 2 bp, fees max($0.40, $0.0035/share), 3% annual intraday financing/borrow proxy. FX, exact exchange/regulatory/GST charges and paid data expense are excluded. $10 monthly overhead is a separate sensitivity. Entry liquidity uses at most 1% of the preceding completed minute's volume; closing fills assume full availability at stressed prices.
- Drawdowns use minute closes and cannot capture every intraminute extreme. Exposure stops are not guaranteed loss caps.
- Only five evaluation months: no annualized Sharpe, inferential confidence interval, significance claim or long-run forecast is produced. Check both compounded growth and the count of actual months reaching 10%.

Every result is retained in `summary.csv`, every monthly return in `monthly_returns.csv`, and detailed paths/trades in local ignored subfolders. `VERIFICATION.json` checks every NAV path against signed fills. See `docs/INTRADAY_V3.md` for sources and multi-year data requirements. 2025+ price bars remain unfetched.
