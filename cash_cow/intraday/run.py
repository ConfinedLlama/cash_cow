"""Frozen intraday pilot: every variant retained, no parameter search."""
from datetime import datetime, timezone
import json
import platform
import numpy as np
import pandas as pd
from cash_cow.data import ROOT, sha256
from .data import load_sample
from .signals import features, decisions
from .engine import simulate, metrics, monthly

def reconcile(result, frame, settings, account):
    """Derive NAV independently from signed fills and marks, not engine cash."""
    p=result.path; t=result.trades
    flows=pd.Series(0.,index=p.index);quantities=flows.copy()
    if not t.empty:
        flow=(-t.quantity*t.price-t.fee).groupby(t.timestamp).sum()
        qty=t.quantity.groupby(t.timestamp).sum()
        flows.loc[flow.index]=flow;quantities.loc[qty.index]=qty
        assert (t.timestamp>=t.signal_available).all()
        assert (t.quantity!=0).all()
        assert np.isclose(t.fee.sum(),p.fees.iloc[-1])
    positions=quantities.cumsum()
    expected=settings['capital']+flows.cumsum()+positions*frame.close-p.borrow-p.overhead
    error=float((expected-p.equity).abs().max())
    assert error<1e-6,error
    assert np.allclose(positions,p.position)
    assert p.groupby(p.index.date).position.last().eq(0).all()
    if account=='cash_long_only':
        assert p.cash.min()>=-1e-6 and p.position.min()>=-1e-6
        assert np.allclose(p.cash+p.receivables+p.position*frame.close,p.equity)
    return error

