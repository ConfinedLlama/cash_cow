"""Compare close definitions offline without selecting or replacing a price."""
import json

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

from cash_cow.data import ROOT, sha256
from .data import NY
from .input_audit import audit_cache


def compare_closes(minute, daily, reference):
    """Keep exact scheduled boundaries; never substitute a nearby minute."""
    for series in (minute, daily, reference):
        if (series.empty or series.index.hasnans or series.index.has_duplicates
                or not series.index.is_monotonic_increasing
                or not np.isfinite(series.to_numpy()).all() or (series <= 0).any()):
            raise ValueError('Invalid close observations')
    if (minute.index.tz is None or not minute.index.equals(minute.index.floor('min'))
            or minute.index.min() < pd.Timestamp('2016-01-01', tz='UTC')
            or minute.index.max() >= pd.Timestamp('2025-01-01', tz='UTC')):
        raise ValueError('Invalid historical minute interval')
    for series in (daily, reference):
        if (series.index.tz is not None or not series.index.equals(series.index.normalize())
                or series.index.min() < pd.Timestamp('2016-01-01')
                or series.index.max() >= pd.Timestamp('2025-01-01')):
            raise ValueError('Invalid historical daily interval')
    if not daily.index.equals(reference.index):
        raise ValueError('Daily sources must have identical dates')
    schedule = mcal.get_calendar('NYSE').schedule(daily.index.min(), daily.index.max())
    if not daily.index.equals(schedule.index):
        raise ValueError('Daily observations must cover every scheduled session')
    minute = minute.copy()
    minute.index = minute.index.tz_convert(NY)
    final_by_day = minute.groupby(minute.index.tz_localize(None).normalize()).last()
    names = ('daily', 'final_regular_minute', 'close_boundary_minute', 'last_observed_minute')
    totals = {name: {'available': 0, 'missing': 0, 'over_10bps': 0,
                     'max_absolute_difference_bps': None} for name in names}
    flagged = []
    for day, session in schedule.iterrows():
        final_at = session.market_close-pd.Timedelta(minutes=1)
        values = {'daily': daily.loc[day],
                  'final_regular_minute': minute.get(final_at),
                  'close_boundary_minute': minute.get(session.market_close),
                  'last_observed_minute': final_by_day.get(day)}
        comparisons = {}
        for name, value in values.items():
            bps = None if value is None else float((reference.loc[day]/value-1)*10000)
            comparisons[name] = bps
            bucket = totals[name]
            if bps is None:
                bucket['missing'] += 1
            else:
                bucket['available'] += 1
                bucket['over_10bps'] += abs(bps) > 10
                bucket['max_absolute_difference_bps'] = max(
                    bucket['max_absolute_difference_bps'] or 0., abs(bps))
        if abs(comparisons['daily']) > 10:
            flagged.append({'session_date': str(day.date()),
                            'scheduled_close': session.market_close.isoformat(),
                            'final_regular_minute_at': final_at.isoformat(),
                            'reference_difference_bps': comparisons})
    return {'sessions': len(schedule), 'comparisons': totals,
            'original_daily_discrepancies': flagged,
            'limits': 'Differences are (reference/comparison - 1) * 10000, not returns. '
                      'Close-boundary minute may contain auction or post-session trades. '
                      'Last observed minute is not an official close. Exact missing boundaries stay unavailable. '
                      'No best-source selection, price replacement, eligibility inference or strategy validation.'}


def audit(root=ROOT):
    baseline = audit_cache(root)
    sources = baseline['source_sha256']
    raw = root/'data/raw/intraday'
    minute_path = raw/'alpaca_SPY_1Min_2016-01-01_2025-01-01.csv.gz'
    daily_path = raw/'alpaca_SPY_1Day_2016-01-01_2025-01-01.csv.gz'
    minute = pd.read_csv(minute_path, usecols=['timestamp', 'close'])
    minute.index = pd.DatetimeIndex(pd.to_datetime(minute.timestamp, utc=True))
    daily = pd.read_csv(daily_path, usecols=['timestamp', 'close'])
    daily.index = pd.DatetimeIndex(pd.to_datetime(daily.timestamp, utc=True)).tz_convert(NY).tz_localize(None).normalize()
    reference = pd.read_csv(root/'data/raw/SPY.csv', index_col=0, parse_dates=True).Close.reindex(daily.index)
    result = compare_closes(minute.close, daily.close, reference)
    if any(sha256(root/path) != digest for path, digest in sources.items()):
        raise ValueError('Source changed during close comparison')
    return {'status': baseline['status'], 'input_issues': baseline['issues'],
            'source_sha256': sources, **result}


def main():
    try:
        result = audit()
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        print(json.dumps({'status': 'review_required', 'issues': ['invalid_or_unreadable_close_evidence']}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 2 if result['input_issues'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
