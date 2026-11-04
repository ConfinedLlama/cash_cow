# AI-driven Alpaca paper trial

Requested November 4, 2026. The user explicitly selected AI decisions with simulated money, then chose their existing ChatGPT subscription. The initial API-based draft was disabled pending credentials. The subscription backend subsequently passed an authenticated structured-response preflight using the app's bundled Codex CLI. Check the daily report and actual service heartbeat for deployment status; a successful preflight alone cannot establish trading activity.

The selected backend is `codex_subscription`, using the existing supported CLI login without extracting tokens. It ignores user configuration, disables shell, apps, plugins, browsing and other execution features, uses a temporary working directory and read-only sandbox, and rejects unexpected tool activity. Only the supplied market/news packet informs the proposal. The subprocess receives an allowlisted environment without broker or API keys. It is terminated after 45 seconds, and failures cannot silently fall back to API billing.

## What changes

A model proposes BUY, HOLD or EXIT from current quantitative features, quote context, recent first-observed news and the sourced event watchlist. A BUY does not require the original ORB breakout condition. EXIT can close the reconciled long position. The original ORB features remain observations in the model packet, not the final decision rule. HOLD, unavailable responses and refusals generate no new orders.

Code continues to enforce SPY-only, long-only, USD 2,000 allocation, at most 95% invested, one entry attempt per session, whole-share entry, spread/data checks, daily/total loss breakers, session cutoff, ownership and reconciliation. The model receives no broker credentials, trading tools, executable code capability or authority to change these constraints. Risk and end-of-session exits run before model proposals and do not wait for model requests.

The initial model is `gpt-6.1-sol`, low reasoning effort, with strict structured output and local validation. Confidence is an uncalibrated score; the initial 0.6 entry gate is a declared design choice, not a demonstrated probability of success. News instructions are ignored and citations must match supplied IDs. Unknown fields, unsupported actions, fabricated citations and invalid numeric values reject the proposal.

## Timing and budget

At most one model attempt is made per completed five-minute feature bar and current position quantity. Requests run on a separate thread. Responses expire 120 seconds after the packet's observation time and must match the position quantity. The execution loop continues checking risk while the model works. No order is based on a partial minute, stale quote or late response.

The news collector must have succeeded within ten minutes. Only revisions actually first observed by the packet timestamp are included; future revisions cannot leak into earlier decisions. The last four hours of locally collected headlines are eligible, capped at eight. Sparse/truncated coverage remains visible, and the seed calendar requires primary-source re-verification. This is not continuous worldwide news coverage.

Subscription mode persists each attempt before invocation, with a maximum of 80 per New York calendar date, including preflight/failed requests. A completed-bar/position slot is never retried automatically. It records reported token usage in `ai_subscription_usage.json`; the request cap is not a token or monetary cap. This workload shares the user's plan limits and may exhaust them. Packet size is capped at 20,000 bytes. No automatic purchase or API fallback is configured. The official client manages its own authentication and transport.

The optional, currently unselected Responses API backend requires an explicit API key and positive spending budget. It reserves a conservative estimated cost before sending, retains reservations after ambiguous failures, and caps output at 1,500 tokens. Its initial configured rates are $2.50 per million input tokens (cache-write ceiling) and $10 per million output tokens, checked November 4. These API rates do not price subscription usage. A local estimate is not a provider billing guarantee.

Optional API costs are recorded in `ai_budget.json` and are **not included in broker-fill or trading-cost-stress returns**. Subscription costs/credits are likewise not allocated into trading returns. Reports disclose this; do not call those returns fully net of research costs.

## Activation procedure

1. Verify the selected subscription CLI's login with `codex login status`. This deployment uses `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`; the unrelated npm CLI on PATH is broken and is not used. Do not copy or expose authentication tokens. API mode instead requires a separately authorized key and spending cap.
2. Select the backend and enable the configuration. Run `.venv/bin/python -m cash_cow.paper check-model --config paper_ai_v1` for a bounded schema/abstention check counted against the same local request limit. It cannot place a broker order. Activation requires its successful fingerprint to match configuration and AI source. Retain the previous ORB state untouched. Failed checks are retained; a changed fingerprint permits a new explicit preflight, never an automatic retry.
3. Verify the broker has no positions or open orders. Request `python -m cash_cow.paper stop` for the old runner and wait for its `stopped` event. Preserve its journal. Unload the old LaunchAgent only after verifying flat.
4. Back up the previous plist locally, then install the selected version with `.venv/bin/python scripts/paper_service.py install --config paper_ai_v1`. The installer refuses to overwrite an existing plist; remove only the verified-stopped backed-up definition. Only one version may own the shared Alpaca account. Both a shared telemetry lock and the legacy runner's lock protect the transition.
5. Verify fresh AI-service, news and sleep-prevention status. Capture the first real model packet/response and broker execution outcome separately. Do not label fixture tests as an end-to-end model test.

The service uses `caffeinate -i` so the display can sleep while automatic idle system sleep is prevented. Keep the machine powered, online and lid open; this does not prevent forced sleep, shutdown, lid sleep or loss of connectivity.

Commands select the experiment explicitly:

```sh
.venv/bin/python -m cash_cow.paper status --config paper_ai_v1
.venv/bin/python -m cash_cow.paper report --config paper_ai_v1
.venv/bin/python -m cash_cow.paper stop --config paper_ai_v1
```

Private evidence lives in `data/telemetry/paper_ai_v1/`: order/fill journal, `ai_decisions/` packets and responses, `ai_budget.json`, news revisions and session reports. Prompt/config/source changes require a new trial version and controlled deployment. Preserve failed proposals, missed sessions and losing trades. A losing or winning day alone does not justify changing the prompt.

## Validation and limits

Before activation, freeze the prompt, configuration, model identifier and source hashes for the first 20 scheduled exchange sessions after cutover. Retain every scheduled session, including operational failures; do not replace missed or losing days to improve the sample. Report complete-attendance coverage separately. Compare observed sleeve returns with cash and a separately labelled same-session SPY open-to-close reference using the same allocation and declared cost stress. Record broker paper fills, max($0.40, $0.0035/share) plus 2bp per-order stress, API cost reservations, turnover, drawdown, proposal failures and missed coverage separately. Missing benchmark data stays unavailable. No parameter changes based on interim returns; material correctness fixes require a recorded version change. Twenty sessions are an operational pilot, not evidence of a reliable edge or a live-deployment criterion. The historical holdout remains untouched.

Offline tests cover malformed actions/citations, confidence values, structured output, refusals, persistent cost reservations, budget exhaustion, ambiguous-call retry prevention, first-seen news handling, expired responses, HOLD overriding the old quantitative BUY, and risk/time exits while AI is unavailable. These establish implementation behavior under fixtures, not profitable performance or model access.

The preceding US session had no orders because the Mac slept and triggered a monitoring-gap block. Preserve it as an operational incident. The corrected report labels blocked sessions explicitly and retains their actual sleeve returns, including losses; it does not erase bad days or imply a complete strategy evaluation.

Official references: [Codex subscription authentication](https://learn.chatgpt.com/docs/auth), [Non-interactive mode and structured output](https://learn.chatgpt.com/docs/non-interactive-mode), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [GPT-6.1 Sol capabilities and pricing](https://developers.openai.com/api/docs/models/gpt-6.1-sol).
