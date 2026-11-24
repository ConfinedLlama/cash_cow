# Historical trade-probe audit

Use this offline command to verify private response snapshots from bounded historical SPY SIP trade queries:

```sh
.venv/bin/python -m cash_cow.intraday.trade_audit PATH/manifest.json
```

The manifest declares endpoint `https://data.alpaca.markets/v2/stocks/trades`, symbol `SPY`, feed `sip` and a `probes` list.
Each probe specifies `start`, `end_exclusive`, `http_status`, `observed_at`, `response_file` and `response_sha256`.
Keep responses and manifests in ignored local evidence directories; never commit raw licensed trades.
Response files must be unique basenames alongside the manifest and match their recorded SHA-256.
Requests must succeed with HTTP 200; the diagnostic does not equate an API failure with zero trading.

The audit rejects intervals outside 2016-2024 UTC or longer than one hour, unordered/out-of-range timestamps, unexpected symbols and invalid price/size values.
Trade timestamps retain nanosecond precision.
The [Alpaca endpoint](https://docs.alpaca.markets/us/reference/stocktrades-1) documents an inclusive end; the acquisition queries use one nanosecond before the diagnostic's exclusive end.
An end-boundary record is rejected rather than assigned to the preceding missing minute.

An empty complete response is labelled `no_records_returned`, not absence of trading or evidence of a halt.
A remaining pagination token produces `partial_response` and CLI exit 2; its count is a lower bound.
Missing pagination metadata is rejected rather than assumed complete.
A successful audit only establishes consistency of the supplied snapshot, not vendor accuracy, independent provenance or bar eligibility under sale-condition rules.
The manifest records the stated feed; a hash does not independently authenticate the provider.
The command performs no network calls, state changes, price reconstruction, validation exemptions or strategy evaluation.
The paper runner and frozen historical validator do not import it.
