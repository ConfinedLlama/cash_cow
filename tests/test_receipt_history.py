"""Synthetic receipt integrity and leakage boundaries; no market evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from cash_cow.packet_research.capture import capture
from cash_cow.packet_research.history import digest
from cash_cow.packet_research.receipts import receipt_history


def fixture():
    now = datetime(2026, 11, 12, 15, 5, tzinfo=timezone.utc)
    opened = now.replace(hour=14, minute=30)
    prices = [{'t': (opened+timedelta(minutes=i)).isoformat(), 'o': 600, 'h': 602,
               'l': 599, 'c': 601, 'v': 20} for i in range(35)]
    class Client:
        def clock(self):return {'is_open': True, 'timestamp': now.isoformat()}
        def calendar(self, day):return [{'date': day, 'open': '09:30', 'close': '16:00'}]
        def request(self, *args, **kwargs):return {'bars': {'SPY': prices}, 'next_page_token': None}
    record = capture(Client(), wall=lambda: now, monotonic=lambda: 0)
    context = {'as_of': (now+timedelta(seconds=1)).isoformat(), 'session_date': '2026-11-12',
               'symbol': 'SPY', 'feed': 'iex', 'features': {'bar': prices[-1]['t'], 'close': 601}}
    return record, context


def rehash(record, key):
    record[key]['payload_sha256'] = digest(record[key]['payload'])


def test_valid_receipt_features_do_not_mutate_inputs():
    record, context = fixture();original = deepcopy((record, context))
    result = receipt_history(record, context)
    assert result['receipt_timing'] == 'recorded_response_received_before_cutoff'
    assert len(result['five_minute_bars']) == 6
    assert result['close_returns'] == {'5': 0, '15': 0, '30': 0}
    assert result['capture_sha256'] == digest(record)
    assert (record, context) == original


@pytest.mark.parametrize('mutation', ['future_receipt', 'stale_receipt', 'hash', 'backwards',
    'elapsed', 'elapsed_bool', 'closed', 'legacy', 'incomplete', 'pagination', 'symbol',
    'missing_bar', 'future_bar', 'wrong_close', 'calendar', 'early_close', 'request', 'count', 'end'])
def test_unusable_or_lookahead_captures_fail(mutation):
    record, context = fixture()
    if mutation == 'future_receipt':context['as_of'] = '2026-11-12T15:04:59Z'
    elif mutation == 'stale_receipt':context['as_of'] = '2026-11-12T15:07:01Z'
    elif mutation == 'hash':record['bars']['payload']['bars']['SPY'][0]['v'] = 40
    elif mutation == 'backwards':record['bars']['request_started_at'] = '2026-11-12T15:05:01Z'
    elif mutation == 'elapsed':record['bars']['elapsed_seconds'] = 10
    elif mutation == 'elapsed_bool':record['bars']['elapsed_seconds'] = False
    elif mutation == 'closed':record['clock']['payload']['is_open'] = False;rehash(record, 'clock')
    elif mutation == 'legacy':record['schema'] = 'legacy_tick_start'
    elif mutation == 'incomplete':record['status'] = 'incomplete_bars'
    elif mutation == 'pagination':record['bars']['payload']['next_page_token'] = 'page';rehash(record, 'bars')
    elif mutation == 'symbol':record['bars']['payload']['bars']['QQQ'] = [];rehash(record, 'bars')
    elif mutation == 'missing_bar':record['bars']['payload']['bars']['SPY'].pop(8);rehash(record, 'bars')
    elif mutation == 'future_bar':record['bars']['payload']['bars']['SPY'][-1]['t'] = '2026-11-12T15:05:00Z';rehash(record, 'bars')
    elif mutation == 'wrong_close':context['features']['close'] = 600
    elif mutation == 'calendar':record['calendar']['payload'][0]['date'] = '2026-11-11';rehash(record, 'calendar')
    elif mutation == 'early_close':record['calendar']['payload'][0]['close'] = '10:00';rehash(record, 'calendar')
    elif mutation == 'request':record['request_params']['adjustment'] = 'all'
    elif mutation == 'count':record['bar_count'] = 34
    elif mutation == 'end':record['request_params']['end'] = '2026-11-12T15:04:30Z'
    with pytest.raises(ValueError):receipt_history(record, context)
