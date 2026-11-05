# Alpaca prospective paper runner

Authorized November 3, 2026. This is an engineering and prospective research trial, not an approved funded strategy. Paper orders use **only** `https://paper-api.alpaca.markets/v2`; market data uses `https://data.alpaca.markets`. No configurable live URL exists. The original `paper_v1` strategy described below is deterministic and is now stopped. Since November 4 the service selects `paper_ai_v1`, whose model proposals pass through the same deterministic execution/risk controls. See [AI_PAPER_TRIAL.md](AI_PAPER_TRIAL.md) for its frozen protocol.

## Frozen first experiment

`configs/paper_v1.json` registers `paper_orb30_v1`, a new opening-range/VWAP candidate. It is **not** the selected winner of v3/v4 and has no claimed historical edge. It avoids requiring a retrospective post-2024 warm-up download. Current-session data collection is authorized by the prospective paper task; the older historical holdout stays untouched.

- SPY only, long-only, whole-share entries, USD 2,000 research sleeve, at most 95% allocation and no borrowing. The broker paper balance may be larger; the sleeve ledger and sizing remain capped.
- First 30 minutes define the high/low. At completed five-minute boundaries from 10:05 New York time, attempt a long entry when the close exceeds both opening-range high and cumulative HLC3 volume-weighted price. Missing minutes invalidate signals; no interpolation.
- One entry attempt per session, including canceled/rejected attempts. No new entries during the final hour. No new entries on shortened sessions. Entry is a DAY limit at ask + 2bp rounded upward to the cent; quantity is capped using that limit. Cancel unfilled remainder after 60 seconds and reconcile partial fills.
- Exit on a completed five-minute close below opening-range low or VWAP, a risk/data breaker, a stop request, or ten minutes before exchange close. Exits are paper DAY market orders for reconciled long inventory only. Up to five exit attempts per day; failures require attention. A fresh market-clock check prevents deliberately queueing an after-hours exit.
- USD 40 daily and USD 100 total drawdown-from-initial-capital circuit breakers use observed bid-marked sleeve NAV after the modeled cost overlay. These are triggers, not guaranteed maximum losses. Quote/API/network failures and polling gaps can prevent timely execution.
- IEX is explicitly selected. Its observations cover one exchange, while Alpaca paper fills use its simulation rules; this is not identical to consolidated-market execution. Do not silently change feeds or parameters during the trial.

Keep the initial configuration and strategy source frozen for an initial 20 observed sessions unless a correctness or safety defect requires suspension. Twenty sessions are an engineering observation window, not enough to prove a trading edge. Review fills, missing data, reject rate, drawdown and net costs before proposing another frozen candidate. Preserve failures and no-trade sessions. Separate accounts/ledgers are required before interpreting multiple strategies' broker P&L independently.

## Credentials and preflight

Use a dedicated Alpaca **paper** account with no existing positions or open orders. Place its matching key pair locally in `.env` as `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`. Spaces/quotes are unnecessary. Do not paste keys in chat, Git, commands or service definitions. `.env` is ignored by Git. A 401 means the current credentials were not accepted; regenerating a key requires replacing both local values. The running trading client reads keys on process start.

```sh
cd /Users/matthiasjoseph/Desktop/cash_cow
.venv/bin/python -m cash_cow.paper check
.venv/bin/python -m pytest -q
.venv/bin/python scripts/paper_service.py install
.venv/bin/python -m cash_cow.paper status
```

`check` performs read-only API calls. `install` repeats a paper-account preflight and creates the macOS user LaunchAgent `com.cashcow.paper`, then starts the runner. It never embeds credentials in its plist. The account fingerprint, frozen configuration/source fingerprint and initial cash baseline bind the durable state to this trial. Never delete state to clear an error; doing so can destroy order ownership and accounting evidence.

## Operation and recovery

The runner polls every 15 seconds in-session and 60 seconds when closed, using Alpaca's clock and calendar for time zones, holidays and early closes. It uses an exclusive OS lock to prevent two workers sharing state. Each order intent is atomically persisted and fsynced **before** submitting. The same client order ID is looked up after a timeout/restart. Unknown outcomes are never blindly retried. Manual orders, unexplained cash changes, account switches and fill/position mismatches block further submissions pending reconciliation.

