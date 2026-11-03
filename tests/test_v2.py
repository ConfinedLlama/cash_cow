import json
import numpy as np
import pandas as pd
import pytest
from cash_cow.data import ROOT
from cash_cow.data_v2 import restore_nominal
from cash_cow.strategies_v2 import make_signals_v2
from cash_cow.run_v2 import block_inference, extended_metrics, benchmark_for
from cash_cow.engine import Simulation

C = json.loads((ROOT/'configs/experiment_v2.json').read_text())

def histories(n=900):
    rng = np.random.default_rng(818)
    dates = pd.bdate_range('2006-01-01', periods=n)
    frames = {}
    for symbol in C['symbols']:
        p = 100*np.exp(np.cumsum(rng.normal(.0002, .015, n)))
        frames[symbol] = pd.DataFrame({'Signal':p, 'SplitClose':p}, index=dates)
    return frames

@pytest.mark.parametrize('spec', C['strategies'], ids=lambda s:s['id'])
def test_v2_no_future_information(spec):
    f = histories()
    expected = make_signals_v2(f, spec, C['sectors'])
    for frame in f.values():
        frame.iloc[820:] *= 20
    actual = make_signals_v2(f, spec, C['sectors'])
    pd.testing.assert_frame_equal(expected.iloc[:820], actual.iloc[:820])
    assert (actual.sum(axis=1) <= .95+1e-10).all()
    assert (actual >= 0).all().all()

def test_split_restoration_and_capital_gains_not_double_counted():
    f = pd.DataFrame({k:[25.,25.,25.] for k in ['Open','High','Low','Close']},
                     index=pd.bdate_range('2020-01-01', periods=3))
    f['Stock Splits'] = [0.,2.,0.]
    f['Dividends'] = [0.,.5,0.]
    f['Capital Gains'] = [0.,.25,0.]
    r = restore_nominal(f, 2)
    assert r.Close.tolist() == [100.,50.,50.]
    assert r.Dividends.tolist() == [0.,1.5,0.]
    assert r.Signal.iloc[1]/r.Signal.iloc[0]-1 == pytest.approx(.03)

def test_spin_off_does_not_create_parent_shares():
    dates = pd.bdate_range('2020-01-01', periods=3)
    f = pd.DataFrame({k:[80.,80.,80.] for k in ['Open','High','Low','Close']}, index=dates)
    f['Stock Splits'] = [0.,1.25,0.]
    f['Dividends'] = 0.
    r = restore_nominal(f, cash_proxies={str(dates[1].date()):20.})
    assert r.Close.tolist() == [100.,80.,80.]
    assert r['Stock Splits'].eq(0).all()
    assert r.Dividends.iloc[1] == 20
    assert np.allclose(r.Signal, 100)

def test_inverse_variance_not_inverse_standard_deviation():
    f = histories(100)
    spec = next(s for s in C['strategies'] if s['id']=='inverse_variance_tqqq')
    a = make_signals_v2(f, spec, C['sectors'])
    variance = f['QQQ'].Signal.pct_change().iloc[-21:].var()*252
    assert a.TQQQ.iloc[-1] == pytest.approx(min(.95,.3**2/variance/3))

def test_intermediate_momentum_ignores_recent_six_months():
    f = histories(900)
    spec = next(s for s in C['strategies'] if s['id']=='intermediate_mom12_7')
    a = make_signals_v2(f, spec, C['sectors'])
    for frame in f.values(): frame.iloc[-126:] *= 17
    b = make_signals_v2(f, spec, C['sectors'])
    pd.testing.assert_series_equal(a.iloc[-1], b.iloc[-1])

def test_bootstrap_null_and_reproducibility():
    assert block_inference(np.zeros(108),100,3,1)['one_sided_p'] == 1
    x = np.array([.01,-.03,.02]*36)
    assert block_inference(x,100,3,1) == block_inference(x,100,3,1)

def test_target_uses_compounded_growth_not_arithmetic_mean():
    # +50%, -30% averages +10%, but compound growth is only sqrt(1.05)-1.
    index = pd.to_datetime(['2020-01-31','2020-02-28'])
    p = pd.DataFrame({'equity':[1500.,1050.], 'fees':0.,'slippage_cost':0.,
                      'overhead':0.,'withheld_dividends':0.,'exposure':1.}, index=index)
    m = extended_metrics(Simulation(p,pd.DataFrame()),1000,.1)
    assert m['mean_month'] == pytest.approx(.1)
    assert m['geometric_month'] == pytest.approx(np.sqrt(1.05)-1)
    assert m['target_hit_months'] == 1
    assert m['target_ending_equity'] == pytest.approx(1210)

def test_leveraged_timing_has_leveraged_comparator():
    for spec in C['strategies']:
        if spec.get('instrument') == 'TQQQ': assert benchmark_for(spec)=='tqqq95_hold'
        if spec.get('instrument') == 'UPRO': assert benchmark_for(spec)=='upro95_hold'
