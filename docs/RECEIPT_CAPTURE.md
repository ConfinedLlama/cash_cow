# Current-session receipt capture

The November 9 offline packet audit found that legacy snapshots record the
runner's tick-start time, not receipt of the HTTP response. A snapshot may not
have been available at that earlier instant. The standalone `receipt_capture_v1`
tool records request start and conservative response availability after decoding.
It does not rewrite old timestamps or connect a new input to paper_ai_v1.

Run a single observation manually from the repository:

```sh
.venv/bin/python -m cash_cow.packet_research.capture
```

It checks the broker clock, requests that day's exchange calendar when open,
then requests only completed SPY IEX minutes from the current regular session.
Closed markets are archived as `market_closed`, with no price download. The
first minute returns `no_completed_minute`. No old-session date argument exists.
Early closes use the exchange calendar. No model, account, position or order
methods are invoked. The active LaunchAgent never imports this module.

Each response has its own start, receipt, monotonic duration and payload hash.
Reads over 60 seconds, clock discontinuities, clock/broker disagreement above
10 seconds, unexpected pagination, wrong sessions/symbols, duplicate or future
bars and invalid OHLCV are rejected. Sparse bars are retained as incomplete;
there is no interpolation. A 120-second total clock-to-bars limit applies.
These acquisition checks do not change the frozen candidate's thresholds.

Complete content-addressed JSON files are published without overwriting under
ignored `.local/research/receipt_captures/`, with 0600 file permissions. A failed
write leaves no final partial file. Preserve command failures in the daily audit;
the CLI withholds raw exception data and returns exit 2. Exit 0 can mean closed
market or incomplete data: inspect status, not just exit code. Raw licensed
responses remain local. A successful artifact proves local recording, not an
authenticated exchange publication timestamp, synchronized clock or completeness
of the provider's feed. Hashes detect changes; they do not establish authenticity.

This is a one-shot collector, not a scheduled service. No automatic integration
or strategy evaluation is enabled. `packet_context_v2` remains frozen and its
reader does not accept this new format. A future explicitly versioned adapter
must enforce response receipt before decision cutoff and preserve both source
and packet hashes. Historical diagnostics remain labelled legacy timing.
Model comparison still needs its own fixed prospective start and request budget.

## Offline receipt validation (November 12)

`packet_research.receipts.receipt_history` now validates saved capture payload
hashes, request/response ordering, monotonic durations, decision cutoff,
current-session calendar, exact request scope and complete minute coverage.
It reuses v2's unchanged feature formulas and rejects future, sparse, stale,
closed-market and legacy records. Zero-volume bars remain excluded by those
feature rules. This is a pure offline reader, with no runtime imports or calls.
Local timestamp consistency is not proof of synchronized clocks or source
identity; preserve the original capture hash alongside normalized features.
The versioned packet consumer is a separate research step.