The service runs under the logged-in macOS user and restarts after abnormal termination. Since November 4, it wraps the process with `/usr/bin/caffeinate -i` to prevent automatic idle system sleep while the runner is running; the display may still sleep. **Keep the Mac plugged in, online, logged in and the lid open.** Lid closure, explicit sleep, shutdown and network outages are not prevented by this assertion. Confirm `pmset -g assertions` shows caffeinate's `PreventUserIdleSystemSleep`. Codex need not remain open for the runner itself; the separate daily Codex maintenance still needs the app. The service is not a cloud deployment. Machine/network failure can leave paper exposure overnight; the next active session attempts to flatten it and halts the trial for review.

Incident on the November 3 US session: the Mac entered idle sleep at 22:30:41 Singapore, shortly after the open. The runner first observed the open session at 23:21 and blocked entries for a monitoring gap. No orders were submitted. This was an operationally blocked session, not evidence that the strategy saw no opportunities. The initial deployment omitted explicit sleep prevention; the November 4 maintenance corrected the service definition after verifying the account flat and stopping the old process. Its recorded session remains preserved.

```sh
# Inspect service and journal status:
.venv/bin/python scripts/paper_service.py status
.venv/bin/python -m cash_cow.paper status --config paper_ai_v1
# Request safe stop, cancellation and regular-session flattening:
.venv/bin/python -m cash_cow.paper stop --config paper_ai_v1
# Refresh the private human-readable performance report:
.venv/bin/python -m cash_cow.paper report --config paper_ai_v1
```

For the active version, run `.venv/bin/python -m cash_cow.paper.health` to audit heartbeat age, news freshness, nonterminal intents and session event gaps. Run `.venv/bin/python -m cash_cow.paper.news_audit` to verify stored revision hashes and causal timestamps; `--as-of` accepts a timezone-aware cutoff. Both commands are read-only, make no broker/model calls and emit sanitized aggregates. Exit 2 means review is needed, not permission to reset state. A fresh heartbeat does not erase a blocked session or establish broker reconciliation. News integrity does not establish comprehensive coverage. Separately verify actual broker positions/orders, process ownership and the caffeinate assertion.

November 4 session incident: power logs show Clamshell Sleep at 21:46:45 Singapore before the US open, and again at 00:18:39 November 5. The runner first observed the session around 23:11:59 Singapore and blocked it for a monitoring gap. No AI proposals or orders occurred. The idle-sleep assertion remained active; it cannot prevent lid-closure sleep. Keep the lid open and maintain power/network, or separately plan an always-on host. Do not weaken the monitoring-gap guard to manufacture trades.

The STOP file is persistent and the process exits only after confirmed flat/no pending orders during its normal loop. Closed markets or unresolved orders can delay completion. Verify in the paper dashboard before unloading the service. Do not kill a process and assume this canceled broker orders. After a safe stop, restarting requires deliberate removal of STOP and `launchctl kickstart gui/$(id -u)/com.cashcow.paper`; inspect state first. `run --once` is an execution tick, not a dry run, and must not be run while the service owns its lock.

## Evidence and reporting

Private data stays under `data/telemetry/paper_v1/`, excluded from Git:

- `state.json`: durable order intents, cumulative broker order responses, session coverage, reconciliation and circuit-breaker state.
- `events.jsonl`: timestamped decisions/status, marks and error categories; `bars/`: first-observed signal snapshots and source hashes.
- `sessions.json`: only closed, flat, reconciled sessions, with explicitly modeled costs. Missed days and unresolved sessions are not invented as zero returns.
- `REPORT.md`: paper and cost-stressed session returns, attribution/coverage limits and news-collector health.
- `news/`: private headline metadata/revisions with source URL, publication/update time and first-observed timestamp. Full article content is not requested.

Broker fill P&L and a separate stress overlay are both reported. The stress overlay is max(USD 0.40, USD 0.0035/share) plus 2bp per filled order; these are **assumptions**, not reported Alpaca fees or measured live slippage. Alpaca simulation omits several real-market costs and execution effects. No live monthly-return promise follows from its results. Full-month statistics require an explicit exchange-session coverage audit.

The daily maintenance should read this report, source journal and news health before proposing changes. Use the generic daily reporter with `--observations data/telemetry/paper_v1/sessions.json` only when reconciled sessions exist; retain the cost-stress label. Publish sanitized aggregates and explanations, never raw accounts or licensed feed content.

## Quantitative and qualitative research

The background news collector polls the general Alpaca news feed every five minutes on a separate thread, preserving revisions and first observation time. It samples a rolling 15-minute window with a three-page bound; gaps/truncation/errors are explicit. It is neither a comprehensive geopolitical monitor nor a low-latency news-trading engine. News failures do not alter the fixed baseline strategy. Text is untrusted context and cannot change configurations or issue orders.

