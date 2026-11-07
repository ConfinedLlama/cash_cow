from datetime import datetime, timedelta, timezone
import json
import pytest

from cash_cow.paper.health import audit

NOW = datetime(2026, 11, 5, 8, tzinfo=timezone.utc)


def fixture(folder, news_age=0):
    state = {"last_event": {"at": NOW.isoformat(), "kind": "market_closed"}, "orders": {}, "sessions": {}}
    (folder / 'state.json').write_text(json.dumps(state))
    (folder / 'news').mkdir()
    (folder / 'news/status.json').write_text(json.dumps({'last_success':(NOW-timedelta(seconds=news_age)).isoformat(), 'coverage_gap':False}))
    (folder / 'events.jsonl').write_text(json.dumps(state['last_event'])+'\n')
    return state


def test_fresh_process_does_not_hide_stale_news_or_mutate_files(tmp_path):
    fixture(tmp_path,3600)
    before={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result=audit(tmp_path,NOW)
    assert result['heartbeat_age_seconds']==0
    assert not result['news_fresh'] and result['news_coverage_gap_now']
    assert 'news_unavailable' in result['issues']
    assert before=={p:p.read_bytes() for p in before}


def test_session_endpoints_reveal_missed_open_and_no_invented_returns(tmp_path):
    s=fixture(tmp_path)
    opened=NOW-timedelta(hours=18); closed=opened+timedelta(hours=6,minutes=30)
    s['sessions']['2026-11-04']={'open':opened.isoformat(),'close':closed.isoformat(),'closed':True,'partial_attendance':True,'blocked':'monitoring_gap'}
    (tmp_path/'state.json').write_text(json.dumps(s))
    (tmp_path/'events.jsonl').write_text(json.dumps({'at':(opened+timedelta(minutes=42)).isoformat(),'kind':'flat'})+'\n')
    r=audit(tmp_path,NOW)
    assert r['sessions']['2026-11-04']['event_gaps_over_120_seconds']==2
    assert r['sessions']['2026-11-04']['max_event_gap_seconds']==348*60
    assert 'return' not in r['sessions']['2026-11-04']


def test_unknown_intent_and_corrupt_tail_fail_closed_without_payloads(tmp_path):
    s=fixture(tmp_path);s['orders']={'private-id':{'payload':{'account':'private-account'}}}
    (tmp_path/'state.json').write_text(json.dumps(s))
    with (tmp_path/'events.jsonl').open('a') as f:f.write('{"private_secret":')
    r=audit(tmp_path,NOW)
    assert r['nonterminal_order_intents']==1 and r['malformed_or_future_events']==1
    assert 'private' not in json.dumps(r)


def test_future_timestamps_are_not_healthy(tmp_path):
    s=fixture(tmp_path,-100)
    s['last_event']['at']=(NOW+timedelta(seconds=30)).isoformat()
    (tmp_path/'state.json').write_text(json.dumps(s))
    r=audit(tmp_path,NOW)
    assert not r['news_fresh']
    assert 'runner_heartbeat_missing_stale_or_future' in r['issues']


def test_missing_state_is_review_required(tmp_path):
    r=audit(tmp_path,NOW)
    assert r['status']=='review_required'
    assert 'unreadable:state.json' in r['issues']


def test_recovered_collector_does_not_erase_reported_coverage_gap(tmp_path):
    fixture(tmp_path)
    p=tmp_path/'news/status.json';n=json.loads(p.read_text());n['coverage_gap']=True;p.write_text(json.dumps(n))
    r=audit(tmp_path,NOW)
    assert r['news_fresh'] and 'news_coverage_gap' in r['issues']
    assert r['status']=='review_required'


@pytest.mark.parametrize('field', ['last_event', 'sessions', 'orders'])
@pytest.mark.parametrize('bad', [None, [], 'private-secret'])
def test_nested_bad_state_fails_review_without_crash_or_disclosure(tmp_path, field, bad):
    state = fixture(tmp_path)
    state[field] = bad
    (tmp_path/'state.json').write_text(json.dumps(state))
    result = audit(tmp_path, NOW)
    assert 'invalid_object:' + field in result['issues']
    assert result['status'] == 'review_required'
    assert 'private-secret' not in json.dumps(result)
    if field == 'orders':
        assert result['order_intents'] is None
        assert result['nonterminal_order_intents'] is None


def test_unknown_order_schemas_are_unresolved_not_zero(tmp_path):
    state = fixture(tmp_path)
    state['orders'] = {'a': None, 'b': {'broker': []}, 'c': {'broker': {'status': []}}}
    (tmp_path/'state.json').write_text(json.dumps(state))
    result = audit(tmp_path, NOW)
    assert result['nonterminal_order_intents'] == 3
    assert 'invalid_order_record' in result['issues']


def test_untrusted_labels_and_nested_usage_are_not_published(tmp_path):
    state = fixture(tmp_path)
    state['last_event']['kind'] = 'private-secret'
    state['sessions'] = {'private-day': {}, '2026-11-04': None}
    (tmp_path/'state.json').write_text(json.dumps(state))
    (tmp_path/'events.jsonl').write_text(json.dumps(state['last_event']))
    (tmp_path/'ai_subscription_usage.json').write_text(json.dumps({
        'private-day': {}, '2026-11-04': [],
        '2026-11-05': {'a': None, 'b': {'status': ['private-secret']}}
    }))
    result = audit(tmp_path, NOW)
    assert result['last_event_kind'] == 'unknown'
    assert result['subscription_attempts']['2026-11-05'] == {'unknown': 2}
    assert 'private-' not in json.dumps(result)
    assert result['status'] == 'review_required'


def test_string_boolean_cannot_establish_closed_session(tmp_path):
    state = fixture(tmp_path)
    state['sessions'] = {'2026-11-04': {'closed': 'true'}}
    (tmp_path/'state.json').write_text(json.dumps(state))
    assert 'invalid_session_interval:2026-11-04' in audit(tmp_path, NOW)['issues']
