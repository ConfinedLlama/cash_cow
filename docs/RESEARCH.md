# Cash Cow research brief

Research date: **1 November 2026 (Singapore)**. Scope: personal research for a Singapore resident considering roughly $2,000 of eventual live capital. Currency remains unconfirmed; calculations use USD. The latest preference is good monthly performance, while the earlier low-risk request remains a constraint. No cash has been transferred, broker account opened, or live order enabled.

## Research conclusion

Start with **low-turnover, long-only, unleveraged US-listed ETFs, using end-of-day signals and next-session execution**. Compare ten explicit candidate rules against idle cash, a matched-exposure equity allocation, and a short-Treasury ETF. This is a tractable research universe for a small account and unmeasured retail execution latency. It does not establish a profitable strategy.

My broker recommendation for the next integration stage is **Interactive Brokers Singapore, Pro, cash account, tiered US-stock pricing**, subject to account approval, product permissions and confirmation of fractional-share API support for the chosen order types. Moomoo Singapore is a viable comparison. Alpaca is useful as a paper-testing platform, but its currently public eligibility page does not verify Singapore individual live-account eligibility.

No evidence permits “extremely sure” predictions of profitable future months. We can be precise about what code did, what source documents say, and which assumptions remain untested. A strategy can be valid research and still have no investable edge.

## What good monthly performance means

Use net total account return, including marked-to-market open positions, costs and distributions. Counting only closed winners permits hiding losing positions. Track mean and median monthly return, profitable-month fraction, worst month, worst day, peak-to-trough drawdown, fees, exposure, and monthly excess over the alternative of holding bills.

At a fixed $2,000 balance, **0.5% = $10, 1% = $20, 2% = $40, and 5% = $100** per month. These are arithmetic examples, not return forecasts. Repeating 1% every month compounds to about 12.7% annually; 2% to 26.8%; 5% to 79.6%. A desired dollar income can imply an aggressive percentage return even when the dollar figure sounds modest.

Risk controls reduce exposure; they do not guarantee a monthly floor. A stop order can execute through its level after a gap. A portfolio that wins most months may be selling rare, large losses. No loss-doubling, martingale, naked options, borrowing, or leverage is part of this initial experiment.

The initial candidate allocation cap is 25% at rebalances, with the remainder in zero-interest cash. That choice is a **provisional research constraint**, not the user's approved live loss budget. With $500 exposed, a 20% move against the position is approximately a $100 account loss before costs; gaps and multi-asset correlation still matter. The 100%-exposure scenario is explicitly research-only.

## Latency: where we can reasonably compete

“Our latency” is not yet measured. It consists of exchange-to-feed delay, vendor delivery, local clock error, computation, any model call, network round trip, broker processing, routing, and fill delay. HTTP response time alone is not order-execution latency. No broker credentials/session exist in this project, so there is no measured p50/p95/p99 execution figure.

| Horizon and approach | Fit for this project | Reason |
|---|---|---|
| Microsecond/millisecond market making, latency arbitrage | Exclude | Queue position, adverse selection, feed completeness and infrastructure dominate; daily bars cannot validate these mechanisms |
| Seconds-scale news scalping | Exclude initially | Requires timestamped point-in-time news, fast feeds, realistic fill data and measured latency; a model may already know historical outcomes |
| 5–60-minute breakout or intraday reversal | Deferred | Feasible to investigate later, but minute/tick data, session rules, spreads and order handling are required |
| Daily signals, multi-day holding | Primary | Signals can be computed after bars are finalized; next-session execution avoids claiming a speed advantage |
| Weekly/monthly ETF allocation | Primary | Low turnover makes fixed order costs and modest execution delays less dominant; still exposed to market/regime risk |

