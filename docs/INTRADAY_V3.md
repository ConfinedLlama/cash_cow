# Intraday research protocol and data access

Specified 2 November 2026 before strategy performance was inspected. User requested the previously identified intraday papers, acquisition of necessary data and continued research toward 10% monthly. No live account is connected. This is a finite, registered experiment; no search-until-success optimizer runs.

## Available data and evidence limits

Downloaded [HistoricalData.net's free stock sample](https://historicaldata.net/samples.html): July–December 2022. SPY contains 109,105 total minute rows, of which 49,350 are regular-session bars across 127 sessions. Data is raw OHLCV in US Eastern time, with session labels and daily corporate actions. The [vendor methodology](https://historicaldata.net/methodology.html) describes raw versus adjusted prices. The license permits free sample evaluation; raw files stay local and are ignored by Git.

Checks: verify vendor file hashes, finite positive OHLC/volume, OHLC bounds, ordered unique timestamps, timezone/DST, exact NYSE calendar coverage including the 210-minute November 25 session, and daily/minute date consistency. No missing regular minutes were found. Compare daily closes with independently sourced cached Yahoo data: maximum difference under 0.001 basis point. This does not independently audit each minute or volume observation. Last-minute closes differ from published daily closes by up to 5.16 bp, so daily and minute-close definitions are kept separate. Minute VWAP fields are empty; a cumulative HLC3×volume proxy is explicitly used.

July is warm-up; **August–December 2022 provides five full evaluation months**. Dates follow sample availability, not performance. This is insufficient for reliable monthly-income estimates, statistical significance, general regime robustness, or an exact 17-year paper replication. No annualized Sharpe or inferential confidence interval will be reported from these five months. There is no parameter tuning on them. Future price bars from 2025 onward remain unfetched.

## Registered hypotheses

[Gao, Han, Li and Zhou (2018), Market Intraday Momentum](https://profiles.wustl.edu/en/publications/market-intraday-momentum/) studies predictability from the first half-hour, including overnight returns, to the last half-hour. The paper also discusses stronger effects under certain conditions. Our three implementations are:

1. `gao_first_half`: sign of 09:59-bar close relative to previous daily close, adjusted for today's known ex-dividend distribution; trade the final half-hour.
2. `gao_agreement`: additionally require the 15:00–15:30 move to agree. This is a fixed agreement heuristic, not a fitted paper regression.
3. `gao_high_volume`: require first-half-hour volume above its preceding 20-session median. This median rule is an explicit adaptation, not a reproduced paper threshold.

All hold to the scheduled flatten. No early-day volume or return is visible to a decision before 10:00. Cash accounts suppress negative directions; the hypothetical reference permits shorts.

[Zarattini, Aziz and Barbon, Beat the Market](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf), revised September 2025, motivates three further implementations. For each clock minute, estimate average absolute open-to-that-minute return using only the preceding 14 sessions. Bands use the larger/smaller of today's open and previous close, adjusted for known distributions. Observe at half-hour boundaries:

4. `noise_opposite_band`: enter beyond a band; hold until an opposite-band reversal or end of day.
5. `noise_current_vwap`: require price beyond both the relevant band and cumulative VWAP proxy; otherwise flat. Entry confirmation and current-band/VWAP exits are explicit conventions.
6. `noise_vol_target`: same rule, size by 2% divided by preceding 14 daily-return standard deviation, at most 4×. Cash version caps exposure at 1× before the 95% allocation factor.

The paper uses a $100,000 portfolio, IQFeed history and specific commission/slippage assumptions. Our five-month vendor sample, delayed fills, whole-share small-account sizing, VWAP approximation, entry convention and account constraints differ materially. These are causal implementations of paper mechanisms, **not a claimed reproduction of the published performance**. Author code was inspected for conventions but was not downloaded and executed as trusted code.

## Execution and account assumptions

A bar labelled 15:29 covers the minute ending 15:30. It can first inform a decision at 15:30. The base waits one further full minute and executes at 15:31 open with adverse slippage. Zero-extra-latency sensitivity fills at 15:30, never inside the signal bar. Two- and five-minute delays are also tested. These are bar-resolution delay models, not measured network latency.

Noise rules change desired direction only every half-hour. Positions are not resized continuously inside a trade. A reversal is a separate exit and entry, each charged fees. Repeated identical side signals do not create repeated opening orders. There are no intrabar threshold fills inferred from a bar's high or low. Every position is closed at the final regular minute's open (15:59); this differs from the paper's closing price and avoids assuming a late decision can enter the closing auction. All rules stay flat on shortened sessions, a declared adaptation.

Entry quantity uses start-of-day equity and that day's observed open. Whole shares in base; fractional sizes only in sensitivity, with no claim a broker offers them for every order type or short. New entries are capped at 1% of the preceding completed minute's volume. Full exits assume fills at stressed prices and do not simulate an order queue.

Cash model: $2,000, long-only, no borrowing, 95% target allocation. Sale proceeds are receivables and cannot fund another intraday purchase until settled. Historical settlement is T+3 before September 5, 2017, T+2 afterward and T+1 from May 28, 2024; the pilot therefore uses T+2. A conservative US bank-holiday exclusion supplements the NYSE calendar. This is not a complete clearinghouse settlement calendar. Six separately labelled **modern-T+1 counterfactuals** apply today's shorter cycle to 2022 prices; they are not the historical account simulation. See the SEC's [T+2 implementation](https://www.sec.gov/newsroom/press-releases/2017-163) and [T+1 notice](https://www.sec.gov/compliance/risk-alerts/shortening-securities-transaction-settlement-cycle).

Hypothetical margin model: $2,000, long/short, immediate capital reuse and up to the rule's specified leverage. It intentionally does not assert eligibility under historical or current account rules, short availability, locate/recall costs, short-sale restrictions, or broker house margin. A 25% maintenance ratio triggers liquidation at the next minute open and stops trading for the day; a gap can exceed that threshold. Short notional and negative cash incur a conservative 3% annualized intraday funding proxy. Borrow quotes and actual broker margin are not known.

Current rules must not be confused with old blanket PDT advice: [FINRA's new intraday-margin guidance](https://syndication.finra.org/content/understanding-new-intraday-margin-requirements) describes changes effective June 4, 2026 and a broker transition period through October 20, 2027. The specific Singapore account entity and broker implementation must be checked before any execution claim. This does not make the hypothetical $2,000 reference a funded-account recommendation.

Base costs: adverse 2 bp per side, commission max($0.40, $0.0035/share). They are research assumptions, not a verified all-in brokerage tariff. Tests include 5/10 bp, $1.10 minimum fee, $10 monthly overhead, fractional shares and half allocation. FX, GST, precise exchange/regulatory fees and paid data subscriptions are not reconstructed. Six separate $100,000 diagnostics use the paper's stated $0.0035/share fee and $0.001/share slippage, with no fee minimum and zero extra latency. They still retain our other implementation differences.

Three references run through the same engine: zero-interest cash, always-long intraday SPY, and always-long SPY in the final half-hour. They separate a signal's directional selection from merely holding intraday exposure. They are not overnight buy-and-hold benchmarks.

## Tests, accounting and reporting

Tests cover future-data invariance, session completeness, half days, exact signal availability, next-bar execution plus latency, T+2 cash reuse restrictions, T+1 transition, bank-holiday buffer, both-side transaction costs, disabled cash shorts, hypothetical short accounting, preceding-volume liquidity, and 14-session band inputs. Each run independently reconciles marked NAV from signed fills, costs and positions; it also checks flat overnight positions and nonnegative settled cash in cash models. Minute-close drawdown can miss intraminute extremes.

Report 120 candidate scenarios, 60 benchmark scenarios, six paper-cost diagnostics and six modern-cash counterfactuals: **192 runs**, all retained. Primary output is every actual monthly return, compounded month, worst month, minute-close drawdown, orders, fees, funding, blocked entries and forced liquidations. Scenario reuse does not create 192 independent observations. A promising sample ranking does not validate 10% monthly.

## Multi-year data path

[Alpaca's market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq) distinguishes consolidated SIP data from the single-exchange IEX feed and states that historical SIP requests ending at least 15 minutes ago do not require a subscription. Actual account entitlement must still succeed. The [historical-bars API](https://docs.alpaca.markets/us/reference/stockbars) supports explicit raw adjustment, SIP feed, timestamps and pagination.

No Alpaca keys were present in the local process when this work began. The user was asked to create data/paper access and save keys locally, never in chat. The read-only downloader uses only GET requests to `data.alpaca.markets`, with no trading or account-management endpoints. It preserves 2025+ price bars and refuses to overwrite downloaded files.

Create a local `.env` file in the repository with `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`. These names and `.env` are Git-ignored. Then download:

```sh
.venv/bin/python -m cash_cow.intraday.data --alpaca --start 2016-01-01 --end 2025-01-01
```

The downloaded raw minute/daily files require the same session and dividend alignment checks before a new registered multi-year run. Missing minutes must be examined, not silently filled. No paid dataset was purchased. Free samples from other vendors were shorter or lacked the required verified coverage; unverified community uploads and quote-volume substitutes were not used to fabricate a long test.

The v4 specification now preserves all eight candidates, including the separately registered rest-of-day follow-up below. It uses 2016 warm-up, 2017–2020 diagnostics and 2021–2024 later evaluation. These are retrospective windows; 2022 and broader market history were already inspected. The prepared command downloads and validates the raw SIP files, independently aligns cached dividend records, and runs the registered base cases:

```sh
.venv/bin/python -m cash_cow.intraday.multiyear --fetch
# After the base run, execute the full declared ten-scenario matrix:
.venv/bin/python -m cash_cow.intraday.multiyear --full
```

The base stage has 44 account/rule/window combinations; the full matrix has 440. Both include benchmarks. Outputs retain their stage, window and configuration, and are only marked complete after reconciliation. This pipeline is prepared and unit-tested; **the real authenticated multi-year download and run have not occurred yet**. A corrupt cache fails closed, valid cached downloads are reused, API retries are bounded and keys never enter manifests or reports.

## Additional paper and adaptive follow-up

After inspecting v3 results, a separate v3b experiment was registered from [Baltussen, Da, Lammers and Martens (2021), Hedging demand and market intraday momentum](https://academicweb.nd.edu/~zda/intramom.pdf). It studies rest-of-day returns predicting the closing half-hour across futures markets. Our SPY sign rule uses the previous close to 15:30 move, with fixed exposure and a separately labelled volatility-sizing hybrid. It does not reproduce the diversified futures portfolios or measured dealer gamma exposure. Two candidates, two account models, ten scenarios and four diagnostics add 44 runs. The same pilot is reused; this is explicitly adaptive historical research, not new evidence from an untouched sample.

Reproduce this pilot:

```sh
.venv/bin/python -m cash_cow.intraday.data --sample
.venv/bin/python -m pytest -q
.venv/bin/python -m cash_cow.intraday.run
```

Do not promote a rule from this pilot alone. Freeze it, test it over multiple independent market regimes with realistic costs, then log prospective paper signals before outcomes. A subsequent change needs a new trial entry and fresh evaluation.
