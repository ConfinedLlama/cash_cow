# Packet context v3 — frozen offline construction protocol

Registered November 12, 2026 before archive evaluation. Hypothesis: receiving
recent price history and verified official-release values before a decision
could reduce missing-context HOLDs. This is not evidence that more trades or
higher returns will follow. The current paper_ai_v1 and packet_context_v2 stay
frozen; no runtime import, prompt change, model call or order is introduced.

The config fixes SPY/IEX, six five-minute OHLCV aggregates, 5/15/30-minute close
returns, 120-second history age, seven-day release age and 20,000 UTF-8 packet
bytes. Three arms use the identical baseline context: baseline alone, baseline
plus history, and baseline plus history plus available official releases.
No missing input is imputed; empty release archives are explicitly unavailable.
Packet overflow rejects the observation rather than selectively trimming news.

History must come from receipt_capture_v1 with response hashes, sequential
request/receipt times, at most 60 seconds per read and 120 seconds overall,
wall/monotonic duration agreement within one second and broker/local receipt
agreement within ten seconds. All receipts precede the decision cutoff. The
request covers only completed current-session minutes; calendar close, sparse
bars, zero volume, price mismatch, stale data and legacy timing can reject it.
The unchanged v2 feature formulas are reused, without relabeling old archives.

Every nonempty official-release archive must pass release_evidence_v1 before
selection, including records observed after the decision (those remain excluded
from the packet). Publication, capture, manual review and first observation keep
their distinct times. SHA hashes verify local bytes and references; they do not
prove source authorship, accurate numeric extraction or clock synchronization.
Original captures, exclusions and failed observations remain in the denominator.

## Evaluation and costs

Phase one is offline construction on all saved decision records, including
failed/pending proposals. Use the latest receipt no later than each cutoff;
ambiguous equal-time sources reject history arms. Never replace a bad latest
capture with an older convenient one. Report each arm's assembled/rejected
count, reason, sizes, source/code/specification hashes and unavailable inputs.
Previously inspected records are development diagnostics, not a holdout. A
successful packet is not a successful model decision or a profitable trade.

A later model comparison needs an explicitly registered future start, frozen
prompt/model and bounded request budget before collecting its 20 scheduled
sessions. It is not activated by this protocol. Match all arms at the same
cutoffs; keep outages, missing packets, refusals and losing outcomes. Do not
extend the window to replace failures. Compare to the frozen baseline and cash,
and assess coverage, decision validity, latency and cost-stressed results before
returns. No performance-based tuning or 2025+ retrospective price retrieval.

For any later simulated execution, preserve a USD 2,000 sleeve, 95% allocation,
no borrowing, whole shares and a per-filled-order stress of
max(USD 0.40, USD 0.0035/share) plus two basis points. Model usage and data costs
must be reported separately. Complete-month returns, profitable/target-hit
months and drawdown require verified coverage; no 10% monthly claim follows
from this engineering protocol. The existing paper risk limits remain intact.

## Read-only archive audit

```sh
.venv/bin/python -m cash_cow.packet_research.replay_v3 \
  --directory data/telemetry/paper_ai_v1 \
  --captures .local/research/receipt_captures
```

Optional `--releases` and `--evidence` must be supplied together; source files
resolve beside the evidence manifest. Output contains only aggregate counts,
fixed rejection categories and hashes. The CLI returns 2 for review required,
including empty archives; this does not start a collector or request a model.
Invalid capture identities/timestamps invalidate history construction across the
archive rather than allowing selection around an unorderable record. All read
inputs are bounded and hash-checked again, and decision/capture membership is
rechecked, but these checks cannot make a live directory an atomic snapshot.
