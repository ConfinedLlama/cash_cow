import pandas as pd
import pytest

from cash_cow.intraday.close_audit import compare_closes


def fixture(day='2023-11-24'):
    # Synthetic early-close fixture: final regular minute, close-boundary and later bar.
    minute = pd.Series([100., 101., 102.], index=pd.to_datetime([
        day+'T17:59:00Z', day+'T18:00:00Z', day+'T19:00:00Z']))
    daily = pd.Series([103.], index=pd.to_datetime([day]))
    reference = pd.Series([100.], index=daily.index)
    return minute, daily, reference


def test_early_close_exact_boundaries_and_no_favorable_source_selection():
    minute, daily, reference = fixture()
    before = minute.copy(deep=True)
    result = compare_closes(minute, daily, reference)
    row = result['original_daily_discrepancies'][0]
    assert row['scheduled_close'] == '2023-11-24T18:00:00+00:00'
    assert row['final_regular_minute_at'] == '2023-11-24T17:59:00+00:00'
    assert row['reference_difference_bps']['final_regular_minute'] == 0
    assert row['reference_difference_bps']['daily'] == pytest.approx((100/103-1)*10000)
    assert result['comparisons']['daily']['over_10bps'] == 1
    pd.testing.assert_series_equal(minute, before)


def test_missing_exact_final_minute_is_not_replaced_by_nearby_close():
    minute, daily, reference = fixture()
    minute = minute.iloc[1:]
    result = compare_closes(minute, daily, reference)
    assert result['comparisons']['final_regular_minute']['missing'] == 1
    assert result['original_daily_discrepancies'][0]['reference_difference_bps']['final_regular_minute'] is None


def test_daylight_saving_regular_close_and_daily_denominator():
    days = pd.to_datetime(['2024-03-08', '2024-03-11'])
    minute = pd.Series([100., 100.], index=pd.to_datetime(['2024-03-08T20:59:00Z', '2024-03-11T19:59:00Z']))
    daily = pd.Series([100., 100.], index=days)
    result = compare_closes(minute, daily, daily)
    assert result['sessions'] == 2
    assert result['comparisons']['final_regular_minute']['available'] == 2
    assert result['comparisons']['close_boundary_minute']['missing'] == 2


@pytest.mark.parametrize('kind', ['duplicate', 'nan', 'unaligned', 'holdout', 'missing_day'])
def test_rejects_invalid_or_out_of_protocol_inputs(kind):
    minute, daily, reference = fixture()
    if kind == 'duplicate':
        minute = pd.concat([minute, minute.iloc[-1:]])
    elif kind == 'nan':
        minute.iloc[0] = float('nan')
    elif kind == 'unaligned':
        minute.index = minute.index+pd.Timedelta(seconds=1)
    elif kind == 'holdout':
        minute.index = minute.index+pd.Timedelta(days=500)
    else:
        daily.loc[pd.Timestamp('2023-11-28')] = 100.
        reference = daily.copy()
    with pytest.raises(ValueError):
        compare_closes(minute, daily, reference)
