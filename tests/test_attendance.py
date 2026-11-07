"""Synthetic exchange schedules and events, not trading evidence."""
from datetime import datetime, timedelta, timezone
import json

import pytest

from cash_cow.paper.attendance import audit

NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
CALENDAR = {'source': 'Alpaca GET /v2/calendar', 'start': '2026-11-04', 'end': '2026-11-09',
            'fetched_at': NOW.isoformat(), 'sessions': [
                {'date': day, 'open': '09:30', 'close': '16:00'}
                for day in ('2026-11-04', '2026-11-05', '2026-11-06', '2026-11-09')]}


def fixture(folder):
    opened = NOW.replace(day=4, hour=14, minute=30)
    closed = opened+timedelta(hours=6, minutes=30)
    session = {'open': opened.isoformat(), 'close': closed.isoformat(), 'closed': True,
               'partial_attendance': False, 'blocked': None}
    state = {'last_event': {'at': NOW.isoformat(), 'kind': 'market_closed'},
             'orders': {}, 'sessions': {'2026-11-04': session}}
    (folder/'state.json').write_text(json.dumps(state))
    (folder/'news').mkdir()
    (folder/'news/status.json').write_text(json.dumps({'last_success': NOW.isoformat()}))
    events = [{'at': (opened+timedelta(minutes=i)).isoformat(), 'kind': 'warmup'} for i in range(391)]
    (folder/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
    return state


def test_missing_days_remain_in_denominator_and_future_is_not_zero_return(tmp_path):
    fixture(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = audit(tmp_path, CALENDAR, '2026-11-04', 4, NOW)
    assert result['elapsed_sessions'] == 3
    assert result['counts'] == {'no_local_attendance_issue': 1, 'missing': 2, 'scheduled': 1}
    assert result['planned_sessions'] == 4
    assert all('return' not in row for row in result['sessions'])
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize('change,reason', [
    ({'blocked': 'monitoring_gap'}, 'blocked'),
    ({'partial_attendance': True}, 'partial_attendance'),
    ({'closed': False}, 'close_not_recorded'),
    ({'close': '2026-11-04T20:00:00+00:00'}, 'calendar_interval_mismatch'),
])
def test_recorded_sessions_do_not_imply_complete_attendance(tmp_path, change, reason):
    state = fixture(tmp_path);state['sessions']['2026-11-04'].update(change)
    (tmp_path/'state.json').write_text(json.dumps(state))
    result = audit(tmp_path, CALENDAR, '2026-11-04', 4, NOW)
    assert result['sessions'][0]['status'] == 'incomplete'
    assert reason in result['sessions'][0]['reasons']


def test_corrupt_event_evidence_never_passes_attendance(tmp_path):
    fixture(tmp_path)
    with (tmp_path/'events.jsonl').open('a') as f:f.write('\nprivate-corrupt-record')
    result = audit(tmp_path, CALENDAR, '2026-11-04', 4, NOW)
    assert result['counts'] == {'unverifiable': 3, 'scheduled': 1}
    assert 'private-' not in json.dumps(result)


def test_calendar_duplicates_and_short_horizon_are_rejected(tmp_path):
    fixture(tmp_path)
    with pytest.raises(ValueError, match='Calendar snapshot'):
        audit(tmp_path, CALENDAR, '2026-11-04', 20, NOW)
    bad = dict(CALENDAR, sessions=CALENDAR['sessions']+[CALENDAR['sessions'][-1]])
    with pytest.raises(ValueError, match='Calendar snapshot'):
        audit(tmp_path, bad, '2026-11-04', 4, NOW)


def test_in_progress_session_is_not_a_completed_sample(tmp_path):
    fixture(tmp_path)
    now = NOW.replace(day=4, hour=15)
    calendar = dict(CALENDAR, fetched_at=now.isoformat())
    result = audit(tmp_path, calendar, '2026-11-04', 4, now)
    assert result['elapsed_sessions'] == 0
    assert result['counts'] == {'in_progress': 1, 'scheduled': 3}


def test_unreadable_state_is_unknown_not_missing_or_flat(tmp_path):
    result = audit(tmp_path, CALENDAR, '2026-11-04', 4, NOW)
    assert result['counts']['unverifiable'] == 3
    with pytest.raises(ValueError, match='timezone'):
        audit(tmp_path, CALENDAR, '2026-11-04', 4, NOW.replace(tzinfo=None))


def test_exchange_short_session_uses_its_actual_close(tmp_path):
    state = fixture(tmp_path)
    state['sessions']['2026-11-04']['close'] = '2026-11-04T18:00:00+00:00'
    (tmp_path/'state.json').write_text(json.dumps(state))
    calendar = dict(CALENDAR, sessions=[dict(CALENDAR['sessions'][0], close='13:00')]+CALENDAR['sessions'][1:])
    result = audit(tmp_path, calendar, '2026-11-04', 4, NOW)
    assert result['sessions'][0]['status'] == 'no_local_attendance_issue'


def test_state_change_between_reads_invalidates_completed_evidence(tmp_path, monkeypatch):
    import cash_cow.paper.attendance as module
    fixture(tmp_path)
    original = module.health_audit
    def changed(*args):
        result = original(*args)
        result['source_sha256']['state.json'] = 'different-snapshot'
        return result
    monkeypatch.setattr(module, 'health_audit', changed)
    result = audit(tmp_path, CALENDAR, '2026-11-04', 4, NOW)
    assert result['counts']['unverifiable'] == 3
    assert 'state_changed_during_audit' in result['issues']
