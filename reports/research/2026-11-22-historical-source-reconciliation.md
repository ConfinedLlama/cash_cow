# Historical source reconciliation - November 22, 2026

## Repeat requests preserve yesterday's findings

Eight bounded, authenticated SPY SIP minute requests repeated each gap session's regular-hours interval on November 22.
Each response had one complete page; timestamp and OHLCV values matched the original cached regular-session rows exactly.
A separate one-page daily request over the unchanged 2016-2024 interval also matched all 2,264 original timestamp/OHLCV rows exactly.
These are repeat observations from the same provider, not independent confirmation of truth.
All responses, request parameters where recorded and receipt timestamps remain in ignored local evidence; no original cache was overwritten.
No account or order endpoint was used for this historical investigation.

The proposed explanation that a fresh bounded request would recover the missing minutes was not supported.
The original total remains 104 absent regular-session minutes across eight dates, with twenty daily-close discrepancies above the fixed 10 bp threshold.
The 2025+ historical holdout, frozen v4 configuration, daily-close threshold and original failed attempt remain unchanged.
No v4 strategy was evaluated.

## Exact halt interval comparison

The [exchanges' March 2020 working-group report](https://www.nyse.com/publicdocs/nyse/markets/nyse/Report_of_the_Market-Wide_Circuit_Breaker_Working_Group.pdf), submitted March 31, 2021, supplies the following Eastern Time trigger and reopening-auction times on printed pages 4-5.
Today's source review occurred after the historical period and is diagnostic metadata, not information supplied to old strategy decisions.

| Date | Published halt start | Published reopening start | Missing minute interval, end exclusive | Count |
|---|---|---|---|---:|
| 2020-03-09 | 09:34:13 | 09:49:13 | 09:35-09:49 | 14 |
| 2020-03-12 | 09:35:44 | 09:50:44 | 09:36-09:50 | 14 |
| 2020-03-16 | 09:30:01 | 09:45:01 | 09:31-09:45 | 14 |
| 2020-03-18 | 12:56:17 | 13:11:17 | 12:57-13:11 | 14 |

All 56 absent full-minute intervals lie within the published halts.
Partial minutes containing the trigger or reopening can still have trades, so a fifteen-minute halt need not produce fifteen absent minute bars.
This is interval correspondence, not a complete symbol-specific replay of reopening execution.
No halt exemption, forward-filled bar or permission to execute during a halt was added to the backtester.

The remaining 48 missing minutes are not explained by that source:

| Date | Missing intervals, New York time, end exclusive | Count |
|---|---|---:|
| 2016-02-02 | 11:19-11:28 | 9 |
| 2019-08-12 | 15:29-15:31; 15:32-16:00 | 30 |
| 2021-05-05 | 11:27-11:32 | 5 |
| 2023-06-05 | 09:52-09:56 | 4 |

The August 2019 gap reaches the close, so deleting those missing minutes could create a false impression that an end-of-session liquidation was possible.
A different independently timestamped source or documented outage/halt explanation is still needed.
The source records were not repaired by inference.

## Daily-close definitions remain unresolved

[Alpaca's aggregation documentation](https://docs.alpaca.markets/us/docs/market-data-faq) states that minute and daily bars aggregate trades according to tape, trade-condition and bar-type rules.
It explicitly distinguishes some minute and daily eligibility rules and identifies market-center official-close messages as not updating its bar fields.
That supports investigating definitions; it does not establish the cause of these twenty discrepancies or prove either provider correct.

A fixed descriptive comparison examined the same twenty failing dates against three cached minute endpoints: 15:59, 16:00 and the last available minute.
Every endpoint was available on all twenty dates.
Against Yahoo Close, absolute differences still exceeded 10 bp on seven, twelve and nineteen dates respectively.
The 15:59 comparison's maximum absolute difference was 59.779914 bp, so merely substituting that endpoint would not pass the existing check either.
These diagnostics use `(minute close / Yahoo Close - 1) * 10000`; the original frozen check uses `(Yahoo Close / Alpaca daily close - 1) * 10000` and retains its 279.344906 bp maximum.
The reversed denominators must not be confused.
No replacement basis was selected, and no strategy outcome was viewed to choose one.

## Diagnostic improvement and validation

The existing public diagnostic could return diagnostic_checks_passed for a complete synthetic minute grid with an extra 09:30:30 timestamp.
This was reproduced before editing; off-grid timestamps now fail with Invalid minute timestamps.
The diagnostic also emits contiguous missing intervals with timezone offsets and exclusive ends, preserving separate runs and holiday boundaries.
Counts and validation thresholds are unchanged.
The frozen trading engine and running paper process were not edited or restarted.

Six focused tests passed, including interval reconstruction across a holiday/early close and off-grid rejection.
An initial interval test failed because ISO timestamps deserialize to a fixed-offset timezone rather than the named New York timezone; normalizing the test's reconstruction to the source timezone fixed that assertion without changing output semantics.
The full suite passed 463 tests in 15.62 seconds.
The real-cache diagnostic still exits 2 with the original issues, as intended.
Original cache hashes were checked before and after investigation.

## Retained evidence

Minute source SHA-256: 2a4b87ac1c745533cef13e14d76bf639e3e8148e2a29478540706a1dee41be6e.
Daily source SHA-256: c164b66481de6ef01294f0eef3e059460cebc635cc060a2335a38a876c906d32.
Yahoo cache SHA-256: 67371e45a62f59f0dd6ad6c10d220ad5365c8dc6c612003240968f3f2acd26e4.

| Repeat request | Private response SHA-256 |
|---|---|
| 2016-02-02 minutes | 4683f3b6fb8bf5800337c86986ca62e2d4cf7a9bcfee81c234f38b2141e8f0fa |
| 2019-08-12 minutes | e4fe85aa714abe3bd7d7b07fb1f128e8f69d3fbed4bb7c79d4739b7d9473ae69 |
| 2020-03-09 minutes | 9eb708a231749a5167107cd8888b5a4da498df702d7d2f91a87d1b9b3100337b |
| 2020-03-12 minutes | 7de63a1ab3ca91807225614b2b4350bba73e045605918813fe89ed2409341af7 |
| 2020-03-16 minutes | 7334be9fb44a2e5fb83e8c934e263ee00e6632e72ca8dec94a816b5058f4aede |
| 2020-03-18 minutes | 0781c48ae5dfd53938d23c2bcbeedeacc0ec398bbbb7ca99620dff498febf523 |
| 2021-05-05 minutes | 7a413e668ccfff73796985679d4e9332c7c50314b8705e8a5a6f359fbb0678ed |
| 2023-06-05 minutes | e653f62c2d429cdd248acd195472afcafed039f28c30dc871e0e6f2b9349e2c2 |
| 2016-2024 daily | 958f1d82dc31bb9902bc0aa60c3435ab1b99aebb14b24500c6833b768127290f |

Next work must resolve the four unexplained gap dates and independent close basis, then separately register and test any halt-aware execution and local-date-boundary correction before running v4.
Neither relaxing the threshold nor removing difficult dates is justified by today's evidence.
