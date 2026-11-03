# Higher-risk research result

Completed 2 November 2026. Run: `20261102T021739Z_v2_papers`. Starting research capital: USD 2,000 per simulation, with a separate USD 1,000 sensitivity; currency assumption still unconfirmed.

**The higher-risk screen did not produce a 10%-per-month strategy.** The highest compounded monthly return among the twelve base-case candidates was 2.98%, with a 66.27% maximum drawdown. This is a much riskier research set than v1. The results do not support funding it to meet a monthly income target.

## Results that matter

Base evaluation: January 2016–December 2024, 108 months. Assumed costs and withholding included; recurring overhead and FX excluded from base. Compounded month is the constant monthly growth rate equivalent to the entire path, not what each month delivered.

| Method | Compounded month | Arithmetic mean month | Months ≥10% | Worst month | Maximum drawdown |
|---|---:|---:|---:|---:|---:|
| QQQ trend filter, trade TQQQ | 2.98% | 3.75% | 33/108 | −35.16% | −66.27% |
| Rotate UPRO/TQQQ on relative momentum | 2.90% | 3.99% | 39/108 | −35.16% | −66.27% |
| Inverse-variance TQQQ allocation | 2.61% | 3.16% | 31/108 | −24.75% | −44.85% |
| Passive TQQQ, 95% initially | 2.67% | 4.04% | 43/108 | −37.64% | −81.45% |
| Passive QQQ, 95% initially | 1.42% | 1.55% | 6/108 | −13.16% | −34.21% |

All twelve candidates and seven references appear in the [full results](../reports/runs/20261102T021739Z_v2_papers/RESULTS.md). Weak results were retained: weekly sector reversal compounded at −0.23% monthly, and most sector-selection variants trailed passive SPY in this window. More risk increased some historical returns, but did not establish additional alpha.

A 66.27% drawdown means a $2,000 **account peak** would fall to about $675 if that drawdown occurred from that peak. It does not mean the historical run necessarily lost that amount from its starting deposit. Drawdowns are marked daily and include open positions. Stops cannot guarantee protection through market gaps.

## Robustness and what did not transfer

The trend-filter candidate's growth was 2.00% monthly in the separate 2011–2015 diagnostic, below passive TQQQ's 2.96%. Its apparent advantage in the main period was not uniform across history. In 2016–2024 it earned 2.97% under higher commissions/slippage, 2.83% with one-session stale signals, 2.77% with $10/month operating overhead, and 1.70% when target allocation was halved. Lower allocation still left a 38.69% drawdown.

The inverse-variance candidate produced 2.58% monthly in 2011–2015 and 2.61% in 2016–2024. Its latter drawdown was smaller than the other leveraged candidates above, but **44.85% is still a severe loss**, not a low-risk strategy. Three-session stale information increased its drawdown to 49.64%. With $10/month overhead it compounded at 2.41% in the main period.

The leveraged-switch rule varied from 5.97% monthly in 2019–2021 to 0.73% in 2022–2024. Selecting a particularly favorable market block would dramatically exaggerate its typical record. The complete monthly series and three calendar blocks are exported.

The exploratory paired bootstrap tests found no positive **arithmetic mean excess return** over each candidate's matched passive benchmark after the declared correction. This test does not directly test a geometric-growth advantage: the trend rule's geometric return exceeded passive TQQQ despite its lower arithmetic mean because volatility affects compounding. Neither this finding nor an observed ranking establishes a durable edge. The separate 10%-log-growth tests also did not support the target.

## Paper basis and reproduction limits

The [paper mapping](PAPERS_V2.md) covers industry, relative and intermediate momentum; proximity to 52-week highs; short- and long-horizon reversal; time-series momentum; tactical trend; and volatility management. Twelve ETF implementations adapt nine sources. They are not exact replications of stock-level long-short or diversified futures portfolios. Source access and every material formula/universe change are disclosed.

Actual leveraged ETF histories were used. TQQQ's daily leverage does not imply three times the long-term index return. XLF's 2016 spin-off uses a documented cash-equivalent approximation; exact XLRE distributions and sale execution remain a data-quality follow-up for sector strategies.

The 2016–2024 sample was already viewed in v1. The earlier diagnostic is also retrospective. All scenarios share market history; ten sensitivities are not ten independent validations. Future price bars remain unfetched, but prior market knowledge and published literature prevent calling the design fully blind. These are historical simulations, not forward paper trades or independently audited executable results.

## Research decision and next experiment

No candidate is promoted to live trading, and no broker has been connected. For a **next frozen research evaluation**, the inverse-variance and trend-filter hypotheses are more useful to investigate than adding still more leverage just to reach a desired number. That is a research priority, not an allocation recommendation. A fresh test must retain passive comparators and all rejected variants.

The separate intraday queue contains Gao et al.'s early-to-late-session momentum and Zarattini/Aziz/Barbon's SPY noise-region breakout. They need historical minute data with timestamps and volume, paper-matched execution, a realistic $2,000 settled-cash account, and broker-specific costs. No intraday result is claimed here. Their publication figures should not be substituted for our own simulations.

For further work: validate a licensed data source and account permissions; freeze exact intraday entry/exit and fill conventions; preserve a fresh evaluation interval; then record forward paper orders before their outcomes. Reusing the same years until a strategy displays 10% monthly would select historical luck rather than establish the desired income.

## Audit files

- [Exact code/config/data hashes](../reports/runs/20261102T021739Z_v2_papers/manifest.json)
- [All 209 simulation summaries](../reports/runs/20261102T021739Z_v2_papers/summary.csv): 120 candidate sensitivities, 70 benchmark sensitivities, 19 earlier diagnostics
- [All base monthly returns](../reports/runs/20261102T021739Z_v2_papers/base_monthly.csv)
- [Exploratory statistical comparisons](../reports/runs/20261102T021739Z_v2_papers/inference.csv)
- [Independent trade-ledger reconciliation](../reports/runs/20261102T021739Z_v2_papers/VERIFICATION.json)
- [Chart](../reports/runs/20261102T021739Z_v2_papers/risk_return.png)

The automated tests cover accounting, execution timing, future-price invariance for all candidate rules, inverse-variance sizing, intermediate-momentum window selection, corporate actions and compounded-return interpretation. The ledger audit checks internal accounting and provenance; it does not certify the external vendor data or actual broker fills.
