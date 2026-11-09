"""Deterministic current-session history; no network, model or order calls."""
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import math
from zoneinfo import ZoneInfo

from cash_cow.paper.client import timestamp

VERSION = 'packet_context_v2'
LAGS = (5, 15, 30)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def history_features(snapshot, context):
    """Use only complete minutes through the baseline feature timestamp.

    observed_at on legacy snapshots was tick start, so this validates recorded
    timing only. It does not certify HTTP receipt timing or execution feasibility.
    """
    cutoff = timestamp(context['as_of'])
    day = datetime.strptime(context['session_date'], '%Y-%m-%d').date()
    opened = datetime.combine(day, time(9, 30), ZoneInfo('America/New_York'))
    if cutoff.astimezone(ZoneInfo('America/New_York')).date() != day:
        raise ValueError('session_date_mismatch')
    if context['symbol'] != 'SPY' or context['feed'] != 'iex' or snapshot['feed'] != 'iex':
        raise ValueError('symbol_or_feed_mismatch')
    observed = timestamp(snapshot['observed_at'])
    if not 0 <= (cutoff-observed).total_seconds() <= 120:
        raise ValueError('snapshot_not_available_or_stale')
    end_bar = timestamp(context['features']['bar'])
    minutes = (end_bar-opened).total_seconds()/60 + 1
    if (minutes < 35 or minutes > 390 or not minutes.is_integer()
            or int(minutes) % 5 or end_bar+timedelta(minutes=1) > cutoff
            or (cutoff-end_bar-timedelta(minutes=1)).total_seconds() > 120):
        raise ValueError('invalid_feature_interval')
    rows = snapshot['bars']
    if not isinstance(rows, list) or len(rows) > 390:
        raise ValueError('invalid_bar_collection')
    used = []
    for i, row in enumerate(rows):
        at = timestamp(row['t'])
        if (at != opened+timedelta(minutes=i)
                or at+timedelta(minutes=1) > min(cutoff, observed)):
            raise ValueError('missing_unordered_or_future_bar')
        values = [row[k] for k in ('o', 'h', 'l', 'c', 'v')]
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError('invalid_ohlcv')
        if row['h'] < max(row['o'], row['l'], row['c']) or row['l'] > min(row['o'], row['c']):
            raise ValueError('invalid_ohlc_bounds')
        if at <= end_bar:
            used.append(row)
    if len(used) != int(minutes):
        raise ValueError('missing_feature_bar')
    if used[-1]['c'] != context['features']['close']:
        raise ValueError('baseline_close_mismatch')
    aggregates = []
    for start in range(len(used)-30, len(used), 5):
        chunk = used[start:start+5]
        aggregates.append({'start': chunk[0]['t'], 'end':
                           (timestamp(chunk[-1]['t'])+timedelta(minutes=1)).astimezone(timezone.utc).isoformat(),
                           'open': chunk[0]['o'], 'high': max(r['h'] for r in chunk),
                           'low': min(r['l'] for r in chunk), 'close': chunk[-1]['c'],
                           'volume': sum(r['v'] for r in chunk)})
    return {'version': VERSION, 'snapshot_sha256': digest(snapshot),
            'recorded_observed_at': snapshot['observed_at'],
            'receipt_timing': 'unverified_legacy_tick_start',
            'through_bar': context['features']['bar'], 'five_minute_bars': aggregates,
            'close_returns': {str(lag): used[-1]['c']/used[-1-lag]['c']-1 for lag in LAGS}}
