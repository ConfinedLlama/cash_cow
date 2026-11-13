# November 13 research: event timing and observed model inputs

Review recorded at **2026-11-13T08:13:02.534763+00:00**.
This review is available at the timestamp above, not retrospectively at a source's
publication or incident date. Existing local first-observed news revisions and
prior reports remain immutable. The running strategy and watchlist were not changed.

## Verified calendar and primary-source context

All nine seed entries were rechecked. The [BLS November calendar](https://www.bls.gov/schedule/2026/11_sched.htm)
still shows JOLTS Nov 3 at 10:00 ET, employment Nov 6 at 08:30 ET, CPI Nov 10
at 08:30 ET, and **PPI today Nov 13 at 08:30 ET / 21:30 Singapore**. At this
review's cutoff PPI is still ahead; no value, consensus surprise or market
reaction is asserted. It occurs one hour before today's regular US equity open.

The [BLS December calendar](https://www.bls.gov/schedule/2026/12_sched.htm)
confirms JOLTS Dec 1 at 10:00 ET / 23:00 Singapore, employment Dec 4, CPI Dec 10
and PPI Dec 15, all three at 08:30 ET / 21:30 Singapore. The [Fed calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
confirms Dec 8–9 for the FOMC meeting; the seed does not specify a release hour.
The [Fed policy page](https://www.federalreserve.gov/monetarypolicy.htm) lists
Nov 18 for minutes of Oct 27–28 and Dec 30 for minutes of Dec 8–9. Minutes are
not new policy decisions. The [Oct 28 statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm)
held the target range at 3.75–4.00%; no new rate action is inferred.

NVIDIA's **Nov 12 company announcement** states that Jensen Huang resigned as
president, CEO and director effective immediately, Colette Kress became interim
CEO while continuing as CFO, and Harvey C. Jones became board chair. It also
reaffirms Nov 17 results around 13:20 Pacific / 16:20 Eastern, followed by the
14:00 Pacific / 17:00 Eastern call: Nov 18 at 05:20 / 06:00 Singapore.
[Company announcement](https://nvidianews.nvidia.com/news/nvidia-announces-ceo-transition).
This is a new primary-source confirmation in today's review, distinct from
previous allegations and the Nov 10 investigation announcement. It establishes
what the company announced; it does not substantiate third-party allegations or
predict the earnings outcome. Possible broad-market spillover is a hypothesis,
not a measured SPY effect or automatic long/short signal.

The [USTR index](https://ustr.gov/about-us/policy-offices/press-office/press-releases)
still leads with the Nov 6 China call; no newer item is shown in that index.
The separate [Section 301 notice](https://ustr.gov/sites/default/files/files/Issue_Areas/Enforcement/Section%20301/USTR%20FRN%20Extending%20Section%20301%20China%20FTT%20Exclusions%20to%20Jan%202027.pdf)
extends 178 specified product exclusions through Jan 9, 2027 at 23:59 Eastern.
Do not generalize that to all tariffs, chip restrictions or maritime measures.
The [IMO incident list](https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx)
remains at 134 confirmed incidents as of Nov 11 and 25 confirmed seafarer
fatalities. Its reporting date is not today's incident count, and unchanged
publication does not establish absence of new events. Neither wars nor policy
announcements are fully predictable from a fixed date calendar.

## What the local model actually observed

The 08:05 UTC audit found 12,214 valid saved news revisions for 12,169 articles,
including 42 articles with multiple revisions; no stored-hash/timestamp errors.
The maximum recorded vendor-update-to-observation delay was 899.38 seconds.
The collector was fresh but its latest bounded window was truncated. Freshness
and integrity therefore do not establish comprehensive or immediate coverage.

A subsequent keyword review through 08:11:12 UTC found 81 stored revisions
observed since Nov 12 at 08:00 UTC relating to inflation/PPI, Fed, trade, China,
Hormuz or NVIDIA. Secondary reports, opinions and allegations remain unverified.
Raw licensed headlines and source identifiers remain local.

The local feed first stored a headline reporting NVIDIA's transition at
**Nov 12 13:54:22.381525 UTC** (vendor update 13:49:37 UTC). An earlier
11:43:37 UTC observation was a report about possible succession, not the same
confirmation. Today's direct company-source review must not replace either
observation time. The six saved decision packets at 15:05–15:30 UTC each had
eight headlines; two packets contained NVIDIA/Huang/Kress headline matches
(two matches at 15:10, one at 15:15). Keyword inclusion is not proof that the
model used the transition fact or that a headline caused its decision.

All six had empty same-day event lists. The active selector includes only events
whose date range contains that session date; it did not present tomorrow's PPI
as a forward-looking event on Thursday. This is a documented input limitation,
not evidence of a missed profitable trade. Future changes to event lookahead
need a separate frozen candidate and comparison, not a mid-trial patch.

All six unique responses were HOLD. Their explanations cited insufficient
momentum/history or broad-market evidence, alongside range/VWAP/spread context.
These are model explanations, not calibrated probabilities or causal proofs.
Later inactivity is separately explained by operational blocks: the first logged
transport error was 15:36:56 UTC, the first unavailable-quote entry block was
15:40:09 UTC, and monitoring gaps followed. macOS recorded clamshell sleep at
15:32:02 UTC. The sequence supports an operating failure after the six decisions;
it does not prove the physical cause of every transport error.

## Candidate evidence remains unavailable

The unchanged packet_context_v3 construction audit now includes 35 decisions.
All baseline packets assembled; both history arms rejected all 35. For 29 there
was no earlier receipt capture. For the six newer decisions the latest prior
capture was November 10's closed-market record, rejected as unusable. No
prospective price receipts were captured automatically; the existing collector
is one-shot. Old tick-start bars cannot be relabeled as response receipts.

No model comparison, new price download, backtest or holdout retrieval occurred.
The original losing trials remain intact. Next steps are reliable full-session
attendance and prospective receipts before candidate cutoffs, followed by a
separately registered model comparison with fixed start, budget, costs and failure
retention. More model calls or forced trades do not establish an edge.
