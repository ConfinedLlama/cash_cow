"""Combined read-only operational checks. Does not submit, restart or clear state."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from . import broker_audit, decision_audit, health, readiness
from .ai import require_model_preflight
from .client import PaperClient, timestamp

NY = ZoneInfo('America/New_York')


def local_allowance(decisions, config, now):
    """Local persisted request cap only; never claim provider subscription quota."""
    day = str(now.astimezone(NY).date())
    result = {'status': 'unverified', 'session_date': day, 'used': None,
              'limit': None, 'remaining': None}
    try:
        cfg = config['ai']; limit = cfg['daily_request_limit']
        if cfg['backend'] != 'codex_subscription' or isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 80:
            return result
        if decisions['status'] != 'integrity_checks_passed' or decisions['errors'] != {}:
            return result
        if not 0 <= (now-timestamp(decisions['as_of'])).total_seconds() <= 120:
            return result
        counts = decisions['subscription_attempts'].get(day, {})
        if not isinstance(counts, dict) or not counts.keys() <= {'pending', 'failed', 'completed'}:
            return result
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in counts.values()):
            return result
        used = sum(counts.values())
        result.update(status='available' if used < limit else 'exhausted',
                      used=used, limit=limit, remaining=max(0, limit-used))
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    return result


def summarize(local, broker, telemetry, clock, model_matches, started_at, now, allowance):
    """Fail closed on incomplete checks; retain prior session incidents separately."""
    issues, past = [], []
    def fresh(item, seconds=120):
        try:
            age = (now-timestamp(item['as_of'])).total_seconds()
            return 0 <= age <= seconds
        except (KeyError, ValueError, TypeError, AttributeError):
            return False

    if not 0 <= (now-started_at).total_seconds() <= 30:
        issues.append('check_window_exceeded_30_seconds')
    if local.get('status') != 'local_checks_passed' or local.get('issues') != [] or not fresh(local):
        issues.append('service_or_power_requires_review')
    if broker.get('status') != 'reconciliation_checks_passed' or broker.get('issues') != [] or not fresh(broker):
        issues.append('broker_reconciliation_requires_review')
    if model_matches is not True:
        issues.append('frozen_model_preflight_not_verified')
    if allowance.get('status') != 'available' or allowance.get('session_date') != str(now.astimezone(NY).date()):
        issues.append('local_model_allowance_not_available')
    def current_age(field):
        age = telemetry.get(field)
        if (isinstance(age, bool) or not isinstance(age, (int, float))
                or not math.isfinite(age) or age < 0 or not fresh(telemetry)):
            return None
        return age + (now-timestamp(telemetry['as_of'])).total_seconds()

    heartbeat, news_age = current_age('heartbeat_age_seconds'), current_age('news_age_seconds')
    if heartbeat is None or heartbeat > 120:
        issues.append('heartbeat_not_fresh')
    if (news_age is None or news_age > 600 or telemetry.get('news_fresh') is not True
            or telemetry.get('news_coverage_gap_now') is not False):
        issues.append('news_not_fresh_or_coverage_gap')
    remaining = []
    today = str(now.astimezone(NY).date())
    raw_issues = telemetry.get('issues')
    if not isinstance(raw_issues, list) or telemetry.get('status') not in ('no_local_issue_detected', 'review_required'):
        remaining.append('invalid_telemetry')
    else:
        for label in raw_issues:
            # Past blocked days remain visible; they must not permanently make
            # all later preflights fail. Exposure is independently reconciled.
            prefix = 'session_requires_coverage_review:'
            if isinstance(label, str) and label.startswith(prefix):
                day = label[len(prefix):]
                session = telemetry.get('sessions', {}).get(day, {})
                if (health.valid_day(day) and day < today and session.get('closed') is True
                        and session.get('unresolved_at_close') is False):
                    past.append(day)
                    continue
            remaining.append('current_telemetry_issue')
    if remaining:
        issues.append('telemetry_requires_review')
    market_open, next_open = None, None
    try:
        market_open = clock['is_open']
        if not isinstance(market_open, bool) or abs((now-timestamp(clock['timestamp'])).total_seconds()) > 30:
            raise ValueError()
        if not market_open:
            opened, closed = timestamp(clock['next_open']), timestamp(clock['next_close'])
            if not now < opened < closed:
                raise ValueError()
            next_open = opened.isoformat()
    except (ValueError, KeyError, TypeError, AttributeError):
        issues.append('broker_clock_not_verified')
        market_open, next_open = None, None
    return {'as_of': now.isoformat(),
            'status': 'attention_required' if issues else ('market_open_checks_passed' if market_open else 'market_closed_checks_passed'),
            'issues': sorted(set(issues)), 'market_open': market_open, 'next_regular_open': next_open,
            'past_incomplete_sessions': sorted(set(past)),
            'heartbeat_age_at_completion_seconds': heartbeat,
            'news_age_at_completion_seconds': news_age,
            'model_check': 'stored_fingerprint_only',
            'local_model_allowance': allowance,
            'limits': 'Sequential point-in-time checks, not permission to trade or a future uptime guarantee. '
                      'Local request slots are not provider subscription quota. No fresh model request; '
                      'stored preflight does not prove current model access. '
                      'No order submission, state repair, strategy changes or service restart.'}


def inspect(root, *, client=None):
    root = Path(root); directory = root/'data/telemetry/paper_ai_v1'
    started = datetime.now(timezone.utc)
    cfg = json.loads((root/'configs/paper_ai_v1.json').read_text())
    client = client or PaperClient()
    # Keep failure labels fixed. Never emit exception bodies with raw accounts
    # or credentials, and continue independent checks after one failure.
    def checked(call):
        try:
            return call()
        except Exception:
            return {}
    local = checked(lambda: readiness.inspect(root, config='paper_ai_v1'))
    broker = checked(lambda: broker_audit.audit(directory, cfg, client))
    telemetry = checked(lambda: health.audit(directory))
    decisions = checked(lambda: decision_audit.audit(directory, cfg))
    clock = checked(client.clock)
    try:
        require_model_preflight(cfg, directory)
        model_matches = True
    except (OSError, ValueError, KeyError, TypeError):
        model_matches = False
    finished = datetime.now(timezone.utc)
    allowance = local_allowance(decisions, cfg, finished)
    return summarize(local, broker, telemetry, clock, model_matches, started, finished, allowance)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        result = inspect(Path(__file__).resolve().parents[2])
    except Exception:
        result = {'status': 'attention_required', 'issues': ['preflight_unavailable']}
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(2 if result['status'] == 'attention_required' else 0)


if __name__ == '__main__':
    main()
