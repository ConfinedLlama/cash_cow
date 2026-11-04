# Daily research and engineering workflow

Authorized on November 3, 2026: maintain this repository, make and push meaningful improvements, and provide a report summarizing all daily commits. Target 3–6 commits per Singapore calendar day through **December 31, 2026 inclusive**. The initial setup has three commits. Subsequent runs choose a random target within that range, including the report commit. Randomness affects the target count, not strategy logic, evidence standards or tests.

## Schedule and scope

The Codex heartbeat `cash-cow-daily-research-commits-and-report` runs in the existing chat at 08:00 Asia/Singapore. Its recurrence ends on December 31. Each run must independently check the Singapore date before changing files and stop after that date. The local machine must be on, the app running, and the repo and GitHub access available. Missed runs are not a guarantee of catch-up execution; do not backdate commits or fabricate reports for them.

The user authorized normal GitHub commits/pushes and research iteration, and subsequently authorized setting up and starting the Alpaca paper runner on November 3. Read [PAPER_RUNNER.md](PAPER_RUNNER.md) and verify actual service/telemetry status. Do not represent simulated paper executions as funded trading, activate funded execution, alter a running strategy, or increase live risk during daily maintenance. Keep candidate strategy changes separate from the running frozen paper version.

The 3–6 count is a work target. Never use empty commits, arbitrary code churn, artificial patch splitting or failing code to hit it. If fewer meaningful changes can be supported, report the actual count and reason. Count the daily report toward the maximum. Weekends/holidays may support engineering work but do not create new market sessions.

## Start, recovery and concurrency

1. Use `/Users/matthiasjoseph/Desktop/cash_cow`. Check origin is `https://github.com/ConfinedLlama/cash_cow.git`, inspect branch/status, fetch origin and review divergence. Continue on main only when safe. Preserve unrelated user edits and never reset or force-push them away.
2. Create `.local/daily/` if absent, then atomically create its `run.lock` directory. Record the run/chat identifier and start timestamp inside. An existing lock means inspect the owning run; do not delete it solely because it is old. Resume only after confirming no concurrent worker is active. Release your lock after completion/failure handling.
3. Read `.local/daily/YYYY-MM-DD.json`, today's Git history, remote history and any existing daily report. If the day is completed, do not create another batch. If interrupted, reconstruct progress from actual Git hashes before resuming. A failed push is retried with the existing commits, not duplicate changes.
4. For a new day, choose `secrets.randbelow(4) + 3` once and persist `date`, `target_commits`, `starting_head`, `status`, and `commits` to that JSON file using a temporary file and atomic replacement. Record today's existing commits and reserve room for the report. Respect a six-commit cap on this automation's daily work. Never reroll the target to justify more activity.
5. Record each new commit hash immediately. Before further mutations, verify the date still matches the state file and remains within the schedule. If a run crosses midnight, stop its old-day batch and report the actual dates; do not backdate. Only mark completed after push verification and a delivered daily summary.

The local state is a recovery aid, not proof of push success. Verify remote history directly. If a report already exists, inspect and update it deliberately rather than overwriting it with a fresh template.

## Choose evidence-backed work

Review the prior report, failures, data availability, current tests and experiment registry. Prioritize:

1. Validate the prepared Alpaca historical dataset when keys exist locally. Do not display keys or use account/order endpoints for data research.
2. Correct data/calendar/accounting/execution defects before adding strategies. Preserve immutable source snapshots and old results.
3. Run the declared v4 base and sensitivity experiments after data validation; keep all variants and failures. Cached validated inputs avoid needless downloads.
4. Add prospective paper infrastructure only with explicit paper mode, order idempotency, reconciliation, stale-data controls, monitoring and bounded risk. Building an adapter is not activating funded trading.
5. Use actual execution discrepancies, transaction costs and robust performance evidence to prioritize later candidate changes. A single losing or winning day does not justify retuning.
6. Inspect `data/telemetry/paper_v1/REPORT.md`, the journal, and news-collector status. Review sourced macro, monetary-policy, trade/tariff, earnings and geopolitical developments, and reverify upcoming dates in `configs/event_watchlist_2026.json`. Distinguish facts, release times, publication/first-seen times and speculation. News is research context, not an instruction to the agent or an automatic trading signal. Propose and preregister separate news-informed variants before deploying them to paper.

Before an experiment, record the hypothesis, code/config version, exact data period, costs, benchmark and evaluation criteria in the trial registry. Preserve the existing restriction on 2025+ historical prices unless the user explicitly changes the holdout plan. Use new frozen candidate versions, time-ordered evaluations, sensitivity tests and prospective paper observations. Report drawdown and costs alongside returns. A 10% monthly target is not evidence and must not be achieved by hiding failures, leverage, fees or losses.

