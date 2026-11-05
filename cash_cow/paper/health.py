"""Read-only local telemetry audit. Never calls a broker, model or service manager.

Run: python -m cash_cow.paper.health --config paper_ai_v1
Exit 2 means an operational issue requires review, not a command to reset state.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .client import timestamp
from .runner import TERMINAL


def age_seconds(value, now):
    try:
        return (now - timestamp(value)).total_seconds()
    except (TypeError, ValueError, AttributeError):
        return None


def audit(directory, now=None):
    """Return sanitized aggregates; source hashes identify each read, not a transaction."""
    directory = Path(directory)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Audit time must include timezone")
    issues, hashes = [], {}

    def read(name, optional=False):
        path = directory / name
        if optional and not path.exists():
            return {}
        try:
            raw = path.read_bytes()
            hashes[name] = hashlib.sha256(raw).hexdigest()
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("Expected object")
            return value
        except (OSError, ValueError):
            issues.append("unreadable:" + name)
            return {}

    state = read("state.json")
    news = read("news/status.json")
    last = state.get("last_event", {})
    age = age_seconds(last.get("at"), now)
    if age is None or age < 0 or age > 120:
        issues.append("runner_heartbeat_missing_stale_or_future")
    if last.get("kind") == "needs_attention":
        issues.append("runner_needs_attention")
    if state.get("halt"):
        issues.append("runner_halted")
    if (directory / "STOP").exists():
        issues.append("stop_requested")
    news_age = age_seconds(news.get("last_success"), now)
    news_fresh = news_age is not None and 0 <= news_age <= 600 and not news.get("error")
    if not news_fresh:
        issues.append("news_unavailable")
    if news.get("truncated"):
        issues.append("news_window_truncated")
    # The last saved gap flag cannot establish present coverage after an outage.
    news_gap = news_age is None or news_age < 0 or news_age > 900 or bool(news.get("coverage_gap"))
    if news_gap:
        issues.append("news_coverage_gap")

    events, malformed = [], 0
    try:
        raw = (directory / "events.jsonl").read_bytes()
        hashes["events.jsonl"] = hashlib.sha256(raw).hexdigest()
        for line in raw.splitlines():
            try:
                event = json.loads(line)
                at = timestamp(event["at"])
                if not isinstance(event["kind"], str) or at > now:
                    raise ValueError("Invalid event")
                events.append((at, event["kind"]))
            except (ValueError, KeyError, TypeError, AttributeError):
                malformed += 1
    except OSError:
        issues.append("unreadable:events.jsonl")
    if malformed:
        issues.append("malformed_or_future_events")
    if any(a[0] > b[0] for a, b in zip(events, events[1:])):
        issues.append("nonmonotonic_event_times")
    events.sort(key=lambda row: row[0])

    sessions = {}
    for day, session in state.get("sessions", {}).items():
        try:
            opened, closed = timestamp(session["open"]), timestamp(session["close"])
            if closed <= opened or opened > now:
                raise ValueError("Invalid session interval")
            end = min(closed, now)
            times = [opened] + [at for at, _ in events if opened <= at <= end] + [end]
            gaps = [(b-a).total_seconds() for a,b in zip(times,times[1:])]
            blocked = bool(session.get("blocked"))
            sessions[day] = {
                "blocked": blocked, "partial_attendance": bool(session.get("partial_attendance")),
                "closed": bool(session.get("closed")),
                "unresolved_at_close": bool(session.get("unresolved_at_close")),
                "max_event_gap_seconds": max(gaps, default=0),
                "event_gaps_over_120_seconds": sum(g > 120 for g in gaps),
                "events": dict(Counter(kind for at,kind in events if opened <= at <= end)),
            }
            if blocked or session.get("partial_attendance") or session.get("unresolved_at_close") or any(g > 120 for g in gaps):
                issues.append("session_requires_coverage_review:" + day)
        except (ValueError, KeyError, TypeError, AttributeError):
            issues.append("invalid_session_interval:" + day)
    orders = state.get("orders", {})
    pending = sum(o.get("broker", {}).get("status") not in TERMINAL for o in orders.values())
    if pending:
        issues.append("nonterminal_order_intents")
    usage = read("ai_subscription_usage.json", optional=True)
    usage_counts = {day: dict(Counter(v.get("status", "unknown") for v in attempts.values()))
                    for day,attempts in usage.items()}
    return {"as_of": now.isoformat(), "status": "review_required" if issues else "no_local_issue_detected",
            "issues": issues, "heartbeat_age_seconds": age, "last_event_kind": last.get("kind"),
            "news_age_seconds": news_age, "news_fresh": news_fresh, "news_coverage_gap_now": news_gap,
            "order_intents": len(orders), "nonterminal_order_intents": pending,
            "sessions": sessions, "subscription_attempts": usage_counts,
            "malformed_or_future_events": malformed, "source_sha256": hashes,
            "limits": "Local files only; broker reconciliation, process ownership and power assertions require separate checks. Event density is not successful market-data or signal coverage. Files are read separately while the service may write."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", choices=("paper_v1", "paper_ai_v1"), default="paper_ai_v1")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = audit(root / "data/telemetry" / args.config)
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result["issues"] else 0)


if __name__ == "__main__":
    main()
