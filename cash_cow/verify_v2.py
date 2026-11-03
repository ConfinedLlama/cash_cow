"""Reconcile exported trades and corporate actions independently against all NAV paths."""
import json
import numpy as np
import pandas as pd
from .data import ROOT, sha256
from .data_v2 import load_v2

def main():
    out = ROOT/(ROOT/'reports/LATEST_V2.txt').read_text().strip()
    manifest = json.loads((out/'manifest.json').read_text())
    c = manifest['config']; frames,_ = load_v2(c)
    summary = pd.read_csv(out/'summary.csv')
    checked = 0; maximum_error = 0.; trade_count = 0
    for _,row in summary.iterrows():
        earlier = row.window == 'earlier_2011_2015'
        tag = ('earlier' if earlier else row.scenario)+'__'+row.strategy
        path = pd.read_csv(out/'paths'/f'{tag}.csv',index_col=0,parse_dates=True)
        trades = pd.read_csv(out/'trades'/f'{tag}.csv',parse_dates=['date','signal_date'])
        scenario = next(s for s in c['scenarios'] if s['name']==row.scenario)
        s = dict(c['base'],capital=c['capital']);s.update(scenario)
        symbols = c['symbols']; dates = frames['SPY'].index
        position = np.zeros(len(symbols)); credits=[]; buy_spend=0.; fees=0.; withheld=0.
        groups = {d:g for d,g in trades.groupby('date')}
        close = pd.DataFrame({k:frames[k].Close for k in symbols}).reindex(path.index).to_numpy()
        opening = pd.DataFrame({k:frames[k].Open for k in symbols}).reindex(path.index).to_numpy()
        split = pd.DataFrame({k:frames[k]['Stock Splits'] for k in symbols}).reindex(path.index).replace(0,1).to_numpy()
        div = pd.DataFrame({k:frames[k].Dividends for k in symbols}).reindex(path.index).to_numpy()
        tax = np.array([.3 if k!='BIL' or s['all_dividends_withholding'] else 0. for k in symbols])
        for n,(date,record) in enumerate(path.iterrows()):
            i = dates.get_loc(date)
            position *= split[n]
            gross = position*div[n]
            withheld += float(gross@tax)
            net = float(gross@(1-tax))
            if net: credits.append((i+s['dividend_cash_delay_sessions'],net))
            if date in groups:
                for trade in groups[date].itertuples():
                    a=symbols.index(trade.symbol); quantity=trade.quantity
                    assert quantity>0 and trade.signal_date<date
                    sign=1 if trade.side=='BUY' else -1
                    expected_price=opening[n,a]*(1+sign*s['one_way_slippage_bps']/10000)
                    assert np.isclose(trade.price,expected_price,rtol=1e-10)
                    assert np.isclose(trade.fee,s['commission_per_order'])
                    position[a]+=sign*quantity; fees+=trade.fee
                    if sign==1: buy_spend+=quantity*trade.price+trade.fee
                    else: credits.append((i+s['settlement_sessions'],quantity*trade.price-trade.fee))
            assert position.min()>-1e-7
            matured=sum(value for release,value in credits if release<=i)
            pending=sum(value for release,value in credits if release>i)
            months=len(path.index[:n+1].to_period('M').unique())
            expense=months*s['monthly_overhead']
            paid=expense-record.overhead_payable
            cash=s['capital']-buy_spend+matured-paid
            invested=position@close[n]
            expected=cash+pending+invested-record.overhead_payable
            errors=[abs(expected-record.equity),abs(cash-record.settled_cash),
                    abs(pending-record.receivables),abs(fees-record.fees),
                    abs(withheld-record.withheld_dividends),abs(expense-record.overhead)]
            maximum_error=max(maximum_error,max(errors))
            assert max(errors)<1e-5,(tag,date,errors)
            assert cash>=-1e-6
        r=path.equity.resample('ME').last().pct_change()
        r.iloc[0]=path.equity.resample('ME').last().iloc[0]/s['capital']-1
        assert len(r)==row.months
        assert np.isclose(path.equity.iloc[-1],row.ending_equity)
        assert np.isclose(np.expm1(np.log1p(r).mean()),row.geometric_month)
        assert int((r>=c['target_monthly_return']).sum())==row.target_hit_months
        assert np.isclose((path.equity/path.equity.cummax().clip(lower=s['capital'])-1).min(),row.max_drawdown)
        checked+=1;trade_count+=len(trades)
    assert checked==209
    assert all(sha256(ROOT/k)==v for k,v in manifest['sources'].items())
    assert sha256(ROOT/'configs/experiment_v2.json')==manifest['config_sha256']
    assert all(sha256(ROOT/'data/raw'/f'{k}.csv')==v['sha256'] for k,v in manifest['data']['files'].items())
    result={'status':'passed','simulations_reconciled':checked,'trade_records_reconciled':trade_count,
            'maximum_absolute_currency_error':maximum_error,'run_source_config_data_hashes_match':True,
            'verifier_sha256':sha256(Path(__file__)),
            'limits':'Internal accounting and provenance audit, not an independent market-data audit or proof of executable fills.'}
    (out/'VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    from pathlib import Path
    main()