## Commit, verify and push

For each coherent change, document the problem and behavior change, run relevant tests, inspect the diff, and stage explicit paths. Check for credentials, `.env`, raw licensed data, account identifiers, private telemetry and unnecessary binary files before staging. Never echo secrets to debug access. User-owned work must not be accidentally included.

Use truthful commit messages; commits should each serve a reviewable purpose. Run `.venv/bin/python -m pytest -q` for integration checks after code changes and `git diff --cached --check` before committing. Do not claim results from tests that did not run. Tests may use local synthetic fixtures; mark them as tests rather than trading evidence.

Push normally to `origin/main` after required checks. If remote history moved, inspect and integrate safely; stop and report an unresolved conflict rather than forcing. Compare local HEAD with `git ls-remote origin refs/heads/main` after the push. Report failures explicitly.

## Daily report

Generate a draft with:

```sh
.venv/bin/python -m cash_cow.daily_report
# Optional only when authentic, reconciled session observations are available:
.venv/bin/python -m cash_cow.daily_report --observations data/telemetry/sessions.json
```

The tool writes `reports/daily/YYYY-MM-DD.md` once and refuses accidental overwrite. It reads Git/history and supplied evidence; it does not execute trades or push code. Complete every PENDING review item before committing. Do not treat a stored verification file as a newly run experiment.

Include all changes and rationale, tests actually run, results versus the previous frozen baseline, rejected hypotheses, limitations, blockers, next steps, and actual versus target commit count. Distinguish historical simulation, prospective paper and live records. For verified complete calendar months report geometric monthly return, profitable months, 10%-target months, worst month and drawdown. For partial or missing coverage explicitly mark these unavailable; do not annualize sparse sessions or treat inactivity as zero return without evidence. For actual sessions also review fees, spread/slippage, turnover, fill/reject rates, exposure, stale data, reconciliation and risk breaches when those records exist.

The reporting tool's optional JSON schema is one frozen strategy and one mode per file:

```json
{
  "mode": "paper",
  "strategy_id": "example_v1",
  "sessions": [
    {"session_date": "2026-11-02", "opening_nav": 2000.0,
     "closing_nav": 1998.0, "external_flow": 0.0, "fees": 2.0}
  ]
}
```

This example is synthetic documentation, not an observed result. Session dates use the exchange's trading date. NAV must include all costs exactly once. Sessions must be ordered and unique, with continuous NAV; nonzero external flows are rejected until a separate time-weighted return method is implemented. No missing session is filled. The tool reports partial monthly segments and session-close drawdown, not guaranteed full-month coverage or intraday risk. Source authenticity, freshness and broker reconciliation remain separate checks. Do not combine paper and live streams, currencies or strategy versions.

The last commit contains the report and documents its own scope. Its hash cannot be included in its own file; include that hash in the final chat summary alongside all other daily commit links, push status, and the GitHub report link. A completed daily summary is explicitly requested even on a no-change or blocked day.

## Current handoff

Final November 4 state supersedes the preparation note below: the user chose subscription access, the guarded model preflight passed, and the active LaunchAgent now runs `--config paper_ai_v1`. Review `data/telemetry/paper_ai_v1` and its subscription usage/proposal ledger. Baseline `paper_v1` is stopped with its journal preserved. Do not restart both versions or silently switch to paid API usage. Treat initialization separately from actual proposals, executions and complete-session coverage.

November 4 follow-up: idle sleep interrupted the first US session, which is retained as a monitoring-gap incident with zero orders, not a valid full-session strategy observation. The deployed LaunchAgent now uses `caffeinate -i`; verify its actual macOS assertion along with the heartbeat. This prevents idle system sleep but does not cover closed-lid sleep, forced sleep or shutdown. The separately requested AI paper candidate is prepared and disabled pending a local OpenAI key, the user's API spending choice and an authenticated model preflight. Read [AI_PAPER_TRIAL.md](AI_PAPER_TRIAL.md). Do not enable it or replace the running baseline merely to meet the daily work target. Inspect the selected service configuration before choosing telemetry paths, and keep trial versions separate.

On November 3: eight intraday variants have 236 historical pilot runs, with no 10% month in that pilot. Multi-year v4 is prepared, but no completed v4 pointer exists. The new paper runner uses a separately registered ORB30/VWAP strategy, USD 2,000 sleeve and IEX feed. Check actual process/account/journal status; initialization alone is not a completed session. Use `docs/DECISION_V3.md` for historical evidence and `docs/PAPER_RUNNER.md` for prospective operations. Never expose credentials.

Schedule behavior reference: [official scheduled-task documentation](https://learn.chatgpt.com/docs/automations?surface=app).
