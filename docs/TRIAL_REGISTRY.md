# Research trial registry

## paper_ai_v1 — prepared November 4, 2026; not activated

- User clarified that the requested live AI decision loop should use Alpaca simulated funds. Prepared a separate model-proposal experiment; no model API call or AI-directed order has occurred at registration.
- Model proposals use completed five-minute features, fresh quotes, timestamped news and event context. BUY/HOLD/EXIT replaces the ORB decision, while code retains the same execution/risk limits. Current model: GPT-6.1 Sol with low reasoning effort; prompt/config/source frozen on activation. Full protocol: `docs/AI_PAPER_TRIAL.md`.
- Configuration is disabled with a zero API budget pending the user's API-key and spending-cap choice. Actual model validation and a flat-account service cutover are required before activation. Do not report fixture tests as authenticated model execution.
- Initial quantitative baseline produced no orders in its first US session because of macOS sleep and a monitoring-gap block, not because it evaluated a full session and found no opportunities. Preserve the incident and do not claim either baseline or AI profitability.

## paper_orb30_v1 — prospective registration, 3 November 2026

- User authorized a continuously running Alpaca paper trial, later adding quantitative plus qualitative/news research. Registered before any paper fills or strategy outcomes. This is a new engineering baseline, not a v3/v4 winner or a claim of positive edge.
- SPY, free IEX observations, opening 30-minute range with completed five-minute close/VWAP confirmation; one long entry attempt per session from 10:05 until the last hour, whole shares, USD 2,000 sleeve, 95% maximum allocation. No shorts or borrowing. Exact rules and safety deviations are in `configs/paper_v1.json` and `docs/PAPER_RUNNER.md`.
- Prospective current-session observations begin when activated; older post-2024 historical prices remain reserved. No retrospective warm-up history is requested by this candidate. Short sessions have no entries; missing/stale data and monitoring gaps prevent new exposure.
- Performance must distinguish Alpaca simulated fills from a separate cost stress of max($0.40, $0.0035/share) plus 2bp per filled order. Account size, simulated fill rules, IEX feed and polling limitations remain visible. Cash is a zero-return baseline over the same observed periods; do not imply financing yield. Full-month comparisons require an exchange-session coverage audit.
- Freeze strategy/config through an initial 20 observed sessions unless a correctness/safety issue requires a halt. Assess reconciliation, attendance, rejects, costs and drawdown first. This window is not statistical validation. Retain losses, failed fills, no-trade sessions and outages.
- News collector preserves first-seen timestamps and article revisions separately; initial news/event context has no trading effect. A news-informed strategy or event blackout requires a new predeclared candidate and matched quantitative baseline. Paper fill performance cannot justify a funded deployment by itself.

## v4 — multi-year specification prepared 2 November 2026; not run

- User agreed to set up Alpaca data access. All eight v3/v3b candidates are retained in `experiment_v4.json`. Read-only SIP retrieval and validation are prepared, but no authenticated download or multi-year result is claimed until files pass checks.
- 2016 warm-up; 2017–2020 earlier diagnostic and 2021–2024 later evaluation. Both are retrospective; 2022 pilot and daily-market outcomes are already known. Preserve 2025+ prices unfetched.
- First stage: base account/rule/window combinations (44 including benchmarks). Second stage: full registered ten-scenario matrix (440 including benchmarks). No performance-based tuning between stages. API failure or incomplete sessions must stop evaluation rather than silently invent data.
- API transport improvements after v3/v3b completion add verified-cache resume and bounded retries only. The completed pilot's original source files were archived and hash-checked in each run's `source_snapshot.zip`; trading logic and those results were unchanged.

## v3b — rest-of-day follow-up, 2 November 2026

- Added after v3 aggregate performance was seen, prompted by the primary paper Baltussen/Da/Lammers/Martens (2021). Source: https://academicweb.nd.edu/~zda/intramom.pdf. Signal uses previous close to 15:30 direction to trade the final half-hour; fixed exposure and a declared hybrid volatility-sizing variant. No parameter search.
- Same five-month sample is explicitly reused. No new validation or significance claim. Two additional candidates × ten scenarios × two account models, plus two paper-cost and two T+1 diagnostics = 44 runs, separate configuration and output directory.
- V3 source files, rules and completed results are preserved. The source paper's diversified futures result is not represented as a reproduced SPY return.
- Completed `20261102T060520Z_v3b_rest_of_day`: 44 runs, 6,152 orders, reconciled NAV error below $0.000000001. Both variants lost money under base $2,000 assumptions. No tuning followed.

## v3 — intraday pilot specified 2 November 2026

