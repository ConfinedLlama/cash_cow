# Close-definition investigation - November 25, 2026

## Question and result

Can the historical API/Yahoo daily-close mismatch be explained and repaired by a single alternative minute-bar endpoint?
Today's exploratory comparison does not support that repair.
Seven of the original 20 discrepant dates still exceed 10 bp when using the exact final regular-session minute, and four other dates newly exceed that threshold.
This is data diagnosis after observing discrepancies, not a preregistered performance experiment or evidence for selecting a more favorable source.

The [new offline close audit](../../docs/HISTORICAL_CLOSE_AUDIT.md) compares all 2,264 scheduled 2016-2024 sessions with calendar-aware closing boundaries.
It retains shortened sessions and daylight-saving changes and does not substitute a nearby minute when the exact one is missing.
Differences are `(Yahoo reference / comparison - 1) * 10000`, not trading returns.

| Comparison price | Available sessions | Missing endpoints | Absolute discrepancy over 10 bp | Maximum absolute discrepancy, bp |
|---|---:|---:|---:|---:|
| Original Alpaca daily close | 2,264 | 0 | 20 | 279.344906 |
| Exact final regular-session minute close | 2,263 | 1 | 11 | 59.424673 |
| Minute close beginning at the scheduled close | 2,263 | 1 | 186 | 73.193736 |
| Last observed minute close on the New York date | 2,264 | 0 | 1,067 | 412.290582 |

A lower discrepancy count does not validate a replacement price definition.
The closing-boundary minute may contain auction and post-session trades; its close is not an official auction record.
The last observed minute is not necessarily a regular-session or official close.
No comparison identifies which underlying provider is correct.
Missing-minute evidence and original discrepancy flags remain intact.

## Source semantics and limits

[Alpaca documents](https://docs.alpaca.markets/us/docs/market-data-faq) that minute and daily bars aggregate trades using timestamp intervals and trade-condition eligibility rules, with some rules differing between bar types.
Consequently, assuming the daily close must equal the final minute-bar close is not a verified invariant.
The [SEC's closing-price explanation](https://www.investor.gov/introduction-investing/investing-basics/glossary/closing-price) distinguishes primary-market, consolidated and after-hours quotation conventions.
These primary sources were reviewed November 25; they motivate further investigation but do not establish the cause of the historical records in this cache.
No raw trade-condition reconstruction or independent official-closing-price dataset was obtained today.

## Reproducibility and unchanged gate

The actual-cache command was `.venv/bin/python -m cash_cow.intraday.close_audit`.
Its retained private output is `.local/daily/2026-11-25-evidence/close-audit.json`, SHA-256 `42375951f22636eca709cebbf941b3b53c23e11742e1d8c1ea2bd990f7f8a3be`.
It returned exit 2 with the original missing-minute, close-discrepancy and local-date-boundary issues.
Source hashes were verified before and after analysis:

- Minute cache: `2a4b87ac1c745533cef13e14d76bf639e3e8148e2a29478540706a1dee41be6e`.
- Daily cache: `c164b66481de6ef01294f0eef3e059460cebc635cc060a2335a38a876c906d32`.
- Yahoo reference: `67371e45a62f59f0dd6ad6c10d220ad5365c8dc6c612003240968f3f2acd26e4`.

Eight synthetic tests cover early closes, daylight-saving boundaries, exact missing endpoints, unchanged inputs, duplicates, invalid numeric/timestamp fields, missing daily sessions and the historical holdout boundary.
The full suite passed 493 tests in 17.16 seconds.
The frozen multi-year validate-only command was also rerun and still failed its API/Yahoo 10 bp check.
No strategy simulation completed and no prices, costs, thresholds, source manifests or trial settings were changed.
The 44 base and 440 sensitivity runs remain blocked; the protected 2025+ historical holdout remains untouched.

Separately, the corrected trade-response audit now rejects future observation timestamps and suppresses private parser text at the CLI boundary.
Both retained November 24 trade-audit results remain exactly unchanged under the corrected implementation.
Their empty responses still do not prove no trading or authorize filling any missing bar.

Next obtain independently documented close records or transaction eligibility evidence before proposing a versioned treatment for the frozen historical pipeline.
Do not tune data selection to pass the validator or to approach the monthly return target.
