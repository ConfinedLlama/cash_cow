# Historical close-definition diagnostic

Run `.venv/bin/python -m cash_cow.intraday.close_audit` to compare the existing 2016-2024 SPY cache without fetching or modifying prices.
The command verifies the original input manifests and rechecks all source hashes after analysis.
It retains every original input issue and exits 2 while validation remains blocked.

For every scheduled NYSE session it compares the reference daily close against four separately labelled observations:

- The original Alpaca daily close.
- The exact final regular-session minute's close, using the exchange calendar including shortened sessions and daylight-saving changes.
- The close of the minute beginning at the scheduled closing time, which may contain auction or post-session trades.
- The close of the last observed minute on that New York date, which is not necessarily an official closing price.

Differences use `(reference / comparison - 1) * 10000` and are basis-point price discrepancies, not investment returns.
Output includes availability, missing boundaries, counts above the unchanged 10 bp threshold, maxima and detailed comparisons for the original discrepant dates.
No nearby minute replaces a missing exact boundary, and a favorable comparison does not erase the original mismatch.
The command publishes derived differences only, never raw price series.
Invalid evidence produces a fixed sanitized issue label.

[Alpaca's aggregation documentation](https://docs.alpaca.markets/us/docs/market-data-faq) distinguishes minute and daily trade-condition eligibility.
A minute bar at the closing boundary is not itself an official auction record.
The [SEC's closing-price explanation](https://www.investor.gov/introduction-investing/investing-basics/glossary/closing-price) explains why different quotation services may report different closing prices.
These definitions motivate the diagnostic but do not establish the cause of any particular historical discrepancy.
A documented independent source and versioned evaluation decision are still required before changing the frozen validator's price basis.
The module is not imported by the paper runner or historical strategy pipeline and grants no backtest approval.
