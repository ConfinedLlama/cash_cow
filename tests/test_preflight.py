"""Synthetic operational snapshots; no trading or model calls."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from cash_cow.paper import preflight

NOW = datetime(2026, 11, 15, 8, tzinfo=timezone.utc)


def inputs():
    common = {'as_of': NOW.isoformat(), 'issues': []}
    local = dict(common, status='local_checks_passed')
    broker = dict(common, status='reconciliation_checks_passed')
    telemetry = dict(common, status='no_local_issue_detected', heartbeat_age_seconds=12,
                     news_fresh=True, news_coverage_gap_now=False, sessions={})
    clock = {'is_open': False, 'timestamp': NOW.isoformat(),
             'next_open': '2026-11-16T14:30:00Z', 'next_close': '2026-11-16T21:00:00Z'}
    return [local, broker, telemetry, clock, True, NOW-timedelta(seconds=2), NOW]


def test_closed_market_is_not_a_failure_or_a_trade_permission():
    result = preflight.summarize(*inputs())
    assert result['status'] == 'market_closed_checks_passed'
    assert result['market_open'] is False
    assert result['model_check'] == 'stored_fingerprint_only'


def test_old_incidents_retained_separately_but_today_block_prevents_pass():
    args = inputs()
    telemetry = args[2]
    telemetry.update(status='review_required', issues=['session_requires_coverage_review:2026-11-13'],
                     sessions={'2026-11-13': {'closed': True, 'unresolved_at_close': False}})
    result = preflight.summarize(*args)
    assert result['status'] == 'market_closed_checks_passed'
    assert result['past_incomplete_sessions'] == ['2026-11-13']
    telemetry['issues'].append('session_requires_coverage_review:2026-11-15')
    assert preflight.summarize(*args)['status'] == 'attention_required'


@pytest.mark.parametrize('problem', ['power', 'broker', 'heartbeat', 'news', 'clock', 'model', 'slow', 'stale_check', 'nan', 'unresolved'])
def test_independent_failures_cannot_be_hidden_by_a_running_process(problem):
    args = inputs()
    if problem == 'power': args[0].update(status='review_required', issues=['external_power_not_verified'])
    if problem == 'broker': args[1]['status'] = 'review_required'
    if problem == 'heartbeat': args[2]['heartbeat_age_seconds'] = 121
    if problem == 'news': args[2]['news_coverage_gap_now'] = True
    if problem == 'clock': args[3]['timestamp'] = (NOW-timedelta(minutes=2)).isoformat()
    if problem == 'model': args[4] = False
    if problem == 'slow': args[5] = NOW-timedelta(seconds=31)
    if problem == 'stale_check': args[0]['as_of'] = (NOW-timedelta(minutes=3)).isoformat()
    if problem == 'nan': args[2]['heartbeat_age_seconds'] = float('nan')
    if problem == 'unresolved':
        args[2].update(issues=['session_requires_coverage_review:2026-11-13'],
                       sessions={'2026-11-13': {'closed': True, 'unresolved_at_close': True}})
    assert preflight.summarize(*args)['status'] == 'attention_required'


def test_snapshot_failures_are_sanitized_and_other_checks_continue(tmp_path, monkeypatch):
    (tmp_path/'configs').mkdir()
    (tmp_path/'configs/paper_ai_v1.json').write_text('{}')
    calls = []
    def fail(*args, **kwargs):
        calls.append('failed'); raise RuntimeError('private-account-secret')
    monkeypatch.setattr(preflight.readiness, 'inspect', fail)
    monkeypatch.setattr(preflight.broker_audit, 'audit', fail)
    monkeypatch.setattr(preflight.health, 'audit', fail)
    monkeypatch.setattr(preflight, 'require_model_preflight', lambda *args: None)
    class Client:
        def clock(self): calls.append('clock'); return {}
    result = preflight.inspect(tmp_path, client=Client())
    assert calls == ['failed', 'failed', 'failed', 'clock']
    assert 'private-account-secret' not in json.dumps(result)
    assert result['status'] == 'attention_required'
