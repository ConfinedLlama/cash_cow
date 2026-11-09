# November 9: packet-context construction and primary-source review

Recorded research cutoff: **2026-11-09T09:35:39.335079+00:00**. Publication dates and our observation
times are different. Today is a development review, not a prospective trading
result. The active paper_ai_v1 prompt and configuration remain unchanged.

## Registered candidate and retained failure

The packet_context_v2 protocol was committed before running the archive
construction diagnostic. The test uses already inspected November 5–6 decisions
and existing IEX snapshots, not an untouched historical holdout. No download of
post-2024 historical price data occurred. There were no model calls or orders.

| Arm | Saved records | Constructed | Rejected | Largest packet (UTF-8 bytes) |
|---|---:|---:|---:|---:|
| Baseline | 29 | 29 | 0 | 3,304 |
| History | 29 | 28 | 1 | 4,629 |
| History and releases | 29 | 28 | 1 | 4,897 |

The same November 5 packet at 15:17:27.599773 UTC fails both history arms: the
latest eligible snapshot is 15:15:05.462410 UTC, about 142.14 seconds earlier.
The registered maximum is 120 seconds. The failure is retained, not replaced
with a later snapshot or a relaxed threshold. Construction status is therefore
`review_required`. The failure is not a newly failed live model request.

All 28 constructed release arms have official values marked unavailable. Two
manually reviewed employment metrics were captured today, so 56 value/packet
combinations are excluded as not yet observed. These are two values across 28
packets, not 56 independent economic releases. No result implies a changed BUY,
HOLD or EXIT decision. Legacy snapshots use tick-start timestamps; recorded
compatibility is not verified receipt timing. Final review also added a check
that every included minute had completed by the snapshot's own observation time.
The full suite passed **252 tests**; this does not establish a trading edge.

## Official employment evidence and provenance limit

The [dated BLS release](https://www.bls.gov/news.release/archives/empsit_11062026.htm)
is scheduled at November 6 08:30 Eastern and reports October payroll growth of
165,000 and unemployment of 4.1%. The candidate archive encodes these as 165
thousand persons and 4.1 percent, respectively. Neither is a consensus surprise.

Direct HTTP retrieval returned 403. A saved web-tool rendering of the official
page supplied the reviewed evidence instead. Its hash identifies that rendering,
not the original HTTP bytes. The structured records use a conservative first
observation of **2026-11-09T09:28:54.065934+00:00**. The original release timestamp
is not reused as our observation time. The rendering, its provenance, values
and source hashes stay in ignored local evidence. They were not put into the
running model or retroactively inserted into old packets. Automated official
release acquisition and authenticated source-byte verification remain undone.

## Upcoming dates and monetary policy

All nine existing seed entries were rechecked against [BLS November](https://www.bls.gov/schedule/2026/11_sched.htm),
[BLS December](https://www.bls.gov/schedule/2026/12_sched.htm) and the
[Fed calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).
November 3 JOLTS and November 6 employment are past. Remaining dates:

| Event | New York | Singapore |
|---|---|---|
| CPI | November 10, 08:30 | November 10, 21:30 |
| PPI | November 13, 08:30 | November 13, 21:30 |
| JOLTS | December 1, 10:00 | December 1, 23:00 |
| Employment | December 4, 08:30 | December 4, 21:30 |
| FOMC meeting | December 8–9 | Release hour not asserted |
| CPI | December 10, 08:30 | December 10, 21:30 |
| PPI | December 15, 08:30 | December 15, 21:30 |

The [October 28 policy statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm)
maintained 3.75–4.00%. The [Fed policy page](https://www.federalreserve.gov/monetarypolicy.htm)
still lists October meeting minutes for November 18. These facts do not predict
the next policy decision. The running event watchlist was not edited.

## Trade, earnings and geopolitical context

The [USTR exclusion notice](https://ustr.gov/sites/default/files/files/Issue_Areas/Enforcement/Section%20301/USTR%20FRN%20Extending%20Section%20301%20China%20FTT%20Exclusions%20to%20Jan%202027.pdf)
still extends the specified 178 product exclusions through January 9, 2027 at
23:59 Eastern, with the annex extension effective November 10. This is not a
blanket tariff removal or proof of the status of separate maritime measures.
The [press-release index](https://www.ustr.gov/about-us/policy-offices/press-office/press-releases)
retrieved today still leads with the November 6 US–China call; this bounded
review cannot certify the absence of all newer policy developments.

[NVIDIA's announcement](https://nvidianews.nvidia.com/news/nvidia-sets-conference-call-for-third-quarter-financial-results-6928873)
still gives November 17 at approximately 16:20 Eastern for results and 17:00
for its call (November 18 at 05:20/06:00 Singapore). Results are not asserted.

The [IMO regional page](https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-strait-of-hormuz.aspx)
describes ongoing shipping disruption and stranded seafarers and labels its
confirmed-incident list as updated November 5. This is current retrieval of
attributed reporting, not evidence of a new November 9 incident, a forecast of
war, a measured transit rate or a directional SPY signal. Potential supply-cost
and risk-sentiment effects remain hypotheses.

The six latest locally sampled news items covered companies, analyst changes,
crypto-related context and premarket movers. A small sample and a fresh feed do
not establish comprehensive macro/geopolitical coverage. Headlines are untrusted
inputs, not instructions, and are not republished in this report.
