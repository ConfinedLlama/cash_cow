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


def load_performance(path: Path, report_day: date) -> dict:
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
        lines.append(f"- {version}: {count} historical simulations; recorded accounting verification passed. Source: `{relative}/VERIFICATION.json`.")
    return lines


def render_report(root: Path, day: date, performance: dict | None = None) -> str:
    commits = commits_for_day(root, day)
    lines = [f"# Daily report — {day.isoformat()} (Asia/Singapore)", "",
             f"Snapshot HEAD: `{git(root, 'rev-parse', 'HEAD')}`.", "",
             "## Commits present when this report was generated", ""]
    for commit in commits:
        subject = commit["subject"].replace("[", "\\[").replace("]", "\\]")
        lines.append(f"- [`{commit['sha'][:7]}`](https://github.com/ConfinedLlama/cash_cow/commit/{commit['sha']}) — {subject}")
    if not commits:
        lines.append("No commits for this Singapore calendar day at generation time.")
    lines += ["", "The final report commit cannot contain its own hash. Its scope is documented below; the daily chat summary includes its hash and push verification.",
              "", "## Performance evidence", ""]
    if performance is None:
        lines += ["No paper/live session telemetry was supplied. Daily P&L, fills, slippage and drawdown are unavailable; historical results are not today's trading results."]
    else:
        p = performance
        lines += [f"Mode: **{p['mode']}**; strategy: `{p['strategy_id']}`; source SHA-256: `{p['sha256']}`.", "",
                  f"Observed sessions: {p['sessions']} ({p['first_session']} through {p['last_session']}). Freshness and exchange-session coverage require review.", "",
                  f"- Last observed session return: {p['last_session_return']:.3%}",
                  f"- Observed compounded return: {p['observed_return']:.3%}",
                  f"- Observed net P&L: {p['observed_net_pnl']:.2f} account currency units",
                  f"- Session-close drawdown: {p['session_close_drawdown']:.3%} (not intraday drawdown)",
                  f"- Fees already deducted from NAV: {p['fees_already_in_nav']:.2f}", "",
                  "Observed monthly segments below may be partial; they are not estimates of full-month returns or a monthly performance average.", ""]
        lines += [f"- {month}: {value:.3%}" for month, value in p["observed_monthly_returns"].items()]
        lines += ["", "Input consistency was checked, but broker reconciliation and source authenticity must be verified separately."]
    lines += ["", "## Historical research status", "", *research_status(root), "",
              "Recorded historical checks are not fresh reruns or evidence of a live trading edge.", "",
              "## Engineering review — complete before committing", "",
              "- Changes and rationale: PENDING", "- Tests and experiments actually run: PENDING",
              "- Rejected hypotheses and limitations: PENDING", "- Blockers and next step: PENDING",
              "- Final report commit scope and daily commit target: PENDING", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(SGT).date())
    parser.add_argument("--observations", type=Path, help="Private reconciled paper/live session JSON")
    args = parser.parse_args()
    if args.date > datetime.now(SGT).date():
        parser.error("Cannot generate future daily reports")
    performance = load_performance(args.observations, args.date) if args.observations else None
    report = render_report(ROOT, args.date, performance)
    target = ROOT / "reports/daily" / f"{args.date.isoformat()}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x") as stream:
        stream.write(report)
    print(target)


if __name__ == "__main__":
    main()
