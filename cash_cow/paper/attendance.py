"""Audit a fixed trial against a supplied exchange calendar, without trading.

The calendar snapshot must come from a separately verified read-only calendar
request. This command neither fetches prices nor fills missing sessions with 0%.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .client import timestamp
from .health import audit as health_audit, valid_day

NY = ZoneInfo('America/New_York')


def calendar_sessions(snapshot, start, count, now):
    if not valid_day(start) or isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 252:
        raise ValueError('Invalid trial start or session count')
    try:
        if not valid_day(snapshot['start']) or not valid_day(snapshot['end']):
            raise ValueError()
        if not snapshot['start'] <= start <= snapshot['end'] or timestamp(snapshot['fetched_at']) > now:
            raise ValueError()
        if snapshot['source'] != 'Alpaca GET /v2/calendar' or not isinstance(snapshot['sessions'], list):
            raise ValueError()
        rows, previous = [], None
        for row in snapshot['sessions']:
            day = row['date']
            if not valid_day(day) or not snapshot['start'] <= day <= snapshot['end'] or (previous and day <= previous):
                raise ValueError()
            opened = datetime.fromisoformat(day+'T'+row['open'])
            closed = datetime.fromisoformat(day+'T'+row['close'])
            if opened.tzinfo or closed.tzinfo or not opened < closed:
                raise ValueError()
            previous = day
            if day >= start:
                rows.append((day, opened.replace(tzinfo=NY), closed.replace(tzinfo=NY)))
        if len(rows) < count:
            raise ValueError()
        return rows[:count]
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError('Calendar snapshot invalid, future-dated, or shorter than the fixed trial') from None


def audit(directory, snapshot, start, count=20, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Audit time must include timezone')
    expected = calendar_sessions(snapshot, start, count, now)
    directory = Path(directory)
    health = health_audit(directory, now)
    issues, state_hash = [], None
    try:
        raw = (directory/'state.json').read_bytes()
        state_hash = hashlib.sha256(raw).hexdigest()
        state = json.loads(raw)
        sessions = state['sessions']
        if not isinstance(sessions, dict):
            raise ValueError()
        if state_hash != health['source_sha256'].get('state.json'):
            issues.append('state_changed_during_audit')
    except (OSError, ValueError, KeyError, TypeError):
        sessions = {}
        issues.append('unreadable_session_state')
    invalid_events = any(issue in health['issues'] for issue in (
        'unreadable:events.jsonl', 'malformed_or_future_events',
        'nonmonotonic_event_times', 'unknown_event_kind',
    ))
    if invalid_events:
        issues.append('event_evidence_requires_review')
    rows = []
    for day, opened, closed in expected:
        reasons = []
        if now < opened:
            status = 'scheduled'
        elif now < closed:
            status = 'in_progress'
        elif issues:
            status = 'unverifiable'
        elif day not in sessions:
            status = 'missing'
        else:
            local = health['sessions'].get(day)
            session = sessions[day]
            try:
                if timestamp(session['open']) != opened or timestamp(session['close']) != closed:
                    reasons.append('calendar_interval_mismatch')
                if not local:
                    reasons.append('invalid_local_session')
                else:
                    for flag in ('blocked', 'partial_attendance', 'unresolved_at_close'):
                        if local[flag]:
                            reasons.append(flag)
                    if not local['closed']:
                        reasons.append('close_not_recorded')
                    if local['event_gaps_over_120_seconds']:
                        reasons.append('event_gaps')
                    if local['events'].get('needs_attention'):
                        reasons.append('operational_errors')
            except (KeyError, TypeError, ValueError, AttributeError):
                reasons.append('invalid_local_session')
            status = 'incomplete' if reasons else 'no_local_attendance_issue'
        rows.append({'date': day, 'status': status, 'reasons': reasons})
    counts = Counter(row['status'] for row in rows)
    elapsed = sum(now >= closed for _, _, closed in expected)
    if any(counts[k] for k in ('missing', 'incomplete', 'unverifiable')):
        issues.append('elapsed_sessions_require_review')
    return {
        'as_of': now.isoformat(), 'trial_start': start, 'planned_sessions': count,
        'trial_last_session': expected[-1][0], 'elapsed_sessions': elapsed,
        'status': 'review_required' if issues else 'no_local_attendance_issue',
        'issues': issues, 'counts': dict(counts), 'sessions': rows,
        'calendar_observed_at': snapshot['fetched_at'],
        'calendar_sha256': hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
        'state_sha256': state_hash, 'health_source_sha256': health['source_sha256'],
        'limits': 'Calendar completeness/authenticity requires independent verification. Local attendance is not successful data coverage, broker reconciliation or strategy performance. In-progress/future sessions are not completed samples. No returns are inferred; missing and blocked sessions stay in the fixed denominator. Files are read separately; retry concurrent changes.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calendar', type=Path, required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--sessions', type=int, default=20)
    parser.add_argument('--config', choices=('paper_ai_v1', 'paper_v1'), default='paper_ai_v1')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        snapshot = json.loads(args.calendar.read_bytes())
        result = audit(root/'data/telemetry'/args.config, snapshot, args.start, args.sessions)
    except (OSError, ValueError, TypeError):
        print(json.dumps({'status': 'review_required', 'issues': ['invalid_or_unreadable_calendar_or_arguments']}))
        raise SystemExit(2)
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result['issues'] else 0)


if __name__ == '__main__':
    main()
