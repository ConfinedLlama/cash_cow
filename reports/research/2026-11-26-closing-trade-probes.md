# Closing-trade probes - November 26, 2026

## Question and bounded finding

Following the rejected blanket close substitution, does transaction evidence immediately around the March 12, 2020 SPY close corroborate the cached daily close?
Two one-second SIP samples returned 1,016 records, with none within one cent of that cached daily close.
There were 48 records within one cent of the Yahoo reference close.
This exploratory diagnostic does not establish which closing definition is correct, and does not authorize replacing a price or passing the historical validator.
The date was selected after observing historical discrepancies, not as an independent performance test.

| UTC half-open interval on March 12, 2020 | Returned records | Within one cent of cached daily close | Within one cent of Yahoo reference | Pagination complete |
|---|---:|---:|---:|---|
| 19:59:59 to 20:00:00 | 775 | 0 | 4 | yes |
| 20:00:00 to 20:00:01 | 241 | 0 | 44 | yes |

The first sample contains conditions regular sale, F and I in combinations; the second also includes T and 6.
Condition combinations were retained privately, not interpreted as evidence that every print can update a closing bar.
[Alpaca's aggregation documentation](https://docs.alpaca.markets/us/docs/market-data-faq) describes tape-, condition- and bar-type-dependent eligibility.
For example, its table excludes odd-lot condition I from updating open/close.
Matching a print's price does not identify an official auction close or establish eligibility.

## Reproduction and limits

Both authenticated requests used `GET https://data.alpaca.markets/v2/stocks/trades`, symbol SPY, feed sip, ascending order, and limit 10000.
The API's inclusive end was set one nanosecond before each displayed exclusive end.
Responses were observed at 2026-11-26T08:09:20.068016+00:00 and 2026-11-26T08:09:20.328183+00:00, with HTTP 200 and no continuation token.
The existing trade-response auditor checked the raw responses against the manifest and interval boundaries.
The comparison used the cached March 12 daily row after converting its timestamp to New York's date, the matching Yahoo Close row, and `abs(trade_price - close) < 0.010001` for the one-cent comparison with floating-point tolerance.
No prices, account identifiers, trade identifiers or raw licensed records are published here.

Private evidence is in `.local/daily/2026-11-26-evidence/`:

- `close-trades-manifest.json`: SHA-256 `bdf3fafcbea1b2b8d86513948d9734f319d52f77dbed717fc2570cfbf4723b1c`.
- `close-trades-preclose.json`: SHA-256 `693f3bbb5ea29d5394a4d7bcc6a88f117a97e4b671c1f718881c0191b27af850`.
- `close-trades-boundary.json`: SHA-256 `91e90bd422483621525f774a17b71ba01421aad1c6ef40734f42d2196664f95e`.
- `close-trades-audit.json` and `close-trades-comparison.json` retain audit and aggregate comparison results.

These are only two seconds from one provider, not a full closing minute, auction record, correction history or full-day eligible-trade reconstruction.
Absence from these samples does not prove that the cached daily price never traded that day.
A larger sample would require a declared acquisition scope and complete pagination before drawing broader conclusions.
No OHLC repair, strategy evaluation, cost adjustment or threshold selection was performed.

## Validation and next step

All three frozen historical source hashes match yesterday's retained close audit after today's analysis.
The full software suite passed 500 tests in 16.47 seconds, including existing trade-auditor and close-auditor tests.
The raw-response auditor reported 775 and 241 records with complete pagination and valid intervals.
The 44 base and 440 sensitivity runs remain blocked by the previously documented data issues; they were not rerun today.
The protected 2025+ historical holdout remains untouched.
Obtain a primary-market closing record and documented correction/eligibility treatment before proposing a versioned data repair.