`configs/event_watchlist_2026.json` records selected BLS and Fed dates checked November 3, with primary-source links. Reverify before each relevant session; this seed is incomplete and is not an automatic entry blackout. The daily research review should also inspect central-bank announcements, trade/tariff changes, sanctions, elections, major company events and geopolitical developments using primary sources where available. War/outbreak timing cannot be predicted reliably. Distinguish scheduled releases, reported events and speculation.

For a news-informed candidate, preregister the source universe, timestamp/latency rules, mapping from information to exposure, event exclusion windows, and evaluation before activating a new version. Compare against the unchanged quantitative baseline with identical costs and risk budgets. Never replay a revised article using its original publication time as if its revised contents were available then. Qualitative context can inform a hypothesis or a reviewed risk pause; it is not evidence by itself that a direction trade will make money.

## Eventual live funding

No deposit is required for Alpaca paper trading. The eventual capital remains in the user's control. Interactive Brokers Singapore is a broker candidate, subject to account eligibility, permissions, costs and API suitability; it is not integrated by this runner. If selected later, deposit into the user's own brokerage account using the currency-specific instructions generated by that broker's authenticated Client Portal, from an account in the user's name. Never send capital to an assistant, developer or intermediary. SGD versus USD budget remains unconfirmed.

Funded execution needs a separately implemented broker adapter, broker-specific paper validation, reconciled results, operational monitoring and explicitly agreed loss/position limits. A change of API key does not turn this paper-only client into a live client. The user will explicitly authorize a concrete deployment when ready.

## Primary references

- [Alpaca paper environment and limitations](https://docs.alpaca.markets/us/docs/paper-trading)
- [Order fields and regular-hours behavior](https://docs.alpaca.markets/us/reference/postorder)
- [Order recovery by client ID](https://docs.alpaca.markets/us/reference/getorderbyclientorderid)
- [Minute bars](https://docs.alpaca.markets/us/reference/stockbars), [quotes](https://docs.alpaca.markets/us/reference/stocklatestquotes-1), [news](https://docs.alpaca.markets/us/reference/news-3)
- [BLS November](https://www.bls.gov/schedule/2026/11_sched.htm), [BLS December](https://www.bls.gov/schedule/2026/12_sched.htm), [Fed meetings](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
- [IBKR Singapore funding](https://www.interactivebrokers.com.sg/en/support/fund-my-account.php), [API solutions](https://www.interactivebrokers.com.sg/en/trading/ib-api.php)

## November 6 Singapore: quote-timing execution correction

Interactive investigation of the November 5 US session found 16 completed AI
proposals, all HOLD, and zero journaled orders; a fresh read-only broker check
confirmed zero positions and open orders. Entries became blocked at
16:32:29 UTC with `stale_or_unavailable_quote`. The old event did not preserve
quote age or exception type, so the precise cause of that incident cannot be
proven retrospectively. Network errors and a clock-discrepancy event were also
observed. These are incomplete-session observations, not performance evidence.

An execution defect was reproduced with synthetic latency: quote age used the
start of a tick, before multiple sequential HTTP requests. Two four-second
account requests caused a genuinely fresh quote to appear eight seconds in the
future and trip the five-second tolerance. The correction uses receipt time,
retains the 60-second freshness limit and five-second future tolerance, and
records sanitized failure type and measured age. A fresh pre-submission check
also rejects quotes that expire during later work and entries crossing the
existing session cutoff. It does not change the frozen AI prompt, model,
configuration, position sizing, cost assumptions, or decision thresholds.

This is an execution-code revision of `paper_ai_v1`, recorded by its Git commit,
not a new strategy or a reset of the trial. Existing session blocks, proposals,
usage, orders and losses remain intact. New sessions follow the original rules;
no automatic data-failure recovery or forced BUY has been added. For deployment,
request a safe stop, verify the `stopped` event and broker flat/no open orders,
then remove only the deliberate STOP marker and restart the same service.
Never delete state to resume a blocked day. Preserve the revision boundary when
interpreting prospective results. Historical holdout data was not accessed.

Validation: four regression tests cover delayed quote receipt, quote expiry
before submission, crossing the entry cutoff, and sanitized diagnostics with
persistent session blocking. The complete suite passed: 140 tests. Test orders
are synthetic fixtures and were never sent to Alpaca.
