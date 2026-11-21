"""Offline diagnostics for blocked v4 inputs, never a backtest approval.

Report all calendar gaps and close discrepancies without repairing prices,
changing the frozen validator, fetching data or evaluating strategies.
"""
import json

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

from cash_cow.data import ROOT, sha256
from .data import NY


def diagnose(minute_index, daily_close, reference_close, start, end):
    """Use exchange-local dates and an exclusive end, retaining all gaps."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if (start.tz is not None or end.tz is not None or start != start.normalize()
            or end != end.normalize() or start >= end or end > pd.Timestamp('2025-01-01')):
        raise ValueError('Invalid historical diagnostic interval')
    if (minute_index.empty or minute_index.tz is None or minute_index.has_duplicates
            or minute_index.hasnans or not minute_index.is_monotonic_increasing):
        raise ValueError('Invalid minute timestamps')
    minute_index = minute_index.tz_convert(NY)
    for series in (daily_close, reference_close):
        index = series.index
        if (index.empty or index.tz is not None or index.has_duplicates or index.hasnans
                or not index.is_monotonic_increasing or not index.equals(index.normalize())
                or not np.isfinite(series.to_numpy()).all() or (series <= 0).any()):
            raise ValueError('Invalid daily close series')
    schedule = mcal.get_calendar('NYSE').schedule(start, end-pd.Timedelta(days=1))
    if schedule.empty:
        raise ValueError('No scheduled sessions')
    expected = pd.DatetimeIndex([], tz=NY)
    for _, session in schedule.iterrows():
        expected = expected.append(pd.date_range(session.market_open, session.market_close,
                                                freq='min', inclusive='left').tz_convert(NY))
    missing = expected.difference(minute_index)
    gap_counts = pd.Series(missing.date).value_counts().sort_index()
    missing_daily = schedule.index.difference(daily_close.index)
    extra_daily = daily_close.index.difference(schedule.index)
    reference = reference_close.reindex(daily_close.index)
    discrepancy = (reference/daily_close-1)*10000
    bad = discrepancy[discrepancy.abs() > 10]
    outside = ((minute_index < start.tz_localize(NY)) | (minute_index >= end.tz_localize(NY)))
    issues = []
    for condition, label in ((len(missing), 'missing_regular_minutes'),
                             (len(missing_daily), 'missing_daily_sessions'),
                             (len(extra_daily), 'unexpected_daily_sessions'),
                             (reference.isna().any(), 'missing_reference_closes'),
                             (len(bad), 'daily_close_difference_exceeds_10bps'),
                             (outside.any(), 'minute_rows_outside_local_date_interval')):
        if condition:
            issues.append(label)
    return {
        'status': 'review_required' if issues else 'diagnostic_checks_passed',
        'issues': issues,
        'requested_sessions': len(schedule),
        'expected_regular_minutes': len(expected),
        'missing_regular_minutes': len(missing),
        'missing_minutes_by_session': {str(k): int(v) for k, v in gap_counts.items()},
        'minute_rows_outside_local_date_interval': int(outside.sum()),
        'missing_daily_sessions': [str(d.date()) for d in missing_daily],
        'unexpected_daily_sessions': [str(d.date()) for d in extra_daily],
        'missing_reference_closes': int(reference.isna().sum()),
        'max_absolute_close_difference_bps': float(discrepancy.abs().max()) if discrepancy.notna().any() else None,
        'close_discrepancies_over_10bps': {str(k.date()): float(v) for k, v in bad.items()},
        'limits': 'Offline diagnostics only, not full OHLC validation or permission to backtest. '
                  'No forward fill, threshold relaxation, missing-session deletion or causal attribution.',
    }


def audit_cache(root=ROOT):
    """Verify immutable download hashes before reading the fixed v4 cache."""
    raw = root/'data/raw/intraday'
    frames, sources = {}, {}
    for timeframe in ('1Min', '1Day'):
        path = raw/f'alpaca_SPY_{timeframe}_2016-01-01_2025-01-01.csv.gz'
        manifest = json.loads(path.with_suffix('.manifest.json').read_text())
        digest = sha256(path)
        if digest != manifest['sha256']:
            raise ValueError('Cached input hash mismatch')
        frames[timeframe] = pd.read_csv(path, usecols=['timestamp'] if timeframe == '1Min' else ['timestamp', 'close'])
        sources[str(path.relative_to(root))] = digest
    minute_index = pd.DatetimeIndex(pd.to_datetime(frames['1Min'].timestamp, utc=True))
    daily = frames['1Day']
    daily.index = pd.DatetimeIndex(pd.to_datetime(daily.timestamp, utc=True)).tz_convert(NY).tz_localize(None).normalize()
    reference_path = root/'data/raw/SPY.csv'
    reference = pd.read_csv(reference_path, index_col=0, parse_dates=True)
    sources[str(reference_path.relative_to(root))] = sha256(reference_path)
    result = diagnose(minute_index, daily.close, reference.Close, '2016-01-01', '2025-01-01')
    result['source_sha256'] = sources
    return result


def main():
    result = audit_cache()
    print(json.dumps(result, indent=2, allow_nan=False))
    return 2 if result['issues'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