def main():
    c=json.loads((ROOT/'configs/experiment_v3.json').read_text())
    bars,daily,provenance=load_sample()
    feat=features(bars,daily,c)
    selected=feat[(feat.day>=pd.Timestamp(c['evaluation_start']))&(feat.day<=pd.Timestamp(c['evaluation_end']))]
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_v3_intraday_pilot'
    out=ROOT/'reports/runs'/run_id;out.mkdir(parents=True)
    for name in ['paths','trades','monthly']:(out/name).mkdir()
    sources={str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'cash_cow').rglob('*.py'))}
    manifest={'status':'running','run_id':run_id,'config':c,'config_sha256':sha256(ROOT/'configs/experiment_v3.json'),
              'data':provenance,'sources':sources,'python':platform.python_version(),'live_approved':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    specs=c['rules']+c['benchmarks'];signals={s['id']:decisions(feat,s) for s in specs}
    rows=[];allmonthly={};errors=[]
    def run_one(account,scenario,spec,settings):
        tag=account+'__'+scenario+'__'+spec['id']
        result=simulate(selected,signals[spec['id']],spec,settings,c,account)
        errors.append(reconcile(result,selected,settings,account))
        rows.append({'account':account,'scenario':scenario,'strategy':spec['id'],'capital':settings['capital'],**metrics(result,settings['capital'],c['target_monthly'])})
        result.path.to_csv(out/'paths'/f'{tag}.csv.gz',compression='gzip')
        result.trades.to_csv(out/'trades'/f'{tag}.csv',index=False)
        r=monthly(result.path,settings['capital']);r.rename('return').to_csv(out/'monthly'/f'{tag}.csv');allmonthly[tag]=r
    for account in c['account_models']:
        for scenario in c['scenarios']:
            settings=dict(c['base'],capital=c['capital']);settings.update({k:v for k,v in scenario.items() if k!='id'})
            for spec in specs:run_one(account,scenario['id'],spec,settings)
            print('Completed',account,scenario['id'],flush=True)
    for spec in c['rules']:
        settings=dict(c['base'],capital=c['capital']);settings.update(c['paper_cost_diagnostic'])
        run_one('hypothetical_margin_long_short','paper_cost_diagnostic',spec,settings)
        settings=dict(c['base'],capital=c['capital']);settings.update(c['modern_cash_diagnostic'])
        run_one('cash_long_only','modern_T1_counterfactual',spec,settings)
    summary=pd.DataFrame(rows);summary.to_csv(out/'summary.csv',index=False)
    pd.DataFrame(allmonthly).to_csv(out/'monthly_returns.csv')
    base=summary[summary.scenario=='01_base']
    lines=['| Account / rule | Compounded month | Worst month | Minute-close drawdown | Orders |', '|---|---:|---:|---:|---:|']
    for _,r in base.sort_values(['account','geometric_month'],ascending=[True,False]).iterrows():
        lines.append(f'| {r.account} / {r.strategy} | {r.geometric_month:.2%} | {r.worst_month:.2%} | {r.max_drawdown:.2%} | {r.orders} |')
    table='\n'.join(lines)
    report=f'''# Intraday pilot results

Run `{run_id}`. HistoricalData.net SPY sample. Evaluation **August–December 2022: five months**; July supplies warm-up. Availability-selected historical pilot, not fresh validation. No live approval.

Six candidate rules × ten scenarios × two account models = 120 candidate simulations. Three intraday/cash benchmarks × ten × two = 60 benchmarks. Six additional $100,000 paper-cost diagnostics and six modern T+1 cash-settlement counterfactuals. **192 completed runs**. Overlapping scenarios are not independent market histories. Hypothetical margin results cannot be treated as executable returns for the user's $2,000 account.

{table}

## Mechanics and limits

- Raw minute OHLCV, New York timezone with DST, independently checked exchange calendar. All 49,350 regular bars across 127 input sessions passed coverage checks. One early-close day is deliberately flat. No forward-filled missing bars.
- Decisions use completed bars. Base execution waits one additional full minute: a 15:29 bar completes at 15:30 and fills at 15:31 open plus adverse slippage. End-of-day flatten is scheduled at 15:59 open, avoiding a fictional closing-auction fill.
- Gao first-half-hour direction includes the overnight move; penultimate-half-hour agreement and prior-20-session opening-volume median filters are declared adaptations. Noise rules use prior 14 same-clock moves, 30-minute decisions, opposite-band or current-band/VWAP exits. Volatility sizing uses previous 14 daily returns and a 2% daily target capped at 4× in the hypothetical account. No optimizer.
- VWAP uses cumulative HLC3×volume because the sample's minute VWAP field is blank. Both accounts are adaptations, not exact reproductions of published performance.
- Cash account: long-only, at most 95% target exposure, no proceeds reuse before settlement. Historical T+2 in this sample, with a conservative bank-holiday buffer. Whole shares in base. Margin diagnostic permits shorts and immediate capital reuse. Broker eligibility, PDT, locate, short-sale price restrictions and borrowing availability are not modeled. A 25% maintenance threshold triggers next-bar liquidation, not a broker-certified margin model.
- Base costs: one-way slippage 2 bp, fees max($0.40, $0.0035/share), 3% annual intraday financing/borrow proxy. FX, exact exchange/regulatory/GST charges and paid data expense are excluded. $10 monthly overhead is a separate sensitivity. Entry liquidity uses at most 1% of the preceding completed minute's volume; closing fills assume full availability at stressed prices.
- Drawdowns use minute closes and cannot capture every intraminute extreme. Exposure stops are not guaranteed loss caps.
- Only five evaluation months: no annualized Sharpe, inferential confidence interval, significance claim or long-run forecast is produced. Check both compounded growth and the count of actual months reaching 10%.

Every result is retained in `summary.csv`, every monthly return in `monthly_returns.csv`, and detailed paths/trades in local ignored subfolders. `VERIFICATION.json` checks every NAV path against signed fills. See `docs/INTRADAY_V3.md` for sources and multi-year data requirements. 2025+ price bars remain unfetched.
'''
    (out/'RESULTS.md').write_text(report)
    audit={'status':'passed','runs':len(errors),'total_orders':int(summary.orders.sum()),'maximum_nav_reconciliation_error':max(errors),
           'all_flat_overnight':True,'all_cash_accounts_nonnegative_and_long_only':True,'all_fills_at_or_after_signal_available':True,
           'limits':'Internal ledger reconciliation and sample validation, not independently verified execution or statistical edge.'}
    (out/'VERIFICATION.json').write_text(json.dumps(audit,indent=2)+'\n')
    plot(base,c,out)
    manifest.update(status='complete',completed_simulations=len(rows));(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'reports/LATEST_V3.txt').write_text(str(out.relative_to(ROOT))+'\n')
    print(table);print('Report:',out/'RESULTS.md')

def plot(base,c,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names=[s['id'] for s in c['rules']];pos=np.arange(len(names));fig,ax=plt.subplots(figsize=(11,6))
    colors=['#245e9a','#d08a2f']
    for k,account in enumerate(c['account_models']):
        b=base[base.account==account].set_index('strategy').loc[names]
        ax.barh(pos+(k-.5)*.34,b.geometric_month*100,height=.32,label='Cash $2k, long-only' if k==0 else 'Hypothetical margin $2k, long/short',color=colors[k])
    ax.set_yticks(pos,labels=names);ax.invert_yaxis();ax.axvline(10,color='#aa2222',linestyle='--',label='Requested 10% monthly')
    ax.set_xlabel('Compounded monthly return (%) · only five evaluation months')
    ax.set_title('Intraday pilot · August–December 2022\nHistoricalData.net sample; assumed costs; no live track record')
    ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True);ax.legend(fontsize=8,loc='lower right');fig.tight_layout()
    fig.savefig(out/'intraday_comparison.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
