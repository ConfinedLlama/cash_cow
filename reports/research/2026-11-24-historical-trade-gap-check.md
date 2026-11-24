# Historical trade-gap investigation - November 24, 2026

## Result and hypothesis

Fresh SPY SIP trade queries returned no records across all five unexplained intervals, totaling 48 missing minutes.
Four adjacent positive controls returned 2,106 records, establishing that authentication and nearby historical retrieval worked.
This rejects the narrow repair hypothesis that these queries would supply trades from which the missing bars could be reconstructed.
It does not establish that no exchange trading occurred, prove a halt, or identify whether the provider has a historical coverage defect.
All observations come from the same provider and are not independent corroboration.

## Method and evidence

Thirteen bounded GET requests used the [Alpaca historical stock trades endpoint](https://docs.alpaca.markets/us/reference/stocktrades-1), SPY, SIP, ascending order and a 10,000-record limit.
Four initial one-minute samples, four preceding-minute controls and five complete-gap queries all returned HTTP 200 with no next-page token.
Intervals below are half-open New York times; the inclusive API end was set to one nanosecond before the exclusive boundary.
The initial samples were first observed at 10:31:36 UTC on November 24; controls at 10:32:50 UTC; full intervals from 10:34:56 UTC.
No query accessed the protected 2025+ historical holdout.

| Date | Complete gap, America/New_York | Missing minutes | Returned trades |
|---|---|---:|---:|
| 2016-02-02 | 11:19 to 11:28 | 9 | 0 |
| 2019-08-12 | 15:29 to 15:31 | 2 | 0 |
| 2019-08-12 | 15:32 to 16:00 | 28 | 0 |
| 2021-05-05 | 11:27 to 11:32 | 5 | 0 |
| 2023-06-05 | 09:52 to 09:56 | 4 | 0 |

| Date | Positive control, America/New_York | Returned trades |
|---|---|---:|
| 2016-02-02 | 11:18 to 11:19 | 295 |
| 2019-08-12 | 15:28 to 15:29 | 187 |
| 2021-05-05 | 11:26 to 11:27 | 620 |
| 2023-06-05 | 09:51 to 09:52 | 1,004 |

Raw licensed responses and acquisition metadata remain ignored under `.local/daily/2026-11-24-evidence/`.
The sample/control manifest SHA-256 is `5d83f0fd471ff54f78f8b1c2330a0ab5e7b7b36084c083d2fb700543ef5d6556`.
The complete-gap manifest SHA-256 is `c213fbaab574627855eeaee3c08a295a879cca0e3ebcfe1b38507fc6e8f14f80`.
All empty response bodies share SHA-256 `d7e3220c2f8fe6e76f2cc4b8b74c54e14da90d5028f56f49334652cd88f0b57b`; separate request metadata preserves which interval each response concerns.

The new [offline trade audit](../../docs/HISTORICAL_TRADE_AUDIT.md) verified response hashes, request bounds, pagination, ordered timestamps and positive finite trade values against all thirteen responses.
Its seven behavioral tests passed, covering empty versus partial responses, hash corruption, duplicate files, boundary timestamps, invalid numeric fields and holdout rejection.
The complete integration suite passed with 481 tests after the reporting-format change.
The audit does not reconstruct OHLC, classify trade-condition eligibility or certify a market-wide absence of trading.

## Validation remains blocked

The cached multi-year validate-only command was rerun and failed at the unchanged API/Yahoo daily-close threshold of 10 bp.
The previous investigation's 20 discrepant closes and maximum absolute difference of 279.3449063488651 bp remain unresolved.
Of 104 missing minutes, 56 overlap the previously documented March 2020 halt windows; today's 48-minute inquiry concerns the remainder.
Twelve UTC-boundary rows also remain unresolved.
The original data and frozen v4 configuration were not modified; configuration SHA-256 remains `7ba220afc43792725e5ea215063cda9bc59073e54844838539efd14d42ff2992`.
No base or sensitivity strategy run was completed, and no return, drawdown or edge follows from this diagnostic.
The 44 base and 440 sensitivity runs retain their declared costs and evaluation plan.

Next obtain independently documented historical coverage and close-price semantics before proposing a versioned data treatment.
Do not fill missing bars, drop bad dates, relax discrepancy tolerances or select a source simply to obtain a favorable backtest.
