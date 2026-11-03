import json
import numpy as np
import pandas as pd
import pytest
from cash_cow.data import ROOT
from cash_cow.intraday.data import load_sample,validate_bars
from cash_cow.intraday.signals import features,decisions
from cash_cow.intraday.engine import simulate,settlement_dates

C=json.loads((ROOT/'configs/experiment_v3.json').read_text())

@pytest.fixture(scope='module')
def data():return load_sample()[:2]

def test_sample_is_complete_and_early_close_is_identified(data):
    f,d=data
    assert len(f)==49350
    assert len(f.loc['2022-11-25'])==210
    assert len(d)==127

def test_missing_minute_is_rejected(data):
    f,d=data
    with pytest.raises(ValueError,match='incomplete'):validate_bars(f.drop(f.index[300]),d)

@pytest.mark.parametrize('spec',C['rules'],ids=lambda s:s['id'])
def test_future_changes_cannot_change_past_signals(data,spec):
    f,d=data;a=features(f,d,C);expected=decisions(a,spec)
    cut=pd.Timestamp('2022-09-20 12:00',tz='America/New_York')
    f=f.copy();d=d.copy();f.loc[cut:,['open','high','low','close','volume']]*=2
    d.loc['2022-09-20':,['open','high','low','close']]*=2
    actual=decisions(features(f,d,C),spec)
    pd.testing.assert_series_equal(expected.loc[:cut-pd.Timedelta(minutes=1)],actual.loc[:cut-pd.Timedelta(minutes=1)])

def synthetic():
    idx=pd.DatetimeIndex([])
    for day in ['2022-08-01','2022-08-02','2022-08-03']:
        idx=idx.append(pd.date_range(day+' 09:30',periods=390,freq='min',tz='America/New_York'))
    f=pd.DataFrame({'open':100.,'high':100.,'low':100.,'close':100.,'volume':100000.,'daily_vol':.01},index=idx)
    f['day']=pd.DatetimeIndex(f.index.date)
    signal=pd.Series(np.nan,index=idx);signal.loc[idx[idx.hour==10][idx[idx.hour==10].minute==0]]=1
    s=dict(C['base'],capital=2000,slippage_bps=0,commission_per_share=0,minimum_commission=0,borrow_annual_rate=0,allocation=1)
    return f,signal,s

def test_next_bar_plus_latency_and_cash_settlement():
    f,w,s=synthetic();spec=C['rules'][0]
    r=simulate(f,w,spec,s,C,'cash_long_only')
    buys=r.trades[r.trades.quantity>0]
    assert list(buys.timestamp.dt.strftime('%Y-%m-%d %H:%M'))==['2022-08-01 10:02','2022-08-03 10:02']
    assert r.path.cash.min()>=0
    assert np.allclose(r.path.equity,2000)
    assert r.path.groupby(r.path.index.date).position.last().eq(0).all()

def test_short_disabled_in_cash_but_allowed_in_reference():
    f,w,s=synthetic();w.loc[w.notna()]=-1
    cash=simulate(f,w,C['rules'][0],s,C,'cash_long_only')
    ref=simulate(f,w,C['rules'][0],s,C,'hypothetical_margin_long_short')
    assert cash.trades.empty
    assert ref.path.position.min()<0
    assert np.allclose(ref.path.equity,2000)

def test_both_sides_charge_fees_and_slippage():
    f,w,s=synthetic();s.update(slippage_bps=10,minimum_commission=.4)
    r=simulate(f,w,C['rules'][0],s,C,'cash_long_only')
    q=r.trades.quantity.abs().sum()
    assert r.path.equity.iloc[-1]==pytest.approx(2000-len(r.trades)*.4-q*.1)

def test_future_fill_volume_not_used():
    f,w,s=synthetic();a=simulate(f,w,C['rules'][0],s,C,'hypothetical_margin_long_short')
    f.loc['2022-08-01 10:02','volume']=1
    b=simulate(f,w,C['rules'][0],s,C,'hypothetical_margin_long_short')
    assert a.trades.iloc[0].quantity==b.trades.iloc[0].quantity

def test_settlement_regimes_and_bank_holiday_buffer():
    dates=settlement_dates('2022-10-06','2022-10-13')
    assert dates[pd.Timestamp('2022-10-07')]==pd.Timestamp('2022-10-12')
    assert settlement_dates('2024-05-28','2024-05-29')[pd.Timestamp('2024-05-28')]==pd.Timestamp('2024-05-29')

def test_noise_band_uses_previous_fourteen_sessions(data):
    f,d=data;a=features(f,d,C);at=pd.Timestamp('2022-08-01 10:29',tz='America/New_York')
    prior=a[(a.minute==59)&(a.index<at)].tail(14)
    assert a.loc[at,'sigma']==pytest.approx(prior.move.mean())

def test_no_trading_on_half_day(data):
    f,d=data;a=features(f,d,C)
    for spec in C['rules']:assert decisions(a,spec).loc['2022-11-25'].isna().all()
