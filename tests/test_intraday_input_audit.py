import json

import pandas as pd
import pytest

from cash_cow.data import sha256
from cash_cow.intraday.input_audit import audit_cache, diagnose


def inputs():
    # Thanksgiving is absent; Friday is a 210-minute early close.
    minutes = pd.date_range('2022-11-23 09:30', periods=390, freq='min', tz='America/New_York')
    minutes = minutes.append(pd.date_range('2022-11-25 09:30', periods=210, freq='min', tz='America/New_York'))
    daily = pd.Series([100., 101.], index=pd.to_datetime(['2022-11-23', '2022-11-25']))
    return minutes, daily, daily.copy()


def test_calendar_diagnostic_accepts_holiday_and_early_close_without_mutation():
    minutes, daily, reference = inputs()
    before = daily.copy()
    result = diagnose(minutes, daily, reference, '2022-11-23', '2022-11-26')
    assert result['issues'] == []
    assert result['expected_regular_minutes'] == 600
    assert result['requested_sessions'] == 2
    pd.testing.assert_series_equal(daily, before)


def test_reports_all_gaps_discrepancies_and_utc_boundary_spillover():
    minutes, daily, reference = inputs()
    minutes = minutes.delete([0, 10, 500])
    minutes = pd.DatetimeIndex(['2022-11-22 19:01'], tz='America/New_York').append(minutes)
    reference *= 1.01
    result = diagnose(minutes, daily, reference, '2022-11-23', '2022-11-26')
    assert result['missing_minutes_by_session'] == {'2022-11-23': 2, '2022-11-25': 1}
    assert result['minute_rows_outside_local_date_interval'] == 1
    assert len(result['close_discrepancies_over_10bps']) == 2
    assert result['max_absolute_close_difference_bps'] == pytest.approx(100)


def test_missing_daily_and_reference_dates_are_explicit():
    minutes, daily, reference = inputs()
    result = diagnose(minutes, daily.iloc[:1], reference.iloc[1:], '2022-11-23', '2022-11-26')
    assert result['missing_daily_sessions'] == ['2022-11-25']
    assert result['missing_reference_closes'] == 1
    assert result['max_absolute_close_difference_bps'] is None


def test_invalid_timestamps_and_reserved_interval_fail_closed():
    minutes, daily, reference = inputs()
    for bad in (minutes.tz_localize(None), minutes.append(minutes[:1]), minutes[::-1]):
        with pytest.raises(ValueError, match='timestamps'):
            diagnose(bad, daily, reference, '2022-11-23', '2022-11-26')
    with pytest.raises(ValueError, match='interval'):
        diagnose(minutes, daily, reference, '2022-11-23', '2025-01-02')
    with pytest.raises(ValueError, match='daily close'):
        diagnose(minutes, daily.iloc[::-1], reference, '2022-11-23', '2022-11-26')


def test_cache_audit_reads_only_verified_inputs_and_never_repairs(tmp_path):
    minutes, daily, reference = inputs()
    raw = tmp_path/'data/raw/intraday'
    raw.mkdir(parents=True)
    paths = []
    for timeframe in ('1Min', '1Day'):
        frame = pd.DataFrame({'timestamp': minutes}) if timeframe == '1Min' else pd.DataFrame({
            'timestamp': daily.index.tz_localize('America/New_York'), 'close': daily.to_numpy()})
        path = raw/f'alpaca_SPY_{timeframe}_2016-01-01_2025-01-01.csv.gz'
        frame.to_csv(path, index=False, compression='gzip')
        path.with_suffix('.manifest.json').write_text(json.dumps({'sha256': sha256(path)}))
        paths.append(path)
    reference.rename('Close').to_csv(tmp_path/'data/raw/SPY.csv')
    before = {str(p): sha256(p) for p in tmp_path.rglob('*') if p.is_file()}
    result = audit_cache(tmp_path)
    assert result['status'] == 'review_required'  # Deliberately incomplete fixed v4 fixture.
    assert result['missing_regular_minutes'] > 0
    assert before == {str(p): sha256(p) for p in tmp_path.rglob('*') if p.is_file()}
    paths[0].write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='hash mismatch'):
        audit_cache(tmp_path)
