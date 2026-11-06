"""Synthetic packets only; audit never invokes a model or submits an order."""
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from cash_cow.paper.decision_audit import audit

NOW = datetime(2026, 11, 5, 16, tzinfo=timezone.utc)
CONFIG = {'version': 'paper_ai_v1', 'max_quote_age_seconds': 60,
          'ai': {'proposal_ttl_seconds': 120}}


def fixture(folder, status='completed'):
    (folder/'ai_decisions').mkdir()
    observed = NOW-timedelta(minutes=1)
    context = {'as_of': observed.isoformat(), 'session_date': '2026-11-05',
               'features': {'bar': '2026-11-05T15:54:00Z'}, 'position_qty': 0.0,
               'news': [{'id': 'private-news', 'headline': 'private-headline',
                         'published_at': observed.isoformat(), 'updated_at': observed.isoformat(),
                         'first_observed_at': observed.isoformat()}],
               'quote': {'t': observed.isoformat()}}
    slot = hashlib.sha256(f"paper_ai_v1:{context['features']['bar']}:0.0".encode()).hexdigest()[:24]
    record = {'status': status, 'context': context, 'received_at': (observed+timedelta(seconds=4)).isoformat(),
              'proposal': {'action': 'HOLD', 'confidence': .8, 'rationale': 'private-rationale', 'news_ids': []}}
    write(folder/'ai_decisions'/f'{slot}.json', record)
    write(folder/'ai_subscription_usage.json', {'2026-11-05': {
        slot: {'status': status, 'usage': {'input_tokens': 100, 'output_tokens': 20}},
        'preflight-check': {'status': 'failed'}}})
    event = {'kind': 'ai_proposal', 'decision_id': slot, 'as_of': observed.isoformat(),
             'at': NOW.isoformat(), 'action': 'HOLD'}
    (folder/'events.jsonl').write_text('\n'.join(json.dumps(event) for _ in range(3)))
    return slot, record


def write(path, obj):
    path.write_text(json.dumps(obj))


def test_distinct_decisions_not_poll_counts_and_no_mutation(tmp_path):
    fixture(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = audit(tmp_path, CONFIG, NOW)
    assert result['errors'] == {}
    assert result['completed_actions'] == {'HOLD': 1}
    assert result['proposal_events'] == 3
    assert result['unique_decisions_referenced'] == 1
    assert result['repeated_proposal_events'] == 2
    assert result['preflight_attempts'] == 1
    assert result['reported_tokens_all_attempts']['input_tokens'] == 100
    assert 'private' not in json.dumps(result).replace('Private', '')
    assert before == {p: p.read_bytes() for p in before}


def test_future_news_and_response_are_reviewed_not_rewritten(tmp_path):
    slot, record = fixture(tmp_path)
    record['context']['news'][0]['first_observed_at'] = NOW.isoformat()
    write(tmp_path/'ai_decisions'/f'{slot}.json', record)
    result = audit(tmp_path, CONFIG, NOW)
    assert result['errors']['noncausal_packet_news'] == 1
    record['received_at'] = (NOW+timedelta(seconds=1)).isoformat()
    write(tmp_path/'ai_decisions'/f'{slot}.json', record)
    assert audit(tmp_path, CONFIG, NOW)['errors']['invalid_decision_record'] == 1


def test_mismatched_usage_and_unowned_events_are_reported(tmp_path):
    slot, _ = fixture(tmp_path)
    write(tmp_path/'ai_subscription_usage.json', {'2026-11-05': {'unmatched': {'status': 'completed'}}})
    result = audit(tmp_path, CONFIG, NOW)
    assert result['errors']['decision_usage_mismatch'] == 1
    assert result['errors']['market_usage_without_decision'] == 1
    (tmp_path/'ai_decisions'/f'{slot}.json').unlink()
    assert audit(tmp_path, CONFIG, NOW)['errors']['event_without_completed_decision'] == 3


def test_failed_and_expired_pending_trials_stay_visible(tmp_path):
    slot, record = fixture(tmp_path, status='failed')
    (tmp_path/'events.jsonl').write_text('')
    result = audit(tmp_path, CONFIG, NOW)
    assert result['decision_statuses'] == {'failed': 1}
    assert result['completed_actions'] == {}
    record['status'] = 'pending'
    write(tmp_path/'ai_decisions'/f'{slot}.json', record)
    result = audit(tmp_path, CONFIG, NOW+timedelta(minutes=5))
    assert result['errors']['expired_pending_decision'] == 1


def test_stale_quote_and_expired_consumption_cannot_pass(tmp_path):
    slot, record = fixture(tmp_path)
    record['context']['quote']['t'] = (NOW-timedelta(minutes=5)).isoformat()
    write(tmp_path/'ai_decisions'/f'{slot}.json', record)
    event = {'kind': 'ai_proposal', 'decision_id': slot, 'as_of': record['context']['as_of'],
             'at': (NOW+timedelta(minutes=2)).isoformat(), 'action': 'BUY'}
    (tmp_path/'events.jsonl').write_text(json.dumps(event))
    result = audit(tmp_path, CONFIG, NOW+timedelta(minutes=3))
    assert result['errors']['invalid_packet_quote_age'] == 1
    assert result['errors']['invalid_consumption_time'] == 1
    assert result['errors']['event_decision_mismatch'] == 1


def test_corrupt_sources_do_not_leak_private_content(tmp_path):
    slot, _ = fixture(tmp_path)
    (tmp_path/'ai_decisions'/f'{slot}.json').write_text('{private-token')
    write(tmp_path/'ai_subscription_usage.json', {'private-date': {}, '2026-11-05': []})
    (tmp_path/'events.jsonl').write_text('private-headline')
    result = audit(tmp_path, CONFIG, NOW)
    assert result['status'] == 'review_required'
    assert 'private-' not in json.dumps(result)
    assert result['errors']['invalid_usage_date'] == 1


def test_missing_sources_and_naive_now(tmp_path):
    assert audit(tmp_path, CONFIG, NOW)['errors']['missing_decision_directory'] == 1
    with pytest.raises(ValueError, match='timezone'):
        audit(tmp_path, CONFIG, NOW.replace(tzinfo=None))


def test_setup_diagnostics_are_separate_and_bad_tokens_are_flagged(tmp_path):
    fixture(tmp_path)
    p = tmp_path/'ai_subscription_usage.json'
    usage = json.loads(p.read_text())
    usage['2026-11-05']['diagnostic-test'] = {'status': 'failed', 'usage': {'input_tokens': True}}
    write(p, usage)
    result = audit(tmp_path, CONFIG, NOW)
    assert result['diagnostic_attempts'] == 1
    assert 'market_usage_without_decision' not in result['errors']
    assert result['errors']['invalid_token_usage'] == 1
    assert result['completed_actions'] == {'HOLD': 1}