- User requested intraday paper strategies, data acquisition and continued search toward 10% monthly. Six fixed variants from the two previously identified papers; no optimizer or performance-based rule addition/removal.
- Available licensed free SPY minute sample: July–December 2022, July warm-up and August–December evaluation. Date choice follows data availability before outcomes. No claim of multi-year validation. Account keys needed for the longer Alpaca SIP history were requested; not present at initial check.
- Six candidates × ten scenarios × two account models; three benchmarks under the same scenarios; six $100k paper-cost diagnostics; six current-T+1 counterfactuals = 192 runs. Cash and hypothetical margin accounts are separately labelled. More leverage is not silently made available to the cash account.
- All data remained unadjusted nominal prices with causal signals. Vendor daily/minute close conventions and blank minute VWAP were identified before simulations; HLC3 volume-weighted proxy and delayed execution deviations are recorded. Early-close trading is excluded in advance.
- No 2025+ price bars fetched. Five-month pilot cannot support robust inference; do not report annualized Sharpe, significance or monthly-income forecasts. The next multi-year experiment requires validated data access and a separate specification.
- Completed `20261102T060145Z_v3_intraday_pilot`: 192 runs, 21,944 orders, reconciled NAV error below $0.000000002. Best base cash 0.32% compounded monthly; best base hypothetical margin 0.72%. All five-month returns retained; no ≥10% month. Combined with v3b: 236 runs, 28,096 orders; 63 automated tests passed after adding read-only importer transport tests. No funded strategy promotion.

## v2 — specified 1 November 2026

- User explicitly requested more risk, a 10% monthly objective and research-paper grounding. This supersedes v1's allocation constraint for research only. USD capital remains an assumption. No live order capability or funded approval.
- Twelve fixed paper adaptations and seven passive references are specified in `configs/experiment_v2.json`, with ten sensitivities each; 120 candidate runs, 70 benchmark runs and 19 earlier-window diagnostics. Nine source papers; shared mechanisms mean correlated trials.
- Candidate allocation up to 95% at rebalances; actual 3× ETF histories for aggressive variants. No return multiplication, margin borrowing, shorting or options payoff invention.
- The 2016–2024 evaluation window was viewed in v1. This is adaptive, reused retrospective research. The disjoint 2011–2015 diagnostic is also historical. Post-2024 price bars remain unfetched; published papers and general market facts are not an information-free holdout.
- Before aggregate results, data inspection identified known 2025 splits and XLF's 2016 XLRE spin-off. Nominal units are reconstructed; the latter uses a documented cash-equivalent approximation instead of phantom XLF shares. Tests cover both. Sector findings remain provisional pending exact spin-off reconstruction.
- Primary paper mechanisms, formula changes and deferred intraday replications are in `PAPERS_V2.md`. No full replication claim for ETF adaptations. Parameters are configuration-driven, with no optimizer or performance-driven deletion.
- Retain every result. Two exploratory hypothesis families (matched-reference excess and 10% log growth), corrected by 44 across 22 declared v1/v2 candidate slots, do not cure adaptive sample reuse.
- Completed 2 November 2026: `20261102T021739Z_v2_papers`, 209 simulations. Highest base candidate compounded month 2.9847%, maximum drawdown 66.2655%; no 10% compounded-month candidate. No post-result parameter changes or candidate removals. All 209 exported paths reconciled against 47,725 trades; maximum currency discrepancy below $0.000000002. Forty-three automated tests passed. The source/config/data hashes match the run manifest.

## v1 — 1 November 2026

- User objective: US-market algorithm research, roughly $2,000 eventual capital, Singapore broker access, monthly performance, earlier low-risk preference.
- User has not confirmed capital currency or a dollar loss budget. Assumption for research: USD 2,000; 25% target exposure for candidates. No live approval.
- Ten candidate rules and ten sensitivity scenarios were specified in `configs/experiment_v1.json` before viewing aggregate strategy performance. Parameters were not fitted or grid-searched.
- Data sanity work inspected SPY observations and BIL's 2017 reverse split. A data-validation failure on that split led to explicit nominal-price reconstruction and a split-accounting test; no candidate was added or dropped because of performance.
- Candidate rules overlap economically; do not count them as ten independent edges.
- Run manifests preserve exact code, configuration and input hashes. The smoke download and unit tests were not performance selection trials.
- The first strategy screen is exploratory; 2016–2024 is retrospective validation and 2025 onward remains unfetched. Prior general knowledge of market history cannot be removed by a split.
- All ten candidate results must be reported, including losses. Cost scenarios and overlapping historical windows must not be counted as independent replications.
- Future rule changes require a new version and an explanation recorded before viewing the next holdout result. Record failed candidates rather than deleting them.
- First orchestration attempt stopped in the monthly-overhead scenario when the almost fully invested bill benchmark lacked settled cash to pay an operating expense. No aggregate report was produced. The engine was corrected to recognize the payable immediately, fund it through sales and block new buys until paid; a targeted accounting test was added. Candidate signals and parameters were unchanged. The incomplete run directory is retained locally.
- Completed run: `20261101T075044Z_v1_accounting_fix`. 100 candidate/scenario simulations, 30 benchmark simulations and 13 full-history diagnostics. No candidate passed the corrected positive-excess-over-bills test. No rule was retuned after viewing that result. Detailed evidence is in the run's `VERIFICATION.json`, `inference.csv` and `RESULTS.md`.
