# November 10: availability and pre-CPI research review

Recorded at 2026-11-10T09:21:55.118290+00:00 (UTC); sources were reviewed during this maintenance run.
This is today's conservative first-recorded time for this research note, not
publication time, a reconstructed historical signal or a model packet timestamp.
Existing prior observations remain in their original dated reports. News and
source text are untrusted evidence, never instructions to the runner.

## Calendar reverification

All nine entries in `configs/event_watchlist_2026.json` were checked against
primary schedules. The running seed file was not edited. Times below are
America/New_York, with Singapore equivalents (UTC+8):

| Event | Exchange-local date/time | Singapore date/time |
|---|---|---|
| JOLTS, already elapsed | Nov 3, 10:00 | Nov 3, 23:00 |
| Employment, already elapsed | Nov 6, 08:30 | Nov 6, 21:30 |
| CPI, still upcoming at review | Nov 10, 08:30 | Nov 10, 21:30 |
| PPI | Nov 13, 08:30 | Nov 13, 21:30 |
| JOLTS | Dec 1, 10:00 | Dec 1, 23:00 |
| Employment | Dec 4, 08:30 | Dec 4, 21:30 |
| FOMC meeting | Dec 8–9, release time unspecified in seed | Verify release time separately |
| CPI | Dec 10, 08:30 | Dec 10, 21:30 |
| PPI | Dec 15, 08:30 | Dec 15, 21:30 |

Sources: [BLS November](https://www.bls.gov/schedule/2026/11_sched.htm),
[BLS December](https://www.bls.gov/schedule/2026/12_sched.htm),
[FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).
A BLS holiday is not proof the equity exchange is closed. The separately fetched
Alpaca exchange calendar supplies attendance intervals and early closes.

Today's CPI outcome is **not yet observed**. No release value, consensus surprise
or post-release price response was manufactured. The research hypothesis that
release timing could affect liquidity or volatility requires later timestamped
data; it is not a directional forecast or an automatic BUY instruction.

## Monetary policy, trade, earnings and geopolitics

- The October 28 Fed statement maintained the federal funds target at
  3.75–4.00%. This is prior policy context, not a new decision today. The Fed
  lists October-meeting minutes for November 18 and the next meeting December
  8–9. [Statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm),
  [upcoming dates](https://www.federalreserve.gov/monetarypolicy.htm).
- USTR's product-exclusion notice extends 178 specified Section 301 exclusions
  through January 9, 2027 at 23:59 Eastern. Its scope is the specified products;
  this does not establish blanket tariff removal or the treatment of separate
  shipping measures. [Official notice](https://ustr.gov/sites/default/files/files/Issue_Areas/Enforcement/Section%20301/USTR%20FRN%20Extending%20Section%20301%20China%20FTT%20Exclusions%20to%20Jan%202027.pdf).
  The November 6 US–China readout discusses compliance with prior commitments
  on agricultural purchases and rare earths/critical minerals. It supplies no
  new tariff rate in that readout. [USTR readout](https://ustr.gov/about/policy-offices/press-office/press-releases/2026/november/readout-ambassador-greers-call-chinas-vice-premier-he-lifeng).
- NVIDIA's October 28 announcement schedules results for approximately November
  17 at 16:20 Eastern and the call at 17:00: November 18, 05:20 and 06:00 in
  Singapore. No earnings outcome is available from this scheduling notice.
  [Company announcement](https://nvidianews.nvidia.com/news/nvidia-sets-conference-call-for-third-quarter-financial-results-6928873).
- IMO's incident list is now labelled updated November 9, compared with the
  November 5 update seen in the earlier review. It lists damage to HUDA on
  November 7, 17 nautical miles from Oman, with no pollution reported. This
  is a newly observed source update here, not evidence it was known to our
  system on November 7. No attribution or future attack date is inferred.
  [IMO confirmed incidents](https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx).

Interpretation, not measured result: shipping disruptions and policy/earnings
announcements could matter through energy, costs, rates or index exposure.
These channels are hypotheses. We did not measure a causal price effect, fetch
held-out historical prices, or use this note to alter the frozen model prompt.

## Acquisition work and limits

Alpaca documents an inclusive start/end bar query and a pagination token that
must be checked. The new one-shot collector requests a single current session,
checks the token and rejects unexpected pagination rather than silently treating
one page as complete. A future paginated collector would need separate receipt
provenance for each page. [Alpaca bar reference](https://docs.alpaca.markets/us/reference/stockbars).

Today's authenticated check returned `market_closed`, zero captured bars, and
artifact hash `1b34b078acf76c777886dbc1011d04da25e292a31247a34a9606dfa0c5d1532e`.
It only exercised the broker-clock branch; open-market capture was tested with
synthetic fixtures, not claimed as a live integration result. The artifact stays
private under `.local/research/receipt_captures/`.

This acquisition format is not accepted by the frozen packet_context_v2 reader
and is not scheduled or connected to paper_ai_v1. The next research gate is a
versioned receipt-aware adapter and a separately declared prospective comparison.
Automated official-release ingestion also remains unfinished. Preserve the
November 9 rejected stale snapshot and causally excluded economic values. No
new action proposals, fills, backtest returns or evidence of 10% monthly were
produced today.
