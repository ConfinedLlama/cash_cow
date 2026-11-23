# Historical halt overlap audit

Run `.venv/bin/python -m cash_cow.intraday.halt_audit` to classify the frozen historical cache's missing minutes against a separate sourced halt reference.
It reads verified source hashes through the existing input audit and writes JSON to stdout only.
Exit 2 preserves unresolved input issues even when missing minutes coincide with known halts.
This module is not imported by the trading runner or backtest validator.

Each missing bar covers a half-open one-minute interval.
The diagnostic reports full containment, partial overlap, or no overlap with listed halt windows.
It converts explicit offsets to UTC, rejects overlapping or unordered evidence, and does not count a boundary touch as overlap.
Adjacent halt intervals can cover a minute together without counting that minute twice.
Partial trigger and reopening minutes remain distinguishable from fully halted minutes.

The reference is `configs/historical_mwcb_2020.json`, transcribed from pages 4-5 of the [exchange working-group report](https://www.nyse.com/publicdocs/nyse/markets/nyse/Report_of_the_Market-Wide_Circuit_Breaker_Working_Group.pdf), published March 31, 2021 and rechecked November 23, 2026.
It records market-wide triggers and the beginning of reopening auctions, not each symbol's actual reopening time.
It is retrospective research metadata and must not enter historical decision packets as if known before publication.
The list is not an exhaustive halt database.

On the original cache, 56 of 104 missing minutes fall wholly inside these windows; 48 are outside the listed windows and none partially overlap.
All 104 remain flagged by the original validator.
The twenty close discrepancies and twelve exchange-local boundary rows also remain unresolved.
Do not interpret correspondence as causation, price repair, a gap exemption, or permission to run v4.
Any future halt-aware execution treatment needs a separately declared evaluation plan with frozen costs and leakage controls before strategy results are inspected.
