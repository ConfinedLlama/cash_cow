"""Read-only daily engineering report with explicitly sourced performance data.

Never connects to a broker, sends an order, changes a strategy or commits files.
Session NAV must already include trading costs. External cash flows are rejected
until an independently reconciled time-weighted return implementation exists.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

SGT = ZoneInfo("Asia/Singapore")
ROOT = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def commits_for_day(root: Path, day: date) -> list[dict]:
    """Filter actual committer timestamps in SGT; do not assume Git date order."""
    output = git(root, "log", "--first-parent", "--format=%H%x1f%cI%x1f%s")
    commits = []
    for line in output.splitlines():
        sha, timestamp, subject = line.split("\x1f", 2)
        if datetime.fromisoformat(timestamp).astimezone(SGT).date() == day:
            commits.append({"sha": sha, "subject": subject, "timestamp": timestamp})
    return list(reversed(commits))


def load_coverage(state_path: Path | None, data: dict) -> dict:
    """Join the runner's cost-stress export to state without dropping bad days.

    This is local evidence matching, not an exchange-calendar or broker audit.
    Raw block reasons and account fields are never returned.
    """
    rows = data['sessions']
    result = {'state_sha256': None, 'sessions': [], 'counts': {}}
    state = None
    if state_path is not None:
        if data['mode'] != 'paper' or not data['strategy_id'].endswith('_cost_stress'):
            raise ValueError('Coverage state supports the paper cost-stress export only')
        raw = state_path.read_bytes()
        state = json.loads(raw)
        if not isinstance(state, dict) or not isinstance(state.get('sessions'), dict):
            raise ValueError('Invalid coverage state')
        result['state_sha256'] = hashlib.sha256(raw).hexdigest()
    for row in rows:
        status = 'unverified'
        if state is not None:
            entry = state['sessions'].get(row['session_date'])
            if not isinstance(entry, dict):
                raise ValueError('Export session missing from coverage state')
            for exported, stored in [('opening_nav', 'opening_stress_nav'),
                                     ('closing_nav', 'closing_stress_nav'),
                                     ('fees', 'modeled_costs')]:
                value = entry.get(stored)
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                        or not math.isclose(row[exported], value, rel_tol=0, abs_tol=1e-6)):
                    raise ValueError('Export and coverage NAV/cost evidence disagree; retry or reconcile')
            closed, partial = entry.get('closed'), entry.get('partial_attendance')
            unresolved = entry.get('unresolved_at_close', False)
            blocked = entry.get('blocked')
            if (not isinstance(closed, bool) or not isinstance(partial, bool)
                    or not isinstance(unresolved, bool) or 'blocked' not in entry
                    or (blocked is not None and not isinstance(blocked, str))):
                raise ValueError('Invalid coverage flags')
            status = ('incomplete' if not closed or partial or unresolved or blocked
                      else 'no_local_block_recorded')
        result['sessions'].append({'session_date': row['session_date'], 'coverage': status})
        result['counts'][status] = result['counts'].get(status, 0) + 1
    return result


def load_performance(path: Path, report_day: date, coverage_state: Path | None = None) -> dict:
    """One mode and frozen strategy per file; gaps are visible, never filled."""
    raw = path.read_bytes()
    data = json.loads(raw)
    if data.get("mode") not in {"paper", "live"}:
        raise ValueError("Telemetry mode must be paper or live")
    strategy = data.get("strategy_id", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", strategy):
        raise ValueError("A safe, versioned strategy_id is required")
    rows = data.get("sessions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("At least one reconciled session is required")
    previous_day = None
    previous_nav = None
    equity = []
    returns = []
    monthly = {}
    fees = 0.0
    for row in rows:
        session = date.fromisoformat(row["session_date"])
        if session > report_day or (previous_day is not None and session <= previous_day):
            raise ValueError("Sessions must be unique, increasing and not future-dated")
        fields = ["opening_nav", "closing_nav", "external_flow", "fees"]
        for field in fields:
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid finite numeric field: {field}")
        opening, closing = row["opening_nav"], row["closing_nav"]
        if opening <= 0 or closing <= 0 or row["fees"] < 0:
            raise ValueError("NAV must be positive and fees nonnegative")
        if row["external_flow"] != 0:
            raise ValueError("External cash flows require separate return reconciliation")
        if previous_nav is not None and not math.isclose(opening, previous_nav, rel_tol=0, abs_tol=1e-6):
            raise ValueError("NAV continuity failed; reconcile missing sessions or cash movements")
        if not equity:
            equity.append(opening)
        equity.append(closing)
        ret = closing / opening - 1
        returns.append(ret)
        month = session.strftime("%Y-%m")
        monthly[month] = monthly.get(month, 1.0) * (1 + ret)
        fees += row["fees"]
        previous_day, previous_nav = session, closing
    monthly = {month: value - 1 for month, value in monthly.items()}
    peak = equity[0]
    drawdown = 0.0
    for nav in equity:
        peak = max(peak, nav)
        drawdown = min(drawdown, nav / peak - 1)
    return {
        "mode": data["mode"], "strategy_id": strategy,
        "sha256": hashlib.sha256(raw).hexdigest(), "sessions": len(rows),
        "first_session": rows[0]["session_date"], "last_session": rows[-1]["session_date"],
        "last_session_return": returns[-1], "observed_return": equity[-1] / equity[0] - 1,
        "observed_net_pnl": equity[-1] - equity[0], "session_close_drawdown": drawdown,
        "fees_already_in_nav": fees, "observed_monthly_returns": monthly,
        "cost_basis": data.get("cost_basis"),
        "coverage": load_coverage(coverage_state, data),
    }


def research_status(root: Path) -> list[str]:
    lines = []
    for version in ("V3", "V3B", "V4"):
        pointer = root / "reports" / f"LATEST_{version}.txt"
        if not pointer.exists():
            lines.append(f"- {version}: no completed run pointer.")
            continue
        relative = pointer.read_text().strip()
        folder = (root / relative).resolve()
        if not folder.is_relative_to((root / "reports/runs").resolve()):
            raise ValueError("Run pointer escapes reports/runs")
        verification = folder / "VERIFICATION.json"
        if not verification.exists():
            lines.append(f"- {version}: pointer exists, verification missing; not validated.")
            continue
        result = json.loads(verification.read_text())
        if result.get("status") != "passed":
            lines.append(f"- {version}: recorded verification did not pass.")
            continue
        count = result.get("runs", "unspecified")
        lines += [f"- {version}: {count} historical simulations; recorded accounting verification passed.",
                  f"  Source: `{relative}/VERIFICATION.json`."]
    return lines


def load_trial_coverage(calendar_path, state_path, performance, now=None):
    """Join the frozen paper trial calendar without inventing accounting rows."""
    from .paper.attendance import audit, calendar_sessions
    now = now or datetime.now(SGT)
    if (performance['mode'] != 'paper' or performance['strategy_id'] != 'paper_ai_v1_cost_stress'
            or state_path.name != 'state.json' or not performance['coverage']['state_sha256']):
        raise ValueError('Trial calendar requires matching paper_ai_v1 cost-stress state')
    raw = calendar_path.read_bytes()
    calendar = json.loads(raw)
    expected = calendar_sessions(calendar, '2026-11-04', 20, now)
    result = audit(state_path.parent, calendar, '2026-11-04', 20, now)
    if (result['state_sha256'] != performance['coverage']['state_sha256']
            or any(issue != 'elapsed_sessions_require_review' for issue in result['issues'])):
        raise ValueError('Trial coverage evidence changed or is unverifiable; retry or reconcile')
    exported = {row['session_date'] for row in performance['coverage']['sessions']}
    elapsed = {day for day, _, closed in expected if closed <= now}
    if not exported <= elapsed:
        raise ValueError('Accounting export includes an unclosed or out-of-trial session')
    return {'as_of': result['as_of'], 'calendar_sha256': hashlib.sha256(raw).hexdigest(),
            'elapsed_sessions': result['elapsed_sessions'], 'planned_sessions': result['planned_sessions'],
            'sessions': [{'date': row['date'], 'status': row['status'],
                          'accounting_export': 'present' if row['date'] in exported else 'unavailable'}
                         for row in result['sessions'] if row['date'] in elapsed],
            'pending_sessions': [{'date': day, 'calendar_status': 'scheduled' if now < opened else 'in_progress',
                                  'open': opened.isoformat(), 'close': closed.isoformat()}
                                 for day, opened, closed in expected if closed > now],
            'missing_accounting_dates': sorted(elapsed-exported)}


def render_report(root: Path, day: date, performance: dict | None = None, trial: dict | None = None) -> str:
    commits = commits_for_day(root, day)
    lines = [f"# Daily report - {day.isoformat()} (Asia/Singapore)", "",
             f"Snapshot HEAD: `{git(root, 'rev-parse', 'HEAD')}`.", "",
             "## Commits present when this report was generated", ""]
    for commit in commits:
        subject = commit["subject"].replace("[", "\\[").replace("]", "\\]")
        lines.append(f"- [`{commit['sha'][:7]}`](https://github.com/ConfinedLlama/cash_cow/commit/{commit['sha']}) - {subject}")
    if not commits:
        lines.append("No commits for this Singapore calendar day at generation time.")
    lines += ["", "The final report commit cannot contain its own hash.",
              "Its scope is documented below; the daily chat summary includes its hash and push verification.",
              "", "## Performance evidence", ""]
    if trial is not None:
        lines += [f"Frozen trial: {trial['elapsed_sessions']} elapsed of {trial['planned_sessions']} scheduled sessions.",
                  f"Calendar audit as of: `{trial['as_of']}`; source SHA-256: `{trial['calendar_sha256']}`.", "",
                  "| Trial session | Attendance | Accounting export |", "|---|---|---|"]
        lines += [f"| {r['date']} | {r['status']} | {r['accounting_export']} |" for r in trial['sessions']]
        missing = ', '.join(trial['missing_accounting_dates']) or 'none'
        lines += ["", f"Elapsed sessions without an accounting close: {missing}.",
                  "Missing accounting returns are unavailable, never assumed zero.",
                  "Attendance does not certify broker reconciliation, market-data coverage or full-month performance.", ""]
        if trial.get('pending_sessions'):
            lines += ["### Open and upcoming calendar sessions", "",
                      "These are exchange-calendar states, not proof of a running service or observed trading.",
                      "Unclosed sessions have no final return and are excluded from elapsed-session counts.", "",
                      "| Trial session | Calendar status | Opens (UTC offset shown) | Closes (UTC offset shown) |",
                      "|---|---|---|---|"]
            lines += [f"| {r['date']} | {r['calendar_status']} | {r['open']} | {r['close']} |"
                      for r in trial['pending_sessions']]
            lines.append("")
    if performance is None:
        lines += ["No paper/live session telemetry was supplied.",
                  "Daily P&L, fills, slippage and drawdown are unavailable; historical results are not today's trading results."]
    else:
        p = performance
        lines += [f"Mode: **{p['mode']}**; strategy: `{p['strategy_id']}`; source SHA-256: `{p['sha256']}`.", "",
                  f"Observed sessions: {p['sessions']} ({p['first_session']} through {p['last_session']}).",
                  "Freshness and exchange-session coverage require review.", "",
                  f"- Last observed session return: {p['last_session_return']:.3%}",
                  f"- Observed compounded accounting return: {p['observed_return']:.3%}",
                  f"- Observed net P&L: {p['observed_net_pnl']:.2f} account currency units",
                  f"- Session-close drawdown: {p['session_close_drawdown']:.3%} (not intraday drawdown)",
                  f"- {'Modeled costs' if p.get('cost_basis') else 'Fees'} already deducted from NAV: {p['fees_already_in_nav']:.2f}", "",
                  "Observed monthly segments below may be partial; they are not estimates of full-month returns or a monthly performance average.", ""]
        lines += [f"- {month}: {value:.3%}" for month, value in p["observed_monthly_returns"].items()]
        coverage = p.get('coverage')
        lines += ["", "### Session coverage", "",
                  "Accounting returns retain incomplete days and losses.",
                  "They are not evidence of complete strategy evaluation.", ""]
        if coverage and coverage['state_sha256']:
            lines += [f"Coverage state SHA-256: `{coverage['state_sha256']}`.", "",
                      "| Session | Local coverage |", "|---|---|"]
            lines += [f"| {r['session_date']} | {r['coverage']} |" for r in coverage['sessions']]
        else:
            lines.append("Coverage state not supplied: every observed session is **unverified**.")
        lines += ["", "No local block recorded is not verified complete attendance.",
                  "Independently check exchange sessions, event gaps, data coverage, account/strategy identity and broker reconciliation.",
                  "Full-month statistics remain unavailable without that evidence."]
        if p.get("cost_basis"):
            lines += ["", f"Cost basis supplied with telemetry: {p['cost_basis']}"]
        lines += ["", "Input consistency was checked, but broker reconciliation and source authenticity must be verified separately."]
    lines += ["", "## Historical research status", "", *research_status(root), "",
              "Recorded historical checks are not fresh reruns or evidence of a live trading edge.", "",
              "## Engineering review - complete before committing", "",
              "- Changes and rationale: PENDING", "- Tests and experiments actually run: PENDING",
              "- Rejected hypotheses and limitations: PENDING", "- Blockers and next step: PENDING",
              "- Final report commit scope and daily commit target: PENDING", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(SGT).date())
    parser.add_argument("--observations", type=Path, help="Private reconciled paper/live session JSON")
    parser.add_argument("--coverage-state", type=Path, help="Private matching state.json for paper cost-stress observations")
    parser.add_argument('--trial-calendar', type=Path, help='Independent calendar for the frozen paper_ai_v1 twenty-session trial')
    args = parser.parse_args()
    if args.date > datetime.now(SGT).date():
        parser.error("Cannot generate future daily reports")
    if args.coverage_state and not args.observations:
        parser.error('--coverage-state requires --observations')
    if args.trial_calendar and (not args.coverage_state or args.date != datetime.now(SGT).date()):
        parser.error('--trial-calendar requires --coverage-state and the current Singapore report date')
    performance = load_performance(args.observations, args.date, args.coverage_state) if args.observations else None
    trial = load_trial_coverage(args.trial_calendar, args.coverage_state, performance) if args.trial_calendar else None
    report = render_report(ROOT, args.date, performance, trial)
    target = ROOT / "reports/daily" / f"{args.date.isoformat()}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x") as stream:
        stream.write(report)
    print(target)


if __name__ == "__main__":
    main()
