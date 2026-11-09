# Packet context v2 — offline candidate, November 9, 2026

## Hypothesis and version boundary

Several saved paper_ai_v1 explanations cite missing momentum history and the
employment-release outcome. Explanations are not causal evidence, and HOLD can
be correct. Hypothesis: timestamped price history and structured official release
values improve input completeness and decision specificity. More BUY responses
alone are not success. This protocol is recorded before candidate packet results.

`configs/packet_context_v2.json` freezes the first offline specification. No model
calls, service selection, automatic collector, broker integration or deployment
are authorized by loading this configuration. Active paper_ai_v1 and its 20-day
window remain unchanged. Subsequent specification changes get a new version.

## Inputs and causality

- SPY IEX current-session minute bars only. Require contiguous, positive, finite
  OHLCV with valid bounds; never interpolate. Use only complete bars through the
  baseline feature bar. Retain six five-minute OHLCV aggregates and close-to-close
  returns at 5, 15 and 30 minutes. Insufficient history is unavailable, not zero.
- A snapshot must be observed no later than the packet and be at most 120 seconds
  old. Future bars, wrong feeds and conflicting session dates are rejected.
  Existing snapshots record tick-start time, not HTTP receipt time. Replays of
  them are **legacy timing diagnostics**, not certified causal market experiments.
  Future capture needs a verified receipt timestamp before a model comparison.
- Official economic values require release ID, metric, period, unit, value,
  dated primary-source URL, publication timestamp, first observation timestamp
  and vintage timestamp. Only values published, observed and revised by the
  decision cutoff qualify. At most seven days old. New revisions cannot replace
  old values before they were observed. Ambiguous duplicate vintages fail.
- Initial allowlist: BLS employment payroll change (thousands of persons),
  unemployment rate (percent), CPI month-on-month (percent), PPI month-on-month
  (percent). No news-derived consensus, surprise score, forecast or imputed value.
  Scheduled events alone do not contain released outcomes.
- No historical post-2024 download. Offline diagnostics use the already collected
  November 5–6 packets and snapshots. They are development data already inspected;
  no out-of-sample performance or causal model-response claim is allowed.

## Fixed evaluation and costs

Three fixed arms: unchanged baseline packet; baseline plus history; baseline plus
history and eligible official releases. Preserve baseline fields and original
records. Deterministic assembly is capped at 20,000 UTF-8 bytes. Oversized packets
fail; do not silently drop inconvenient news or fields. Record exact source,
configuration and output hashes. No original packet is rewritten.

First phase evaluates data construction only: input availability by arm, rejected
snapshots/releases, causal exclusion, numeric correctness and byte sizes. Retain
all failures. No model calls, action counterfactuals, simulated orders or returns.

A later prospective paired comparison must be separately enabled and its start
date fixed before receiving new outcomes, covering the next 20 scheduled exchange
sessions without replacing outages. It must share a declared total model-request
budget with the baseline; no paid fallback or increased subscription demand is
assumed here. Freeze prompt/model/backend and execution assumptions, compare
matched timestamps, and preserve every failure and abstention. Report coverage,
invalid/expired response rate, latency, rationale specificity, action disagreement,
turnover and net performance separately. No activation follows automatically.

If a future fill study is approved, use separate ownership/ledgers; USD 2,000,
95% maximum allocation, SPY long-only, one entry per session, no borrowing, the
existing USD 40 daily/USD 100 total breakers and session exits. Stress each order
by max($0.40, $0.0035/share) plus 2bp. Report model costs separately, all losing
trials, drawdown, cash and same-session SPY benchmarks. Missing quotes/fills or
benchmark bars stay missing. Nothing here promises 10% monthly or proves an edge.

## Promotion criteria and current limit

Fixture tests and archive diagnostics must pass with source integrity checks,
but passing is only an implementation gate. No decision threshold or history
window is tuned based on BUY count or P&L. Deployment requires a documented new
trial, verified acquisition timing and a flat-account cutover; maintenance must
not replace the currently frozen strategy. Current work ends at offline inputs.
