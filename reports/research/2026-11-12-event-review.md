# November 12 review: PPI ahead, receipt-aware research still data-limited

Review recorded at **2026-11-12T08:19:16.495512+00:00**.
This is a current research review, not evidence that the paper model knew these
facts earlier. Existing first-observed timestamps remain unchanged. New facts in
this review become available only at the recorded review time; publication and
incident dates are not substituted for observation times. No running input,
watchlist, prompt, allocation or risk limit was changed.

## Upcoming primary-source dates

All nine entries in the frozen `configs/event_watchlist_2026.json` were checked
against the linked primary calendars. Dates/times still match; the old seed's
checked_at field was deliberately not relabeled as a newly deployed config.

| Release | US Eastern date and time | Singapore time |
|---|---|---|
| PPI, October | Nov 13, 08:30 | Nov 13, 21:30 |
| JOLTS, October | Dec 1, 10:00 | Dec 1, 23:00 |
| Employment Situation, November | Dec 4, 08:30 | Dec 4, 21:30 |
| FOMC meeting | Dec 8–9; release time not specified by seed | Verify release time separately |
| CPI, November | Dec 10, 08:30 | Dec 10, 21:30 |
| PPI, November | Dec 15, 08:30 | Dec 15, 21:30 |

The three past seed entries also match: Nov 3 JOLTS 10:00 ET, Nov 6 employment
08:30 ET, Nov 10 CPI 08:30 ET. Sources: [BLS November](https://www.bls.gov/schedule/2026/11_sched.htm),
[BLS December](https://www.bls.gov/schedule/2026/12_sched.htm),
[FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).
PPI has not been released at this review time; its value and surprise are unknown.
These calendars are not a complete list of market-moving risks.

The Fed lists **Nov 18** for minutes of the Oct 27–28 meeting. That is distinct
from a new policy decision. The Oct 28 statement held the target range at
3.75–4.00%. Sources: [upcoming Fed dates](https://www.federalreserve.gov/monetarypolicy.htm),
[Oct 28 statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm).

## Existing inflation evidence

The Nov 10 BLS release reports October seasonally adjusted headline CPI up 0.4%
month over month and core up 0.3%. Headline was up 0.6% in September. BLS cannot
publish many October annual changes because October 2025 indexes are missing;
this is not a zero annual inflation rate. No consensus estimate was captured,
so no numerical surprise is asserted. [BLS archived release](https://www.bls.gov/news.release/archives/cpi_11102026.htm).

Yesterday's private CPI evidence was revalidated today: one record, one saved
web rendering, matching source/review hashes and one currently eligible value.
Its original first-observed time is Nov 11 at 08:16:15.261411 UTC, not the Nov 10
publication time. It remains ineligible for earlier decision cutoffs. Source
integrity is a consistency check, not proof of extraction accuracy or authorship.

## Trade, earnings and geopolitical developments

The USTR press-release index still leads with its Nov 6 China call. Its readout
emphasizes implementation of agricultural and critical-mineral commitments;
it does not establish a new blanket tariff removal. [USTR readout](https://ustr.gov/about/policy-offices/press-office/press-releases/2026/november/readout-ambassador-greers-call-chinas-vice-premier-he-lifeng).
The separate [Section 301 notice](https://ustr.gov/sites/default/files/files/Issue_Areas/Enforcement/Section%20301/USTR%20FRN%20Extending%20Section%20301%20China%20FTT%20Exclusions%20to%20Jan%202027.pdf)
extends 178 specified exclusions through Jan 9, 2027 at 23:59 ET. Product scope
matters; this does not determine unrelated tariffs or maritime measures.

NVIDIA's Oct 28 announcement still schedules Nov 17 results at approximately
16:20 ET and its call at 17:00 ET (Nov 18 at 05:20 and 06:00 Singapore).
Those are scheduled times, not actual earnings or guidance. [Company notice](https://nvidianews.nvidia.com/news/nvidia-sets-conference-call-for-third-quarter-financial-results-6928873).
A Nov 10 company statement says independent directors retained external counsel
for an investigation. That establishes the company's announcement, not the truth
of allegations circulating in secondary headlines or the investigation outcome.
[Independent board statement](https://nvidianews.nvidia.com/news/statement-from-the-independent-members-of-the-nvidia-board).

The IMO page now reports **134 confirmed incidents as of Nov 11**, versus 133
as of Nov 10 in yesterday's review, with **25 confirmed seafarer fatalities**.
It lists TARIF under Nov 7, damaged with no pollution. The incident date, the
page's reporting date and today's observation are distinct; this is not evidence
of a new attack today. [IMO confirmed-incident list](https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx).
Potential implications for energy, shipping costs and equity risk are research
hypotheses; no direction, magnitude or causal SPY return is inferred.

## Local news and candidate construction

The 08:06 UTC news audit inspected 10,251 valid revisions for 10,212 articles;
36 articles had multiple revisions, with no integrity errors. Largest recorded
update-to-observation delay was 898.65 seconds. This does not certify feed
completeness or instantaneous receipt. A subsequent keyword review found 64
stored revisions observed since Nov 11 at 08:00 UTC concerning inflation, Fed,
trade, China, Hormuz or NVIDIA. Secondary allegations and commentary remain
unverified; raw licensed headlines and article identifiers stay local.

The newly registered offline packet_context_v3 was audited at 08:17:15 UTC.
All 29 baseline packets assembled (maximum 3,304 bytes). Both augmented arms
rejected all 29 because no capture existed before their cutoffs. The only
receipt_capture_v1 artifact is a Nov 10 closed-market observation. Old v2
snapshots cannot be relabeled as receipts. Source availability, not a new
strategy result, is the blocker. No model call, price download, order, backtest
or holdout consumption occurred in this audit. Its release arm never reached
selection because history failed; the CPI evidence check above was separate.

Next evidence needed: prospectively collect current-session receipts before
candidate cutoffs during reliable market attendance. A later model comparison
still needs a registered start and bounded request budget. Do not backfill old
observations, clear monitoring blocks or force orders to create a result.
