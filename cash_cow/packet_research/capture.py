"""One-shot, read-only receipt capture. Never imported by the trading runner.

Only current-session SPY IEX bars are requested. No model or order calls. Raw
responses stay in ignored local storage; the CLI prints aggregate metadata only.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
from zoneinfo import ZoneInfo

from cash_cow.paper.client import APIError, PaperClient, TransportError, iso, timestamp

VERSION = 'receipt_capture_v1'
NY = ZoneInfo('America/New_York')


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def timed_read(call, wall, monotonic):
    started, tick = wall(), monotonic()
    payload = call()
    elapsed, received = monotonic()-tick, wall()
    if started.tzinfo is None or received.tzinfo is None:
        raise ValueError('timezone_missing')
    wall_elapsed = (received-started).total_seconds()
    if not math.isfinite(elapsed) or not 0 <= elapsed <= 60 or abs(wall_elapsed-elapsed) > 1:
        raise ValueError('clock_discontinuity_or_slow_request')
    if wall_elapsed < 0:
        raise ValueError('clock_went_backwards')
    return {'request_started_at': iso(started), 'received_at': iso(received),
            'elapsed_seconds': elapsed, 'payload_sha256': hashlib.sha256(encoded(payload)).hexdigest(),
            'payload': payload}


def capture(client, wall=lambda: datetime.now(timezone.utc), monotonic=time.monotonic):
    """Capture one observation; failures raise, closed markets remain explicit.

    received_at is after response decoding, a conservative local availability
    bound. It is not exchange publication time or proof of clock synchronization.
    """
    clock = timed_read(client.clock, wall, monotonic)
    current = timestamp(clock['received_at'])
    broker = clock['payload']
    if not isinstance(broker.get('is_open'), bool) or abs((current-timestamp(broker['timestamp'])).total_seconds()) > 10:
        raise ValueError('invalid_or_stale_broker_clock')
    record = {'schema': VERSION, 'symbol': 'SPY', 'feed': 'iex',
              'execution_enabled': False, 'clock': clock}
    if not broker['is_open']:
        return dict(record, status='market_closed', bars=None)
    day = current.astimezone(NY).date().isoformat()
    calendar = timed_read(lambda: client.calendar(day), wall, monotonic)
    if timestamp(calendar['request_started_at']) < current:
        raise ValueError('clock_went_backwards_between_requests')
    rows = calendar['payload']
    if not isinstance(rows, list) or len(rows) != 1 or rows[0]['date'] != day:
        raise ValueError('invalid_current_session_calendar')
    def boundary(key):
        value = datetime.fromisoformat(day+'T'+rows[0][key])
        if value.tzinfo is not None:
            raise ValueError('unexpected_calendar_timezone')
        return value.replace(tzinfo=NY)
    opened, closed = boundary('open'), boundary('close')
    requested = wall()
    if requested < timestamp(calendar['received_at']):
        raise ValueError('clock_went_backwards_between_requests')
    if not opened <= requested < closed or not 0 < (closed-opened).total_seconds() <= 390*60:
        raise ValueError('outside_current_regular_session')
    end = requested.replace(second=0, microsecond=0)-timedelta(microseconds=1)
    record.update(session_date=day, calendar=calendar)
    if end < opened:
        return dict(record, status='no_completed_minute', bars=None)
    params = {'symbols': 'SPY', 'timeframe': '1Min', 'start': iso(opened), 'end': iso(end),
              'feed': 'iex', 'adjustment': 'raw', 'limit': 1000, 'sort': 'asc'}
    bars = timed_read(lambda: client.request('GET', '/v2/stocks/bars', params=params, data=True), wall, monotonic)
    if timestamp(bars['request_started_at']) < requested or timestamp(bars['received_at']) >= closed:
        raise ValueError('capture_crossed_session_boundary')
    if (timestamp(bars['received_at'])-current).total_seconds() > 120:
        raise ValueError('capture_too_slow')
    payload = bars['payload']
    if payload.get('next_page_token'):
        raise ValueError('unexpected_pagination')
    mapping = payload.get('bars')
    if not isinstance(mapping, dict) or set(mapping)-{'SPY'}:
        raise ValueError('unexpected_bar_symbols')
    prices = mapping.get('SPY') or []
    if not isinstance(prices, list) or len(prices) > 390:
        raise ValueError('invalid_bar_count')
    previous = None
    for row in prices:
        at = timestamp(row['t'])
        if (not opened <= at <= end or at.second or at.microsecond
                or (previous is not None and at <= previous)):
            raise ValueError('out_of_window_or_unordered_bar')
        for key in ('o', 'h', 'l', 'c', 'v'):
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0 or (key != 'v' and value == 0):
                raise ValueError('invalid_ohlcv')
        if row['h'] < max(row['o'], row['c'], row['l']) or row['l'] > min(row['o'], row['c']):
            raise ValueError('invalid_ohlc_bounds')
        previous = at
    # Sparse IEX bars remain in the archive; completeness is a separate gate.
    expected = int((end-opened).total_seconds()//60)+1
    record.update(status='captured' if len(prices) == expected else 'incomplete_bars',
                  bars=bars, request_params=params, bar_count=len(prices), expected_minutes=expected)
    return record


def save_capture(record, directory):
    """Publish complete bytes without replacing an existing content hash."""
    raw = encoded(record)
    if len(raw) > 1_000_000:
        raise ValueError('capture_too_large')
    sha = hashlib.sha256(raw).hexdigest()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory/(sha+'.json')
    fd, name = tempfile.mkstemp(prefix='.capture-', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(name, target)
        except FileExistsError:
            if target.is_symlink() or target.read_bytes() != raw:
                raise ValueError('existing_capture_conflict') from None
    finally:
        Path(name).unlink(missing_ok=True)
    return sha


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        record = capture(PaperClient())
        sha = save_capture(record, root/'.local/research/receipt_captures')
        print(json.dumps({'status': record['status'], 'capture_sha256': sha,
                          'bar_count': record.get('bar_count', 0), 'execution_enabled': False}))
        return 0
    except (APIError, TransportError, OSError, ValueError, KeyError, TypeError, AttributeError):
        # Do not print exception payloads, credentials, raw news or broker data.
        print(json.dumps({'status': 'capture_failed', 'execution_enabled': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
