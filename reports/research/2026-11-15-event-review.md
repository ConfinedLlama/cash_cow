# November 15 event and news review

Reviewed by 2026-11-15T08:48:24Z (review completion time).
This timestamp records today's primary-source review, not availability to an
earlier model packet. Publication dates, event dates and local collector
observations are separate. No runtime prompt, calendar or strategy was changed.

## Reverified schedule

| Event | Source-local time/date | Singapore time/date |
|---|---|---|
| NVIDIA FY2027 Q3 results | November 17, approximately 13:20 Pacific | November 18, approximately 05:20 |
| NVIDIA earnings call | November 17, 14:00 Pacific | November 18, 06:00 |
| FOMC minutes for October 27–28 | November 18; hour not verified here | Hour/date conversion pending verified release time |
| BLS JOLTS | December 1, 10:00 Eastern | December 1, 23:00 |
| BLS Employment Situation | December 4, 08:30 Eastern | December 4, 21:30 |
| FOMC meeting | December 8–9 | Do not infer a release hour from meeting dates |
| BLS CPI | December 10, 08:30 Eastern | December 10, 21:30 |
| BLS PPI | December 15, 08:30 Eastern | December 15, 21:30 |

The December BLS entries agree with `configs/event_watchlist_2026.json`.
The Fed also lists December 30 minutes. The calendar is a selected watchlist,
not an exhaustive list of market risks. Primary sources:
[BLS December calendar](https://www.bls.gov/schedule/2026/12_sched.htm),
[Federal Reserve](https://www.federalreserve.gov/monetarypolicy.htm),
[NVIDIA November 12 announcement](https://nvidianews.nvidia.com/news/nvidia-announces-ceo-transition).

## Facts, reported estimates and implications

- **Company announcement:** NVIDIA's November 12 release names Colette Kress
  interim CEO following Jensen Huang's resignation and reaffirms the November
  17 reporting schedule above. Today's vendor commentary about a comeback
  petition or an analyst's opinion is not a new company appointment or an
  earnings result. The official timing is after the regular US close; the
  effect on the next session is unknown. [Company source](https://nvidianews.nvidia.com/news/nvidia-announces-ceo-transition).
- **Trade enforcement:** USTR's November 13 release concerns an alleged labor
  rights denial at Industrias FG in Mexico and suspension of liquidation of
  entries from that facility. This is a facility-specific USMCA action, not
  evidence of a newly enacted economy-wide tariff. No quantitative SPY
  implication was established. [USTR release](https://ustr.gov/about/policy-offices/press-office/press-releases/2026/november/united-states-seeks-mexicos-review-alleged-denial-workers-rights-industrias-fg).
- **Oil estimates and forecasts:** IEA's November 13 report estimates October
  global supply at 105.4 million barrels/day and an observed inventory increase
  of 52 million barrels. It projects a fourth-quarter surplus while describing
  continued attacks on shipping and tight product supply. These are IEA
  estimates/forecasts, not proof that geopolitical risk has ended or a tradable
  equity-price forecast. [IEA November report](https://www.iea.org/reports/oil-market-report-november-2026).
- **Incident register revision:** IMO currently reports 136 confirmed incidents
  as at November 11 and 25 seafarer fatalities. The prior November 13 review
  recorded 134 against the same as-at date. This is an observed revision to a
  published aggregate; it does not establish two attacks occurred today.
  [IMO register](https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx).

## Local news evidence and limitations

The 08:43 UTC audit found 12,985 valid revisions, 12,934 distinct articles and
47 articles with multiple revisions. The collector had recently succeeded
without truncation or a current error, but still flagged a coverage gap.
Integrity of stored revisions does not imply completeness of world news.

Selected observations, retained privately rather than republishing articles:

- Oil-rebalancing vendor item: published November 14 at 16:15:08 UTC, locally
  first observed 16:19:19.824612 UTC. Today's IEA review corroborates the broad
  supply-recovery theme; its forecasts remain uncertain.
- NVIDIA comeback-petition commentary: published November 15 at 06:46:49 UTC,
  first observed 06:55:25.459972 UTC. Treat as reported commentary; no company
  decision or causal price effect was verified.
- NVIDIA analyst commentary: published November 15 at 07:29:36 UTC, first
  observed 07:35:33.901664 UTC. Opinion does not replace the official earnings
  schedule or constitute realized earnings.

Collector timestamps are not verified HTTP receipt timestamps. None of these
weekend observations was available to the last actual model decisions on
November 12. No model evaluation or order was triggered by this review.

An exploratory substring filter produced irrelevant matches (for example,
`PPI` inside another acronym and `USTR` inside longer words). Its category
counts were discarded. Whole-word filtering reduced those false positives,
but is still not a validated economic-event classifier. No classifier was
deployed and no trading result is attributed to this inspection.

## Next research step

Keep the running trial frozen. A separate news-informed comparison must retain
actual receipt cutoffs, source revisions, declared costs and a fixed evaluation
plan. Improved supply estimates, uncertain shipping risk, company leadership
changes and interest-rate speculation are competing context, not sufficient
evidence for a forced BUY. Reliable session coverage remains the immediate
operational requirement; no return or monthly target is inferred here.
