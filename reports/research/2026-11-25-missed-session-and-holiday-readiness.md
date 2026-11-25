# Missing November 24 session and holiday readiness

## New evidence

The November 24 US session is missing from the local session journal and closing accounting export.
The persistent STOP marker remains present and the installed `paper_ai_v1` service has no running worker.
There were zero new model decisions, orders or fills; absence of a decision is not a HOLD decision.
The cumulative decision archive remains 44 completed HOLD proposals with no new failures or pending requests.
The last recorded runner event is still the November 23 19:00:56 UTC stop documented in [yesterday's incident](2026-11-24-stopped-paper-session.md).

Readiness at November 25 08:08 UTC found the lid open, battery power at 67%, no worker idle-sleep assertion and an unmatched historical process manifest.
The STOP file modification time remains November 23 18:08:22.092664 UTC; its creator and purpose are not inferred from that timestamp.
The user's restart clarification is still unanswered, so maintenance preserves the stop, ownership files and frozen strategy.
This is not a new STOP request or an attempted restart.

Authenticated GET-only reconciliation at 08:08:13 UTC passed identity checks and found zero positions, zero open orders, zero pending intents and no cash discrepancy.
The paper sleeve remains USD 2,000 with zero modeled fill costs.
State SHA-256 remains `8c71bb2411632ed00eaea9c5343c67bf0290776f8b678d0bb7cec31d37b9841c`.
These are sequential snapshots, not continuous coverage or permission for funded execution.

The updated scorecard retains 15 elapsed scheduled sessions: 14 incomplete and one missing, with five still scheduled through December 2.
All 14 prior scorecard rows matched yesterday's snapshot exactly.
November 24 paper return remains unavailable because no closing accounting export exists.
Its hypothetical independent-day SPY reference is +0.2923158%, including USD 1.373684 modeled costs, two whole shares and 390 IEX minute bars.
This uses the frozen USD 2,000 daily reset, maximum 95% whole-share allocation with USD 1 reserve and max(USD 0.40, USD 0.0035/share) plus 2 bp per side.
The reference is not a broker fill or a compounded portfolio; there is no defensible strategy comparison for the missing session.
Reference snapshot SHA-256: `8bb3ff0bb313aef10bc886e1c79bc38f99ff8ec3a0a6f7c4880ea214932dd0b7`.
Full-month return, profitable months, target-hit months and worst month remain unavailable.

## Remaining calendar and recovery boundary

Today's authenticated Alpaca calendar still ends the original twenty-session trial on December 2.
November 25 has a normal 09:30-16:00 New York session, or November 25 22:30 to November 26 05:00 Singapore.
November 26 is absent from the trading calendar for Thanksgiving.
November 27 closes at 13:00 New York, or November 28 02:00 Singapore.
The frozen runner prohibits new entries on shortened sessions; the shortened day remains in the trial denominator.
There is no automatic trial extension to replace missed days.

Before any user-directed restart, reconcile again and verify sole service ownership, external power, open lid, connectivity, fresh news and a matching caffeinate assertion.
Opening the lid does not resume a service while STOP remains present.
Caffeinate prevents idle sleep only when running and cannot guarantee protection against lid closure, shutdown or network loss.
No state was reset, no stop cleared, no strategy changed and no funded trading activated during this review.
