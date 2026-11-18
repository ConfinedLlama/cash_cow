# November 18 event review

Reviewed by 2026-11-18T08:04:13.051520+00:00. This records this review's observation cutoff, not the
first public release time or evidence that a running model received the news.
The runtime prompt, calendar and strategy remain frozen.

## Calendar reverified

| Event | Source schedule | Singapore time |
|---|---|---|
| October FOMC minutes | November 18 14:00 Eastern | November 19 03:00 |
| BLS JOLTS | December 1 10:00 Eastern | December 1 23:00 |
| BLS Employment Situation | December 4 08:30 Eastern | December 4 21:30 |
| FOMC meeting | December 8–9 | Release hour not verified here |
| BLS CPI | December 10 08:30 Eastern | December 10 21:30 |
| BLS PPI | December 15 08:30 Eastern | December 15 21:30 |

The [Fed November calendar](https://www.federalreserve.gov/newsevents/2026-November.htm)
and [policy page](https://www.federalreserve.gov/monetarypolicy.htm) still list
the minutes as upcoming at this cutoff. Their contents and reaction cannot
be inferred in advance. Upcoming BLS entries in the frozen
`configs/event_watchlist_2026.json` agree with the
[December schedule](https://www.bls.gov/schedule/2026/12_sched.htm).
Timezone conversions were asserted using ZoneInfo. These dates are selected
context, not a comprehensive risk calendar or a new entry filter.

## Earnings, trade and shipping

[NVIDIA's November 17 release](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Third-Quarter-Fiscal-2027/default.aspx)
reports Q3 FY2027 revenue of USD 115.8 billion, up 103% year over year, and
GAAP diluted EPS of USD 2.70. Its Q4 outlook is USD 130 billion revenue,
plus or minus 3%, with no assumed Data Center compute revenue from China;
the quarter includes an extra week. Expected gross margins are 71–72%.
Reported results and management forecasts are different evidence classes.
No consensus estimate was verified, so no earnings beat/miss is asserted.
These results are after the November 17 regular session and cannot be used
retroactively to justify an intraday decision from that session. A next-day
price direction is not established by the growth figures.

The [USTR release index](https://ustr.gov/about-us/policy-offices/press-office/press-releases)
still lists November 16 as its latest entry in this review. The
[linked tariff-policy letter](https://ustr.gov/about/policy-offices/press-office/press-releases/2026/november/ambassador-greer-pens-letter-editor-wall-street-journal-how-tariffs-are-advancing-americans-long)
is an administration argument about economic benefits, not a new tariff-rate
instrument. No claim of globally unchanged trade policy follows from one
unchanged index. The NVIDIA China assumption is company guidance, not by
itself a newly enacted export-control rule.

The [IMO register](https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx)
now records 138 confirmed incidents as at November 17 and 25 fatalities,
versus 137 as at November 16 in yesterday's review. The newly listed top
entry is AL DHANNAH in the Arabian Gulf on November 15, damaged with no
pollution reported. This is an updated register observed today, not an
incident dated today. First market awareness and subsequent unreported
incidents are unknown. It provides shipping-risk context, not a calibrated
SPY return forecast.

## Local news chronology

At 07:59:43 UTC, the private archive passed integrity checks for 15,118 valid
revisions, 15,060 distinct articles and 53 articles with multiple revisions.
Last first-observed time was 07:06:44.528231 UTC. A currently fresh collector
or valid hashes do not establish complete overnight coverage.

| Vendor item, paraphrased | Published UTC November 17 | First observed locally UTC |
|---|---|---|
| Report of a new NVIDIA security/export oversight committee | 11:31:18 | 11:36:45.277341 |
| Report of an NVIDIA export-compliance warning to buyers | 12:32:23 | 12:37:00.452779 |
| Dell/NVIDIA AI infrastructure announcement | 14:31:22 | 14:32:32.961219 |

Selected metadata has matching publication/update times; first observation
is the collector's persisted time, not an independently measured HTTP receipt.
These three vendor items were not separately primary-confirmed in this
review and remain attributed reports. The company earnings release above was
verified independently during today's review. It is not claimed to have been
present in a saved model packet. A narrow headline filter returned eight
new NVIDIA/FOMC/tariff/Hormuz matches; it is neither exhaustive nor a validated
classifier, and raw licensed text remains private.

No November 17 model proposal was produced, and no new decisions have been
recorded since November 12. Later news cannot explain those earlier HOLDs.
No news or revised metadata was inserted into old packets. Any new
news-informed strategy requires a separate frozen candidate with receipt
cutoffs, revision rules, costs and evaluation criteria declared in advance.
