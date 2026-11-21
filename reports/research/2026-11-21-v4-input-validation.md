# V4 historical inputs: authenticated download, validation blocked

The first authenticated full SIP request completed on November 21, 2026.
It retrieved 1,774,344 SPY minute rows over 178 pages and 2,264 daily rows over one page, using raw prices and the fixed UTC interval from 2016-01-01 through an exclusive 2025-01-01 boundary.
The minute count includes extended-hours rows, not 1,774,344 regular-session observations.
Both compressed caches and their download manifests are preserved locally and excluded from Git.
Credentials and raw price records are not published.

[Alpaca's documentation](https://docs.alpaca.markets/us/docs/market-data-faq) allows historical SIP queries without a subscription when the end is at least fifteen minutes old.
Today's successful download verifies this account's access for these requests; it does not verify real-time SIP entitlement.

## Reproduction and preserved failure

The end-user preparation command was run unchanged before diagnostics were added:

```sh
.venv/bin/python -m cash_cow.intraday.multiyear --fetch --validate-only
```

It exited 1 with `API/Yahoo daily prices differ by more than 10 bp; investigate before running`.
No data/manifest_v4.json, completed v4 run or v4 result pointer was generated.
No v4 strategy simulation ran and there are no new v4 monthly returns to report.
The existing 192 v3 and 44 v3b pilot runs remain separate, unchanged historical evidence.

The frozen v4 configuration hash is `7ba220afc43792725e5ea215063cda9bc59073e54844838539efd14d42ff2992`.
It still declares 2016 warm-up, 2017-2020 earlier diagnostics and 2021-2024 later evaluation, eight rules plus three benchmarks, two account models, 44 base cases and 440 full sensitivity cases.
Costs remain 2 bp one-way slippage, max(USD 0.40, USD 0.0035/share), one minute of additional latency, whole shares and 95% allocation in the base case.
The hypothetical margin model also includes its declared financing proxy.
No parameters, costs, validation threshold, running paper strategy or holdout boundary changed.
2025 onward historical prices remain unrequested; the separate registered prospective scorecard is unrelated to this dataset.

## Offline diagnostic findings

The new `cash_cow.intraday.input_audit` command checks cached hashes and emits aggregate diagnostics without network calls or file writes.
It reports all calendar gaps, missing daily/reference dates, close discrepancies and exchange-local boundary spillover instead of stopping at the first discrepancy.
It is not a replacement for the frozen OHLC/execution validator and cannot authorize a backtest.

```sh
.venv/bin/python -m cash_cow.intraday.input_audit
```

The command exits 2 for the current review-required inputs.
Across 2,264 expected sessions, there are 879,720 scheduled regular minutes and 104 absent minute timestamps over eight dates:

| Session | Missing regular minutes |
|---|---:|
| 2016-02-02 | 9 |
| 2019-08-12 | 30 |
| 2020-03-09 | 14 |
| 2020-03-12 | 14 |
| 2020-03-16 | 14 |
| 2020-03-18 | 14 |
| 2021-05-05 | 5 |
| 2023-06-05 | 4 |

The [NYSE's historical discussion](https://www.nyse.com/article/circuit-breakers-are-doing-their-job-but-dont-close-the-markets) records market-wide halts on March 9, 12, 16 and 18 during the 2020 selloff.
Those dates overlap four of the gap dates; this supports investigating halts rather than assuming every missing bar is a provider defect.
Exact interval matching and a halt-aware execution protocol have not been validated here.
No missing minute was forward-filled, no crisis date was removed, and no imaginary fill during a halt was allowed.
The other four gap dates remain unexplained by this check.

Twenty daily closes differ from the existing Yahoo cache by more than 10 bp, with maximum absolute difference 279.344906 bp on March 12, 2020.
Daily dates are unique and ordered, cover January 4, 2016 through December 31, 2024, and have no missing corresponding Yahoo closes or scheduled daily sessions.
The signed difference is `(Yahoo Close / Alpaca close - 1) * 10000`.
Different auction/trade-condition conventions are a possible explanation, not an established cause or permission to widen the threshold.
A fresh independent source and provider aggregation definitions are needed before selecting any revised close basis.

Twelve minute rows fall on the prior New York date because the request started at UTC midnight.
The earliest timestamp is December 31, 2015 at 19:01 New York; the last is December 31, 2024 at 18:59 New York.
Calling the existing calendar validator directly after the daily check fails on December 31, 2015 with 390 missing regular minutes, since that input begins after its regular close.
The diagnostic uses the declared local-date interval to expose this boundary issue without editing or silently trimming the immutable cache.
Even an explicit future boundary fix would leave the eight real gap dates and daily-close discrepancies unresolved.

## Provenance and checks

| Local source | SHA-256 |
|---|---|
| Minute compressed cache | 2a4b87ac1c745533cef13e14d76bf639e3e8148e2a29478540706a1dee41be6e |
| Daily compressed cache | c164b66481de6ef01294f0eef3e059460cebc635cc060a2335a38a876c906d32 |
| Existing Yahoo SPY cache | 67371e45a62f59f0dd6ad6c10d220ad5365c8dc6c612003240968f3f2acd26e4 |

Minute retrieval completed at 08:18:54.007388 UTC and daily retrieval at 08:18:55.534828 UTC.
The private preparation log, diagnostic JSON and immutable caches preserve the failed attempt.
The new diagnostic agrees with an independently executed calendar/daily comparison in this maintenance run.
Five focused synthetic tests passed, covering holidays and early closes, multiple gaps, UTC boundary spillover, missing daily/reference dates, invalid timestamp ordering, the reserved-date guard, cache corruption and absence of file mutation.
The full suite passed 462 tests in 10.76 seconds.
Synthetic fixtures are engineering tests, not trading results.

Next work should reproduce unexplained gaps with bounded source requests, verify close definitions against independent records, and preregister any halt/boundary treatment before evaluating returns.
Retain this failed preparation attempt and the original validation policy; do not force the 10% monthly target by deleting difficult sessions.
