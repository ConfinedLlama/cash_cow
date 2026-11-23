# Historical close-vintage investigation - November 23, 2026

## Question and scope

Could a stale saved Yahoo closing-price vintage explain the blocked v4 comparison?
This is a descriptive input investigation, not a strategy experiment or selection of a replacement price basis.
The request is bounded to January 1, 2016 through January 1, 2025 exclusive in New York time.
No historical bars in the reserved 2025+ period were requested for analysis.
The original caches, frozen v4 configuration, 10 bp threshold and evaluation plan remain unchanged.

## Observation

A read-only Yahoo chart request completed with HTTP 200 at 2026-11-23T11:25:33.645372+00:00.
It specified daily intervals, dividend/split events and no adjusted-close series.
The private request record retains period1 1451624400 and period2 1735707600, the request URL and response hash.
All 2,264 returned raw closes matched the saved Yahoo Close series exactly, with no missing dates or closes in the comparison.
The maximum relative close change was zero basis points.
The fresh series still differs from Alpaca daily closes by more than 10 bp on twenty dates, with maximum absolute difference 279.3449063488651 bp using `(Yahoo / Alpaca - 1) * 10000`.

The response SHA-256 is `305e4d449ea9e0921fb5bba01ce6469ca29c716517a3fb95e66c56f5ea2ae37f`.
Raw response and bounded comparison aggregates remain private under `.local/daily/2026-11-23-evidence/yahoo-repeat-*`.
This is a repeat of the same reference provider, not an independent third-source confirmation or proof that either vendor is correct.
The stale-Yahoo-vintage explanation is not supported by this observation.

## Remaining blockers

Yesterday's repeat Alpaca queries also matched their saved inputs exactly.
Today's separate halt audit reproduces 56 fully halt-contained missing minutes and 48 outside the four listed market-wide halt intervals.
It retains all original missing-minute, close-difference and exchange-local-boundary issues, returning exit 2.
It does not establish the cause of the four other gap dates or a symbol-specific reopening time.
The published halt reference was rechecked against the [exchange working-group report](https://www.nyse.com/publicdocs/nyse/markets/nyse/Report_of_the_Market-Wide_Circuit_Breaker_Working_Group.pdf).

The [Alpaca aggregation documentation](https://docs.alpaca.markets/us/docs/market-data-faq) describes eligibility differences by trade condition and bar type.
Those differences remain a hypothesis requiring trade-level or independently specified closing-price evidence, not a reason to choose whichever endpoint passes.
A bounded search of exchange material did not resolve the remaining gap dates; search absence is not evidence of normal trading.
No strategy returns were inspected, no gap was filled or discarded, and the 44 base and 440 sensitivity runs remain blocked.
Next obtain independently documented closing-price semantics and provenance for the unexplained intervals, then preregister any changed data/execution treatment before evaluating strategies.
