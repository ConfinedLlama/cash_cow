"""Validate locally recorded response receipts without network or state writes.

This checks internal consistency, not exchange authenticity or clock accuracy.
Legacy tick-start archives must never be promoted to response receipts.
"""
from datetime import datetime, time, timedelta
import math
from zoneinfo import ZoneInfo

from cash_cow.paper.client import timestamp
from .history import digest, history_features

NY = ZoneInfo('America/New_York')


def validate_receipt(receipt, cutoff):
    if not isinstance(receipt, dict) or set(receipt) != {
        'request_started_at', 'received_at', 'elapsed_seconds', 'payload_sha256', 'payload'
    }:
        raise ValueError('invalid_receipt_schema')
    start, end = timestamp(receipt['request_started_at']), timestamp(receipt['received_at'])
    elapsed = receipt['elapsed_seconds']
    if (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
            or not math.isfinite(elapsed) or not 0 <= elapsed <= 60
            or not start <= end <= cutoff
            or abs((end-start).total_seconds()-elapsed) > 1):
        raise ValueError('invalid_receipt_timing')
    if digest(receipt['payload']) != receipt['payload_sha256']:
        raise ValueError('receipt_payload_hash_mismatch')
    return start, end


def receipt_history(record, context):
    """Require complete, timely receipts then reuse the frozen feature formulas."""
    if (record.get('schema') != 'receipt_capture_v1' or record.get('status') != 'captured'
            or record.get('execution_enabled') is not False
            or record.get('symbol') != 'SPY' or record.get('feed') != 'iex'):
        raise ValueError('unusable_capture')
    cutoff = timestamp(context['as_of'])
    timings = [validate_receipt(record[key], cutoff) for key in ('clock', 'calendar', 'bars')]
    clock, calendar, bars = timings
    if (not clock[1] <= calendar[0] or not calendar[1] <= bars[0]
            or not 0 <= (bars[1]-clock[1]).total_seconds() <= 120
            or not 0 <= (cutoff-bars[1]).total_seconds() <= 120):
        raise ValueError('invalid_capture_sequence_or_age')
    broker = record['clock']['payload']
    if (broker['is_open'] is not True
            or abs((timestamp(broker['timestamp'])-clock[1]).total_seconds()) > 10):
        raise ValueError('invalid_broker_clock')
    day = context['session_date']
    rows = record['calendar']['payload']
    if (record['session_date'] != day or clock[1].astimezone(NY).date().isoformat() != day
            or not isinstance(rows, list) or len(rows) != 1 or rows[0]['date'] != day):
        raise ValueError('calendar_session_mismatch')
    def boundary(key):
        result = datetime.fromisoformat(day+'T'+rows[0][key])
        if result.tzinfo is not None:
            raise ValueError('unexpected_calendar_timezone')
        return result.replace(tzinfo=NY)
    opened, closed = boundary('open'), boundary('close')
    if (opened.time() != time(9, 30) or not 0 < (closed-opened).total_seconds() <= 390*60
            or not opened <= clock[1] <= bars[1] < closed or cutoff >= closed):
        raise ValueError('outside_regular_session')
    params = record['request_params']
    start, end = timestamp(params['start']), timestamp(params['end'])
    expected = dict(symbols='SPY', timeframe='1Min', start=params['start'], end=params['end'],
                    feed='iex', adjustment='raw', limit=1000, sort='asc')
    if (params != expected or type(params['limit']) is not int or start != opened
            or end.second != 59 or end.microsecond != 999999
            or not opened <= end < bars[0]
            or not 0 <= (bars[0]-end).total_seconds() <= 120):
        raise ValueError('invalid_bar_request')
    payload = record['bars']['payload']
    if payload.get('next_page_token') or set(payload['bars']) != {'SPY'}:
        raise ValueError('incomplete_or_wrong_symbol_response')
    prices = payload['bars']['SPY']
    count = int((end-opened).total_seconds()//60)+1
    if (not isinstance(prices, list) or not 1 <= count <= 390 or len(prices) != count
            or type(record['bar_count']) is not int or type(record['expected_minutes']) is not int
            or record['bar_count'] != count or record['expected_minutes'] != count):
        raise ValueError('incomplete_bar_response')
    # Frozen helper validates contiguous minute timestamps, OHLCV and baseline
    # close, and uses only bars through the baseline's completed feature bar.
    features = history_features({'feed': 'iex', 'observed_at': record['bars']['received_at'],
                                 'bars': prices}, context)
    if timestamp(prices[-1]['t'])+timedelta(minutes=1) != end+timedelta(microseconds=1):
        raise ValueError('response_does_not_match_request')
    features['receipt_timing'] = 'recorded_response_received_before_cutoff'
    features['capture_sha256'] = digest(record)
    return features
