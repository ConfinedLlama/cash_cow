import numpy as np
import pandas as pd
import pytest
from cash_cow.engine import simulate, monthly_returns
from cash_cow.run import holm, paired_bootstrap
from cash_cow.strategies import make_signals, CADENCE

def fixtures(n=12, symbols=('SPY',)):
    idx = pd.bdate_range('2020-01-01', periods=n)
    frames = {s: pd.DataFrame({'Open': 100., 'High': 100., 'Low': 100., 'Close': 100.,
                               'Dividends': 0., 'Stock Splits': 0., 'Signal': 100.}, index=idx) for s in symbols}
    signals = pd.DataFrame(0., index=idx, columns=symbols)
    settings = dict(capital=1000, one_way_slippage_bps=0, commission_per_order=0,
                    whole_shares=False, monthly_overhead=0, extra_signal_delay_sessions=0,
                    all_dividends_withholding=False, dividend_cash_delay_sessions=3, settlement_sessions=3)
    return idx, frames, signals, settings

def test_flat_prices_preserve_nav_and_cash_no_leverage():
    dates, f, w, s = fixtures()
    w['SPY'] = 0.5
    sim = simulate(f, w, 'donchian', s, dates[1], dates[-1])
    assert np.allclose(sim.path.equity, 1000)
    assert np.allclose(sim.path.settled_cash, 500)
    assert len(sim.trades) == 1

def test_signal_cannot_trade_at_same_close():
    dates, f, w, s = fixtures()
    w.loc[dates[2]:, 'SPY'] = 0.5
    sim = simulate(f, w, 'donchian', s, dates[1], dates[-1])
    assert sim.trades.iloc[0]['date'] == dates[3]
    assert sim.trades.iloc[0]['signal_date'] == dates[2]

def test_extra_delay_is_applied():
    dates, f, w, s = fixtures()
    w.loc[dates[3]:, 'SPY'] = 0.5
    s['extra_signal_delay_sessions'] = 2
    sim = simulate(f, w, 'donchian', s, dates[3], dates[-1])
    assert sim.trades.iloc[0]['date'] == dates[6]

def test_sale_proceeds_cannot_be_spent_until_settled():
    dates, f, w, s = fixtures(symbols=('SPY', 'QQQ'))
    w.loc[:dates[2], 'SPY'] = 1.0
    w.loc[dates[3]:, 'QQQ'] = 1.0
    sim = simulate(f, w, 'donchian', s, dates[1], dates[-1])
    sell = sim.trades.query('side == "SELL"').iloc[0]
    buy = sim.trades.query('symbol == "QQQ"').iloc[0]
    assert sell['date'] == dates[4]
    assert buy['date'] == dates[7]
    assert sim.path.settled_cash.min() >= 0
    assert np.allclose(sim.path.equity, 1000)

def test_dividend_entitlement_tax_and_delayed_cash():
    dates, f, w, s = fixtures()
    w['SPY'] = 0.5
    f['SPY'].loc[dates[3]:, ['Open', 'High', 'Low', 'Close']] = 99
    f['SPY'].loc[dates[3], 'Dividends'] = 1
    sim = simulate(f, w, 'donchian', s, dates[1], dates[-1])
    assert sim.path.loc[dates[3], 'equity'] == pytest.approx(998.5)
    assert sim.path.loc[dates[3], 'settled_cash'] == pytest.approx(500)
    assert sim.path.loc[dates[3], 'receivables'] == pytest.approx(3.5)
    assert sim.path.loc[dates[6], 'settled_cash'] == pytest.approx(503.5)

def test_split_preserves_nav():
    dates, f, w, s = fixtures()
    w['SPY'] = 0.5
    f['SPY'].loc[dates[3]:, ['Open', 'High', 'Low', 'Close']] = 50
    f['SPY'].loc[dates[3], 'Stock Splits'] = 2
    sim = simulate(f, w, 'donchian', s, dates[1], dates[-1])
    assert np.allclose(sim.path.equity, 1000)
    assert len(sim.trades) == 1

def test_fees_and_slippage_are_charged_both_sides():
    dates, f, w, s = fixtures()
    w.loc[:dates[2], 'SPY'] = 0.5
    s.update(commission_per_order=1, one_way_slippage_bps=100)
    sim = simulate(f, w, 'donchian', s, dates[1], dates[-1])
    quantity = sim.trades.iloc[0]['quantity']
    assert sim.path.equity.iloc[-1] == pytest.approx(1000 - 2 - quantity * 2)
    assert sim.path.fees.iloc[-1] == 2

def test_whole_share_and_initial_month_accounting():
    dates, f, w, s = fixtures()
    s['whole_shares'] = True
    w['SPY'] = 0.25
    f['SPY'].loc[dates[1]:, ['Open', 'High', 'Low', 'Close']] = 110
    sim = simulate(f, w, 'donchian', s, dates[1], dates[-1])
    assert sim.trades.iloc[0]['quantity'] == 2
    assert monthly_returns(sim.path, 1000).iloc[0] == pytest.approx(0)

def test_overhead_can_force_sale_without_borrowing_or_hiding_cost():
    dates, f, w, s = fixtures(n=60)
    s['monthly_overhead'] = 10
    w['SPY'] = 1.0
    sim = simulate(f, w, 'bills_100', s, dates[1], dates[-1])
    months = len(sim.path.index.to_period('M').unique())
    assert sim.path.equity.iloc[-1] == pytest.approx(1000 - months * 10)
    assert sim.path.settled_cash.min() >= 0
    assert (sim.trades.side == 'SELL').any()
    assert sim.path.overhead_payable.max() == pytest.approx(10)

@pytest.mark.parametrize('strategy', list(CADENCE))
def test_signals_do_not_change_when_future_prices_change(strategy):
    symbols = ('SPY','QQQ','IWM','EFA','IEF','TLT','GLD','SHY','BIL')
    dates, f, _, _ = fixtures(400, symbols)
    rng = np.random.default_rng(27)
    for frame in f.values():
        frame['Signal'] = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 400)))
    expected = make_signals(f, strategy)
    for frame in f.values():
        frame.loc[dates[320]:, 'Signal'] *= 5
    actual = make_signals(f, strategy)
    pd.testing.assert_frame_equal(expected.iloc[:320], actual.iloc[:320])

def test_multiple_testing_correction():
    assert np.allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])

def test_zero_excess_not_significant_and_bootstrap_reproducible():
    x = pd.Series([0.01, -0.02, 0.03] * 36)
    a = paired_bootstrap(x, x, 100, 3, 123)
    assert a['one_sided_bootstrap_p'] == 1
    assert a == paired_bootstrap(x, x, 100, 3, 123)