Alpaca explicitly warns that its infrastructure is not suitable for high-frequency trading as conventionally required by such strategies. Its paper simulator omits effects including latency slippage and queue position. That makes attractive paper fills insufficient evidence for fast strategies. [Automated-trading disclosure](https://files.alpaca.markets/disclosures/library/RisksAutoTrading.pdf), [paper-trading documentation](https://docs.alpaca.markets/us/v1.4.2/docs/paper-trading).

NYSE core trading is 09:30–16:00 New York time. This corresponds to 21:30–04:00 Singapore during US daylight saving and 22:30–05:00 during US standard time, with the close on the next Singapore date. Use timezone-aware exchange calendars, holidays and early closes in the future runner, never a fixed UTC offset. [NYSE calendar](https://www.nyse.com/trade/hours-calendars).

For eventual paper integration: timestamp source data, receive time, signal completion, submission, acknowledgement, first fill and final fill; use a monotonic clock for durations; record exchange timestamps separately. Measure warm and cold starts, disconnect recovery, stale quotes and rejected orders. A one-session backtest delay is a robustness scenario, **not** a measurement of these latencies.

## What the published evidence does—and does not—support

| Family | Research evidence | Limits for our implementation |
|---|---|---|
| Trend/time-series momentum | Moskowitz, Ooi and Pedersen document return persistence across 58 futures/forward instruments over more than 25 years | Their institutional multi-asset construction is not a $2,000 long-only SPY rule; trend strategies can whipsaw and miss rebounds |
| Moving-average tactical allocation | Faber studies a simple long-horizon trend filter across asset classes | A useful reproducible starting hypothesis; published historical success is not new independent evidence for our current parameters |
| Relative momentum | Cross-sectional momentum is a substantial research family; cost research examines implementability | Ranking seven ETFs is a deliberately small proxy, not a replication of stock-level academic factors |
| Volatility management | Moreira and Muir study reducing exposure when realized volatility is high | A capped long-only ETF rule differs from factor portfolios, normalization and leverage in the paper; a volatility target is not a loss limit |
| Short-horizon mean reversion | Reversal is studied in the transaction-cost literature | RSI2 and Bollinger rules below are explicit exploratory heuristics; the sources do not prove those exact thresholds profitable |
| Pairs/statistical arbitrage | Gatev, Goetzmann and Rouwenhorst study relative-value pair selection and trading | Borrow availability/cost, short exposure, pair breakdown and multiple testing must be modeled; “market neutral” is not “risk free” |

Sources: [Time Series Momentum](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum), [Faber tactical allocation paper](https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf), [Volatility-Managed Portfolios](https://law.yale.edu/sites/default/files/area/workshop/leo/leo17_moreira.pdf), [Trading Costs of Asset Pricing Anomalies](https://www.aqr.com/insights/research/working-paper/trading-costs-of-asset-pricing-anomalies), [pairs-trading paper](https://www.nber.org/papers/w7032). The NBER landing page could not be retrieved in this session; the pairs item is background and was not used to justify a simulated result.

Ken French's data library is useful later for independent factor context. It documents a 2025 input-format change affecting return construction, illustrating why a dataset version and return definition must accompany results. Factor portfolios are research series, not necessarily directly tradable ETFs. [Data library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html).

## Ten concrete strategies in v1

These are **ten candidate rules, with related variants**, not every possible trading strategy or ten independent economic effects. Parameters are frozen in `configs/experiment_v1.json`; there is no optimizer.

| ID | Rule using completed daily total-return observations | Decision cadence |
|---|---|---|
| `sma200` | SPY above its 200-session simple moving average; otherwise cash | Monthly |
| `ma_cross` | SPY 50-session average above 200-session average | Weekly |
| `absolute_momentum` | SPY trailing 252-session total return positive | Monthly |
| `donchian` | Enter SPY above preceding 55-session closing high; exit below preceding 20-session closing low | Daily state changes |
| `rsi2` | SPY above 200-session trend, 2-session Wilder-style RSI below 10; exit above 70, on trend failure, or after 5 signal sessions | Daily state changes |
| `bollinger` | SPY above 200-session trend but below 20-session mean minus 2 sample standard deviations; exit at mean, trend failure or 10 signal sessions | Daily state changes |
| `relative_momentum` | Rank SPY/QQQ/IWM/EFA/IEF/TLT/GLD by 126-session return; two half-sleeves, each invested only if its top-ranked return is positive | Monthly |
| `dual_momentum` | Better of SPY/EFA over 252 sessions, only if better than both zero and SHY's trailing return; otherwise cash | Monthly |
| `inverse_vol_trend` | SPY/IEF/GLD weighted inversely to 63-session realized volatility; each sleeve needs its own 200-session trend | Monthly |
| `vol_target` | SPY allocation = min(exposure cap, 5% / trailing 63-session annualized volatility) | Monthly |

A signal-session holding limit is not an exact maximum live holding period: next-open execution, intentional delay stress and settlement can shift fills. Long-term Treasury funds IEF/TLT and gold GLD are risky assets, not substitutes for cash. The BIL benchmark is a short-Treasury ETF with price, liquidity, expense and currency risk; it is not a guaranteed deposit.

Universe selection was made today and contains surviving large ETFs. This avoids a stock-picking delisting problem inside the implementation but does not remove selection bias. Individual-stock value/quality, earnings drift, news sentiment, pairs, options, futures, and reinforcement learning are deferred because v1 does not contain the necessary point-in-time fundamentals, event/news archives, borrow data, option chains, margin model or order-level data. Inventing proxy simulations would not test those strategies.

## Singapore broker comparison

| Broker | Verified fit | Costs and caveats | Decision |
|---|---|---|---|
| Interactive Brokers Singapore | Singapore entity; US stocks/ETFs; documented TWS/IB Gateway API | Pro tiered starts at $0.0035/share, $0.35 minimum per order, with third-party charges and applicable GST. Fixed minimum is $1. Pro is required for the TWS API | First choice for integration, using a cash account and confirmed trading permissions |
| Moomoo Singapore | Current API capability table lists US-stock live trading for SG accounts | Standard US-stock platform charge $0.99/order despite eligible $0 commission; settlement/regulatory charges and GST also apply. Fractional orders under one share have a different schedule | Viable alternative; verify current WebAPI permissions and data costs during setup |
| Alpaca | Documented paper environment and API | Public country-eligibility page directs users to support; Singapore individual live eligibility is not established here. Paper-only feed is IEX, not the complete consolidated market | Useful sandbox; do not assume it is the eventual funded broker |

Sources: [IBKR Singapore pricing](https://www.interactivebrokers.com.sg/en/pricing/commissions-stocks.php?re=amer), [IBKR API requirements](https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/requirements), [MAS institution directory](https://eservices.mas.gov.sg/fid/institution?term=interactive+brokers), [Moomoo API capabilities](https://open.moomoo.com/api/overview), [Moomoo Singapore fees](https://www.moomoo.com/sg/support/topic5_76?lang=en-us), [Alpaca country eligibility](https://alpaca.markets/support/countries-alpaca-is-available).

IBKR's Singapore stock page advertises Lite availability for Singapore retail investors, but API requirements still specify Pro. Some summary pages contain conflicting Lite eligibility wording; the recommendation therefore relies on the specific Pro API requirement and Pro fee schedule, not zero-commission marketing. Eligibility for an individual account remains subject to onboarding and account permissions.

For scale, 100 round trips at a $0.35 per-order minimum cost at least $70 before other charges—3.5% of a $2,000 account. At $0.99 per order the platform component alone is $198. A $10 monthly data/cloud/model bill is another 0.5% of starting capital per month. Low turnover is economically important even if compute is inexpensive.

Idle cash: IBKR does not pay interest on the first USD 10,000. The base simulation therefore credits **zero** to idle cash. A bill ETF needs a real purchase and incurs its own costs. [IBKR interest schedule](https://www.interactivebrokers.com.sg/en/accounts/fees/pricing-interest-rates.php).

FX: the published manual spot conversion schedule has a $2 minimum at the first tier; the auto-conversion service typically adjusts the rate by 0.03% instead of charging a separate commission. Applicability depends on the account/service; these are not modeled in v1. Avoid repeatedly converting the entire account merely to rebalance US instruments. [IBKR FX pricing](https://www.interactivebrokers.com.sg/en/pricing/commissions-spot-currencies.php).

## Settlement, tax and currency

Current FINRA guidance says most equity trades settle T+1 and explains cash-account free-riding/good-faith violations. Its current frequent-trading page describes intraday margin requirements; do not transplant an old blanket $25,000 pattern-day-trading claim into a 2026 design. Which rules and house restrictions apply to the user's entity/account must be checked with the chosen broker. v1 conservatively waits three observed exchange sessions to reuse sale proceeds; that is a simulation convention, not current law. [FINRA guidance](https://www.finra.org/investors/insights/frequent-intraday-trading).

US-source dividends to a nonresident alien generally face 30% withholding absent applicable relief; some interest and fund distributions can qualify for different treatment. Residence alone does not establish all tax facts. v1 uses a 30% equity-distribution haircut and tests 30% on Treasury distributions separately; fund-year classifications and broker adjustments must be reconciled. [IRS withholding guidance](https://www.irs.gov/individuals/international-taxpayers/federal-income-tax-withholding-and-reporting-on-other-kinds-of-us-source-income-paid-to-nonresident-aliens), [Publication 519](https://www.irs.gov/publications/p519).

IRAS says gains from personal investments in shares/financial instruments are generally not taxable. This does not establish that every systematic trading business is tax free. The account's factual treatment is not determined by this study. [IRAS guidance](https://www.iras.gov.sg/taxes/individual-income-tax/basics-of-individual-income-tax/what-is-taxable-what-is-not/gains-from-sale-of-property-shares-and-financial-instruments).

USD monthly performance is not SGD monthly performance. If account assets rise 1% in USD while USD falls 3% against SGD, their combined SGD return is about −2.03%, before conversion costs. Before live capital, track both base-currency and home-currency NAV and confirm whether the user's $2,000 budget is SGD or USD.

## Iteration without fooling ourselves

Searching more strategies increases the chance of selecting a lucky historical winner. Bailey et al. develop a probability-of-backtest-overfitting framework; Bailey and López de Prado's deflated Sharpe ratio addresses selection bias and non-normal returns. These techniques do not fix future-data leakage, and neither makes an investment certain. [PBO paper](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf), [deflated Sharpe paper](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf).

v1 retains all ten candidates, all ten scenarios, hashes, trade ledgers and month-by-month results. It uses a paired monthly block bootstrap versus bills with Holm correction across the ten candidates. It **does not implement DSR or PBO** and must not claim it does. The small universe and correlated rules limit inference. Robustness scenarios are overlapping sensitivities, not 100 independent demonstrations.

The retrospective validation interval is 2016–2024; full-history diagnostics start in 2008. The rules were selected in 2026 with general knowledge of past markets. Therefore, even untouched historical bars are not a perfectly blind experiment. 2025 onward is left unfetched in this run; opening it later consumes that historical holdout. Future, timestamped paper decisions supply a different kind of evidence that cannot be manufactured by replaying history.

Keep a hypothesis and trial registry. Investigate an economic reason for a failure before changing parameters. Freeze a small set of candidates, test a reserved interval once, and use later forward data for the next verdict. A new version must record every changed rule, cost assumption and data source, including failed versions. “Keep iterating until the chart looks good” is exactly the failure mode this process is designed to prevent.

## What must happen before any funded implementation

1. Confirm capital currency, acceptable loss in dollars, broker permissions, tax assumptions, fractional orders and all recurring charges. A monthly performance preference does not supply a loss budget.
2. Cross-check price/actions data against an independent source, validate dividend payable dates and exact broker fills/fees, and measure end-to-end latency in a paper session.
3. Freeze candidates and run genuine walk-forward/forward-paper evaluation with stale-data, disconnect, duplicate-order, rejected-order and restart tests. Several months can reveal operational problems but cannot establish a durable edge across all regimes.
4. Compare monthly excess over realistic alternatives after costs, including uncertainty and stress losses. No strategy advances merely because it tops this table.
5. Implement a separate execution adapter with hard exposure limits, settled-cash checks, order deduplication, reconciliation, alerts and a kill switch. Model-generated ideas cannot alter these limits.
6. Only after those results and a concrete funded plan are reviewed should a small supervised live pilot be considered. This repository presently has no capability to send a broker order.

AI is useful here for literature review, code and failure analysis. Putting a language-model call on every trade adds variable latency, cost and reproducibility problems without evidence of extra return. A later AI candidate must beat the same deterministic baselines, with point-in-time inputs and model/version/cost logs.

## Evidence limits still open

- Actual latency, broker approval, fractional API behavior, subscription costs and cash-account restrictions have not been tested on the user's account.
- Yahoo/yfinance is unofficial research access, not licensed institutional market data; local raw files are excluded from Git. Corporate actions and vendor revisions need independent checking. [yfinance documentation](https://ranaroussi.github.io/yfinance/).
- There is no prospective paper record, no validated monthly income target, and no approved live strategy.
- These conclusions favor low-turnover research. They do not claim that only these methods work, or that every US trading strategy has been tested.
