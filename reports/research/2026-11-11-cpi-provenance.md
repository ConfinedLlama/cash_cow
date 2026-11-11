# November 11 research review: CPI evidence and publication lags

Review recorded at 2026-11-11T08:18:16.653459+00:00. This timestamp records today's review, not when
an event happened or when an earlier model knew it. No trading rule or runtime
calendar was changed. Source text and news remain untrusted input.

## Observed CPI outcome and limits

The dated BLS release published November 10 at 08:30 Eastern reports October
CPI-U up **0.4% month-on-month, seasonally adjusted**, following 0.6% in September.
Excluding food and energy, the monthly change was 0.3%. The release says that
missing October 2025 observations prevent publication of many October 2026
12-month changes. Those missing annual rates must remain unavailable; do not
infer them from a single monthly change. [Official BLS release](https://www.bls.gov/news.release/archives/cpi_11102026.htm).

The headline monthly value was manually entered into a separate private research
record, with structured first observation **2026-11-11T08:16:15.261411+00:00**.
Its saved evidence is a web-tool rendering captured at 08:14:03.025947 UTC today,
not original HTTP response bytes. Capture SHA-256:
`783c9eb1f7297767436aa71ec2bc2066972d43a18629fa599f36a032b9168adb`.
The record's period is 2026-10, unit percent and value 0.4; it is not 0.004 percent,
an annual rate, a core measure or a consensus surprise. Core CPI is discussed
above but was not added to the frozen metric allowlist.

The new source-provenance audit passed for the exact saved bytes and reviewed
record. At today's cutoff, one value is eligible. At November 10 20:00 UTC,
**zero values are eligible and one is excluded as not yet observed**. This is
an input-availability diagnostic, not a backtest. No historical model packet was
rewritten. Hash consistency does not independently prove extraction accuracy;
the cited release was read manually. No consensus series was acquired, so the
sign/magnitude of a surprise and a causal market response remain unmeasured.

## Primary-source calendar check

All nine seed entries were rechecked. The three elapsed events remain JOLTS
November 3 at 10:00 Eastern, employment November 6 at 08:30 and CPI November 10
at 08:30. Remaining entries:

| Event | Eastern date/time | Singapore date/time |
|---|---|---|
| PPI | Nov 13, 08:30 | Nov 13, 21:30 |
| JOLTS | Dec 1, 10:00 | Dec 1, 23:00 |
| Employment | Dec 4, 08:30 | Dec 4, 21:30 |
| FOMC meeting | Dec 8–9; release time not supplied in seed | Reverify release time separately |
| CPI | Dec 10, 08:30 | Dec 10, 21:30 |
| PPI | Dec 15, 08:30 | Dec 15, 21:30 |

Sources: [BLS November](https://www.bls.gov/schedule/2026/11_sched.htm),
[BLS December](https://www.bls.gov/schedule/2026/12_sched.htm),
[Fed calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).
Although Veterans Day appears on the BLS calendar, today's Alpaca equity clock
and exchange-calendar response identify a regular November 11 session. A
statistical-agency holiday does not establish equity-market closure.

The October 28 Fed statement maintained the target range at 3.75–4.00%; the
policy page lists November 18 minutes and the December 8–9 meeting. These are
prior policy context and upcoming dates, not a new decision today.
[Statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm),
[upcoming dates](https://www.federalreserve.gov/monetarypolicy.htm).

## Trade, earnings and geopolitical observations

- USTR's specified 178 Section 301 product exclusions remain extended through
  January 9, 2027, 23:59 Eastern. This says nothing about all other tariffs or
  separate shipping measures. [USTR notice](https://ustr.gov/sites/default/files/files/Issue_Areas/Enforcement/Section%20301/USTR%20FRN%20Extending%20Section%20301%20China%20FTT%20Exclusions%20to%20Jan%202027.pdf).
  The release index still shows its November 6 China call as the latest listed
  item; absence of a newer item there does not prove no other policy action.
  [Index](https://ustr.gov/about-us/policy-offices/press-office/press-releases).
- NVIDIA's scheduled results remain approximately November 17 at 16:20 Eastern,
  followed by its 17:00 call: November 18 at 05:20/06:00 Singapore. No earnings
  result is inferred. [Company notice](https://nvidianews.nvidia.com/news/nvidia-sets-conference-call-for-third-quarter-financial-results-6928873).
- IMO's list is now marked November 10, with 133 confirmed incidents compared
  with the 131 in the November 9-labelled list viewed yesterday. Entries include
  NAVIG8 MACALLISTER dated November 7 and GRIT dated November 3, both reporting
  damage without pollution. These are newly observed entries here, not attacks
  dated November 10 or knowledge available to our earlier decisions. Attribution,
  future incidents and price effects are not inferred. [IMO list](https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx).

A local keyword review found 25 revisions first observed November 10–11 matching
CPI, consumer prices, tariff, Fed, NVIDIA or Hormuz terms. The latest ten include
non-US inflation and secondary-source corporate/policy reports. They were checked
with publication/update/first-observed timestamps, not promoted to verified US
CPI data or copied into the public repository. Keyword matches are not complete
market coverage. Corporate allegations require primary corroboration and were
not adopted as facts or trading instructions.

Interpretation only: inflation, policy expectations, supply costs and large-index
constituents may interact. We have no verified paired trade/benchmark sample with
which to estimate those effects. The paper trial is still operationally incomplete.
Next gates are reliable attendance, receipt-aware candidate inputs, fixed model
comparison budget and prospective evaluation with declared costs and preserved
failures. This review produces no new model request, fill, return or 10%-monthly
claim and does not access the historical price holdout.
