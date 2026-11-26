"""Synthetic calendar/accounting joins, never broker evidence."""
from datetime import datetime, timezone, date
import json

import pytest

from cash_cow.daily_report import load_performance, load_trial_coverage, render_report

NOW = datetime(2026, 11, 26, 8, tzinfo=timezone.utc)
DAYS = '04 05 06 09 10 11 12 13 16 17 18 19 20 23 24 25 27 30'.split()


def fixture(tmp_path):
    days = ['2026-11-'+d for d in DAYS]+['2026-12-01', '2026-12-02']
    calendar = {'source': 'Alpaca GET /v2/calendar', 'start': days[0], 'end': days[-1],
                'fetched_at': NOW.isoformat(), 'sessions': [
                    {'date': d, 'open': '09:30', 'close': '13:00' if d == '2026-11-27' else '16:00'} for d in days]}
    observation = {'mode': 'paper', 'strategy_id': 'paper_ai_v1_cost_stress', 'sessions': [
        {'session_date': days[0], 'opening_nav': 2000., 'closing_nav': 1990., 'fees': 1., 'external_flow': 0.}]}
    session = {'open': '2026-11-04T14:30:00Z', 'close': '2026-11-04T21:00:00Z',
               'closed': True, 'partial_attendance': True, 'blocked': 'private-block',
               'opening_stress_nav': 2000., 'closing_stress_nav': 1990., 'modeled_costs': 1.}
    state = {'orders': {}, 'sessions': {days[0]: session},
             'last_event': {'at': NOW.isoformat(), 'kind': 'stopped'}}
    c, s, p = [tmp_path/name for name in ('calendar.json', 'state.json', 'sessions.json')]
    c.write_text(json.dumps(calendar));s.write_text(json.dumps(state));p.write_text(json.dumps(observation))
    (tmp_path/'events.jsonl').write_text(json.dumps({'at': NOW.isoformat(), 'kind': 'stopped'})+'\n')
    performance = load_performance(p, date(2026, 11, 26), s)
    return c, s, performance


def test_calendar_keeps_missing_days_and_loss_without_assuming_zero(tmp_path, monkeypatch):
    import cash_cow.daily_report as module
    c, s, performance = fixture(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    trial = load_trial_coverage(c, s, performance, NOW)
    assert trial['elapsed_sessions'] == 16 and trial['planned_sessions'] == 20
    assert len(trial['sessions']) == 16
    assert trial['sessions'][0]['status'] == 'incomplete'
    assert trial['sessions'][-1] == {'date': '2026-11-25', 'status': 'missing', 'accounting_export': 'unavailable'}
    assert len(trial['missing_accounting_dates']) == 15
    assert '2026-11-26' not in trial['missing_accounting_dates']
    monkeypatch.setattr(module, 'commits_for_day', lambda *_: [])
    monkeypatch.setattr(module, 'git', lambda *_: 'fixture')
    report = render_report(tmp_path, date(2026, 11, 26), performance, trial)
    assert '| 2026-11-25 | missing | unavailable |' in report
    assert 'Observed net P&L: -10.00' in report and 'private-block' not in report
    assert before == {p: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('change', ['state', 'mode', 'strategy', 'future_export', 'corrupt_events', 'short_calendar'])
def test_unmatched_or_unverifiable_sources_are_rejected(tmp_path, change):
    c, s, performance = fixture(tmp_path)
    if change == 'state':
        s.write_text(s.read_text()+' ')
    elif change in ('mode', 'strategy'):
        performance['mode' if change == 'mode' else 'strategy_id'] = 'other'
    elif change == 'future_export':
        performance['coverage']['sessions'].append({'session_date': '2026-12-02', 'coverage': 'incomplete'})
    elif change == 'corrupt_events':
        (tmp_path/'events.jsonl').write_text('private-corrupt-data')
    else:
        data=json.loads(c.read_text());data['sessions'].pop();c.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_trial_coverage(c, s, performance, NOW)
