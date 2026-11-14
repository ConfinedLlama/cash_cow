# Paper progress scorecard v1

Registered November 15, 2026 before fetching reference prices. This is an
evaluation/reporting change, not a trading signal or change to paper_ai_v1.

Keep all scheduled sessions starting November 4, including missed and blocked
days. Show actual paper accounting returns alongside cash (zero interest) and
a hypothetical SPY regular-session reference. For each day independently,
start with USD 2,000, buy whole shares at the opening minute's open using at most
95% allocation minus a USD 1 reserve, sell at the last regular minute's close,
and subtract max(USD 0.40, USD 0.0035/share) plus 2bp of notional on each side.
The reference resets capital daily: do not sum or compound its daily returns
and label them a realized portfolio. It is not a buy-and-hold benchmark.

Use raw IEX one-minute bars, matching the trial feed. Endpoint minutes must
exist exactly; do not substitute later opens or earlier closes. Missing or
invalid evidence stays unavailable. No market-price data before trial start
or beyond December 2 (the original twenty-session window) may be fetched by
this tool. Require sessions to have closed at least fifteen minutes earlier.
Preserve fetched snapshots privately, including receipt time and source hash.
These retrospective reference bars cannot become historical model inputs.

Report unique model decisions separately from repeated polls, submitted orders
separately from fills, and coverage separately from accounting return. Broker
reconciliation and service health remain separate checks. Frozen strategy
success requires evidence of actual fills and reliable coverage; do not infer
skill from cash outperforming SPY on days the computer slept. Full-month
performance remains unavailable until independently verified complete months.

The SPY reference uses bar prices, not executable bid/ask quotes or simulated
broker fills. The stress model does not capture market impact, timing,
queue priority or all real-world fees. Subscription/hosting costs are separate.
No new brokerage orders, model calls, or runtime changes are made by this tool.

Usage (new private destination each fetch):

```sh
.venv/bin/python -m cash_cow.paper.scorecard --fetch data/research/scorecard-YYYYMMDDTHHMMSSZ.json
.venv/bin/python -m cash_cow.paper.scorecard --snapshot data/research/scorecard-YYYYMMDDTHHMMSSZ.json
```

Only aggregate returns/costs and source hashes may be published. Raw bars,
account identifiers and private telemetry stay out of Git.
