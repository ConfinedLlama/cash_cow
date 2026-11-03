# V2: higher-risk paper-based strategy adaptations

Research date: 2026-11-01. Run `20261102T021739Z_v2_papers`. **Historical research only. No live approval.**

Completed 120 candidate/scenario simulations, 70 benchmark simulations and 19 earlier-period diagnostics. Each run starts with its own $2,000 account, except the $1,000 sensitivity. Ten scenarios are overlapping sensitivities, not independent market histories.

The user authorized higher-risk research. Candidate allocation increased from 25% to 95% at scheduled rebalances; actual leveraged ETFs can add approximately 3× daily underlying exposure. This does not authorize a funded allocation. No borrowing or short sale is simulated; leverage is embedded in the ETF.

## Monthly target check

10% compounded monthly is 213.8% a year. A $2,000 account compounding at that rate for this 108-month sample would reach $59,079,933. Geometric monthly return measures compounded growth; arithmetic mean can be substantially inflated by volatile outcomes. Target-hit counts distinguish occasional big months from sustained growth.

| Strategy | Geometric month | Average month | Months ≥10% | Worst month | Max drawdown |
|---|---:|---:|---:|---:|---:|
| trend200_tqqq | 2.98% | 3.75% | 33/108 | -35.16% | -66.27% |
| relative_mom_3x | 2.90% | 3.99% | 39/108 | -35.16% | -66.27% |
| tqqq95_hold | 2.67% | 4.04% | 43/108 | -37.64% | -81.45% |
| inverse_variance_tqqq | 2.61% | 3.16% | 31/108 | -24.75% | -44.85% |
| qld95_hold | 2.25% | 2.83% | 27/108 | -25.84% | -63.34% |
| tsmom_tqqq | 2.12% | 3.04% | 33/108 | -35.18% | -66.04% |
| upro95_hold | 2.02% | 2.97% | 30/108 | -46.93% | -75.49% |
| qqq95_hold | 1.42% | 1.55% | 6/108 | -13.16% | -34.21% |
| sector_reversal_36m | 1.04% | 1.18% | 4/108 | -22.44% | -44.01% |
| tsmom_upro | 1.03% | 1.66% | 21/108 | -45.26% | -73.82% |
| spy95_hold | 1.02% | 1.11% | 2/108 | -11.70% | -31.53% |
| sector_mom12_skip1 | 0.93% | 1.01% | 1/108 | -9.40% | -28.87% |
| intermediate_mom12_7 | 0.90% | 0.98% | 1/108 | -9.91% | -28.88% |
| industry_mom6 | 0.87% | 0.95% | 2/108 | -10.94% | -31.76% |
| industry_mom_volscaled | 0.79% | 0.87% | 2/108 | -10.94% | -31.76% |
| sector_high52 | 0.67% | 0.75% | 0/108 | -11.71% | -30.17% |
| bills95_hold | 0.13% | 0.13% | 0/108 | -0.07% | -0.19% |
| cash_v2 | 0.00% | 0.00% | 0/108 | 0.00% | 0.00% |
| sector_reversal_week | -0.23% | -0.14% | 1/108 | -26.35% | -41.75% |

Base includes assumed slippage and per-order fees, 30% withholding on non-BIL cash distributions, and zero idle-cash interest. It excludes recurring overhead and FX; those limits still matter. The $10/month sensitivity is separate. Benchmark holdings start at 95%, then drift and retain distributions as cash.

## What was actually tested

Twelve **ETF adaptations** grounded in nine named paper sources: relative/industry/intermediate momentum, 52-week-high proximity, short/long reversal, time-series momentum, tactical trend and volatility management. Several variants share exposure. These are not exact reproductions of stock-level long-short or futures portfolios. The paper-to-code mapping, changes and data-dependent deferrals are in `docs/PAPERS_V2.md`.

Actual QLD/TQQQ/UPRO histories are used; no annual/monthly return is simply multiplied by leverage. Fund expenses and embedded financing effects are already reflected in those histories. Corporate cash distributions are accounted separately. Known 2025 split facts restore nominal historical units without fetching post-2024 price bars.

XLF's 2016 spin-off is represented by a documented $4.443564 cash-equivalent receivable per original share, conservatively taxed, rather than the vendor's fictitious 1.231 parent-share split. This is an approximation to disposing of the XLRE distribution; actual XLRE prices, payment dates and sale costs are not reconstructed. Sector results remain provisional for this reason.

## Interpretation and controls

- 2016–2024 is a **reused retrospective sample** already examined in v1. It is not a fresh out-of-sample test. 2011–2015 is separately reported; neither window is prospective.
- No parameter optimization or post-result strategy removal. All twelve candidates and seven benchmarks are retained. The trial registry records the scope change.
- `inference.csv` reports a paired 3-month block-bootstrap excess comparison versus a relevant passive benchmark, and a log-growth test against 10% monthly. A Bonferroni factor of 44 accounts for two hypothesis families across 22 declared v1/v2 candidate slots. It does not eliminate adaptive research, unrecorded choices or regime uncertainty. P-values are exploratory.
- Securities-sector composition changes, selection of surviving fund families, one-vendor revisions, share-split assumptions, and simplified fills/settlement/payable dates remain limitations.
- TQQQ history begins in 2010. This study does not establish survival through the dot-com crash or 2008 using that instrument. Earlier synthetic backfills would be separate modeled experiments.
- Higher risk is not evidence of higher alpha. Compare leveraged timing against leveraged buy-and-hold as well as unleveraged benchmarks.
- Every monthly return includes unrealized P&L; losers cannot be hidden by leaving trades open. No scheduled withdrawal or monthly income guarantee is modeled.

See `summary.csv` for all scenarios, `base_monthly.csv` for the complete monthly record, `subperiods.csv` for three calendar blocks, and `manifest.json` for exact code/config/data hashes. No broker API or forward-paper session has been connected.
