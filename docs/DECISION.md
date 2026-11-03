# Initial decision: research continues; no funded strategy selected

**1 November 2026.** The first 100 candidate/scenario simulations are complete, with 30 benchmark simulations and 13 full-history diagnostics. All 24 unit tests pass. The accounting and timing audit checked all 130 validation account ledgers; the run's code/data hashes match the workspace and input cache.

Read the [full results](../reports/runs/20261101T075044Z_v1_accounting_fix/RESULTS.md), [research and broker comparison](RESEARCH.md), and [methodology](METHODOLOGY.md).

## What the monthly numbers actually say

2016–2024 historical screen, 108 months; USD 2,000 starting capital per account. Candidates target at most 25% invested at rebalance; most of the account remains in zero-interest cash. Returns include modeled order costs, slippage and distribution withholding, but exclude FX/remittance and recurring overhead unless specified.

| Portfolio | Average month | Profitable months | Worst month | Largest drawdown |
|---|---:|---:|---:|---:|
| 25% SPY benchmark | 0.30% | 69.4% | −3.17% | −9.10% |
| Volatility-target candidate, capped at 25% | 0.25% | 69.4% | −3.17% | −9.10% |
| Inverse-volatility trend portfolio | 0.07% | 58.3% | −1.00% | −3.25% |
| 99% BIL Treasury-bill ETF benchmark | 0.14% | 74.1% | −0.07% | −0.20% |

The strongest active candidate by average month equates to about **$5/month on a fixed $2,000 base**, before recurring overhead and currency effects. That is a scale illustration, not income or a forecast. Its drawdown fails our provisional low-risk screen. The only active candidate passing that provisional historical risk screen earned less than the bill benchmark on average.

**None of the ten candidates established positive monthly excess over bills at the 5% level after the specified multiple-testing adjustment.** This is failure to establish an edge in this screen, not proof that no edge exists.

Allowing up to full exposure improved the best candidate mean to about **0.85%/month**, accompanied by approximately **33.8% maximum drawdown and a −12.7% worst month**. That candidate was the moving-average crossover. Increasing exposure does not resolve the low-risk requirement.

Adding just **$10/month of operating costs made every candidate's average monthly return negative** in the dedicated conservative-allocation stress scenario. These costs were hypothetical; no subscription was purchased. A small account cannot ignore fixed expenses.

## What we can reasonably do next

Use **IBKR Singapore Pro, cash account, tiered pricing** as the first broker integration target, subject to onboarding and account-specific permissions. The source-backed reasons and Moomoo/Alpaca alternatives are in the research brief. No account creation or funding is necessary to review the present research.

Before spending money on market data or a server, confirm whether the budget is USD or SGD and define a dollar loss limit. Then independently check historical prices, distributions and exact account costs; decide whether low-turnover algorithm research still offers value at this account size. A strategy combining a small risky sleeve with an explicitly traded bill sleeve is a possible later hypothesis, not a tested result in v1.

If pursuing paper integration, first measure actual feed-to-fill latency and operational reliability, and freeze rules before prospective observation. The present results should not be used to choose a winner and repeatedly retune on the same validation years. All strategy changes must enter the trial registry.

## What has not happened

- No forward paper-trading session has run. These are historical simulations.
- No broker API session has been connected, so latency, order permissions and real paper fills are unmeasured.
- No 2025-or-later price history was downloaded for v1.
- No assertion that every possible trading strategy was tested. Ten practical rules were tested; intraday, options, shorting and news strategies require different data and models.
- No live orders, capital transfers, recurring automation, paid subscription, commit or push were made.

The repo is ready for review and further controlled research. It is not ready to trade the user's capital.
