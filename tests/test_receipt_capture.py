"""Synthetic receipts only; no network, paper fills or investment evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os

import pytest

from cash_cow.packet_research.capture import capture, encoded, save_capture, timed_read

NOW = datetime(2026, 11, 10, 15, tzinfo=timezone.utc)


class Client:
    def __init__(self, opened=True, day='2026-11-10', close='16:00'):
        self.calls = []
        self.clock_payload = {'is_open': opened, 'timestamp': NOW.isoformat()}
        self.calendar_payload = [{'date': day, 'open': '09:30', 'close': close}]
        start = NOW.replace(hour=14, minute=30)
        self.bars_payload = {'bars': {'SPY': [
            {'t': (start+timedelta(minutes=i)).isoformat(), 'o': 600, 'h': 601, 'l': 599, 'c': 600, 'v': 20}
            for i in range(30)]}, 'next_page_token': None}

    def clock(self):
        self.calls.append('clock');return deepcopy(self.clock_payload)

    def calendar(self, day):
        self.calls.append(('calendar', day));return deepcopy(self.calendar_payload)

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs));return deepcopy(self.bars_payload)


def run(client):
    return capture(client, wall=lambda: NOW, monotonic=lambda: 0)


def test_capture_exact_current_session_and_no_trading_methods():
    client = Client()
    record = run(client)
    assert record['status'] == 'captured'
    assert record['bar_count'] == record['expected_minutes'] == 30
    assert record['bars']['received_at'] == NOW.isoformat()
    assert record['bars']['payload_sha256'] == hashlib.sha256(encoded(client.bars_payload)).hexdigest()
    assert not record['execution_enabled']
    assert client.calls == ['clock', ('calendar', '2026-11-10'), ('GET', '/v2/stocks/bars', {
        'params': {'symbols': 'SPY', 'timeframe': '1Min', 'start': '2026-11-10T14:30:00+00:00',
                   'end': '2026-11-10T14:59:59.999999+00:00', 'feed': 'iex',
                   'adjustment': 'raw', 'limit': 1000, 'sort': 'asc'}, 'data': True})]


def test_closed_market_never_downloads_old_prices():
    client = Client(opened=False)
    record = run(client)
    assert record['status'] == 'market_closed' and record['bars'] is None
    assert client.calls == ['clock']


def test_first_minute_waits_for_completed_bar():
    client = Client(); now = NOW.replace(hour=14, minute=30, second=30)
    client.clock_payload['timestamp'] = now.isoformat()
    assert capture(client, lambda: now, lambda: 0)['status'] == 'no_completed_minute'
    assert len(client.calls) == 2


def test_receipt_time_is_after_decoding_not_request_start():
    wall = iter([NOW, NOW+timedelta(seconds=3)])
    mono = iter([10, 13])
    record = timed_read(lambda: {'value': 1}, lambda: next(wall), lambda: next(mono))
    assert record['received_at'] != record['request_started_at']
    assert record['elapsed_seconds'] == 3


@pytest.mark.parametrize('wall_seconds,elapsed', [(-1, 1), (90, 90), (30, 1), (0, float('nan'))])
def test_clock_discontinuities_and_long_reads_rejected(wall_seconds, elapsed):
    wall = iter([NOW, NOW+timedelta(seconds=wall_seconds)])
    mono = iter([0, elapsed])
    with pytest.raises(ValueError):
        timed_read(lambda: {}, lambda: next(wall), lambda: next(mono))


@pytest.mark.parametrize('field,value', [('timestamp', '2026-11-09T15:00:00Z'), ('is_open', 'true')])
def test_untrusted_clock_cannot_trigger_data_request(field, value):
    client = Client();client.clock_payload[field] = value
    with pytest.raises(ValueError):run(client)
    assert client.calls == ['clock']


def test_calendar_mismatch_and_halfday_end_rejected():
    for client in (Client(day='2026-11-09'), Client(close='09:45')):
        with pytest.raises(ValueError):run(client)
        assert len(client.calls) == 2


@pytest.mark.parametrize('change', ['future', 'prior_session', 'duplicate', 'nan', 'ohlc', 'pagination', 'other_symbol'])
def test_bad_data_is_rejected_without_retries(change):
    client = Client();row = client.bars_payload['bars']['SPY'][-1]
    if change == 'future':row['t'] = NOW.isoformat()
    elif change == 'prior_session':row['t'] = '2026-11-09T15:00:00Z'
    elif change == 'duplicate':row['t'] = client.bars_payload['bars']['SPY'][-2]['t']
    elif change == 'nan':row['c'] = float('nan')
    elif change == 'ohlc':row['c'] = 700
    elif change == 'pagination':client.bars_payload['next_page_token'] = 'private-token'
    elif change == 'other_symbol':client.bars_payload['bars']['QQQ'] = []
    with pytest.raises(ValueError):run(client)
    assert len(client.calls) == 3


def test_sparse_feed_preserved_as_incomplete_not_filled():
    client = Client();client.bars_payload['bars']['SPY'].pop(4)
    record = run(client)
    assert record['status'] == 'incomplete_bars'
    assert record['bar_count'] == 29 and record['expected_minutes'] == 30


def test_save_is_private_content_addressed_and_does_not_replace(tmp_path):
    record = run(Client())
    sha = save_capture(record, tmp_path)
    target = tmp_path/(sha+'.json');before = target.stat()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == sha
    assert before.st_mode & 0o777 == 0o600
    assert save_capture(record, tmp_path) == sha
    assert target.stat().st_ino == before.st_ino
    assert json.loads(target.read_bytes()) == record
    target.write_text('corrupt')
    with pytest.raises(ValueError, match='conflict'):save_capture(record, tmp_path)
    assert target.read_text() == 'corrupt' and len(list(tmp_path.iterdir())) == 1


def test_failed_atomic_publication_leaves_no_final_or_temp_file(tmp_path, monkeypatch):
    def fail(*args):raise OSError('synthetic disk error')
    monkeypatch.setattr(os, 'link', fail)
    with pytest.raises(OSError):save_capture(run(Client()), tmp_path)
    assert not list(tmp_path.iterdir())


def test_backwards_clock_between_http_requests_is_rejected():
    client = Client()
    times = iter([NOW, NOW, NOW-timedelta(seconds=2), NOW-timedelta(seconds=2)])
    with pytest.raises(ValueError, match='between_requests'):
        capture(client, lambda: next(times), lambda: 0)
    assert len(client.calls) == 2


def test_response_arriving_after_early_close_is_rejected():
    client = Client(close='10:01')
    times = iter([NOW, NOW, NOW, NOW, NOW, NOW+timedelta(seconds=59), NOW+timedelta(seconds=61)])
    ticks = iter([0, 0, 0, 0, 0, 2])
    with pytest.raises(ValueError, match='session_boundary'):
        capture(client, lambda: next(times), lambda: next(ticks))
