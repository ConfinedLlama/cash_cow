"""Higher-risk historical screen, with target and matched-benchmark inference."""
import argparse
from datetime import datetime,timezone
import json
import platform
import time
import numpy as np
import pandas as pd
from .data import ROOT,sha256
from .data_v2 import fetch_v2,load_v2
from .engine import simulate,metrics,monthly_returns
from .strategies_v2 import make_signals_v2

def block_inference(x, samples, block, seed):
    x=np.asarray(x,dtype=float)
    if len(x)<block or not np.isfinite(x).all():
        raise ValueError('Invalid inference series')
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,len(x),(samples,int(np.ceil(len(x)/block))))
    ids=((starts[:,:,None]+np.arange(block))%len(x)).reshape(samples,-1)[:,:len(x)]
    means=x[ids].mean(axis=1)
    obs=x.mean()
    return {'mean':float(obs),'ci95_low':float(np.quantile(means,.025)),
            'ci95_high':float(np.quantile(means,.975)),
            'one_sided_p':float((1+((means-obs)>=obs).sum())/(samples+1))}

def extended_metrics(sim,capital,target):
    r=monthly_returns(sim.path,capital)
    m=metrics(sim,capital)
    longest=current=0
    for v in r:
        current=current+1 if v<0 else 0
        longest=max(longest,current)
    rolling=(1+r).rolling(12).apply(np.prod,raw=True)**(1/12)-1
    m.update(geometric_month=float(np.expm1(np.log1p(r).mean())),
             target_hit_months=int((r>=target).sum()),target_hit_fraction=float((r>=target).mean()),
             worst_12m_geometric_month=float(rolling.min()),longest_losing_month_streak=longest,
             target_ending_equity=capital*(1+target)**len(r))
    return m

def benchmark_for(spec):
    if spec.get('instrument')=='TQQQ' or spec['id']=='relative_mom_3x':
        return 'tqqq95_hold'
    if spec.get('instrument')=='UPRO':
        return 'upro95_hold'
    return 'spy95_hold'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fetch',action='store_true')
    args=parser.parse_args()
    c=json.loads((ROOT/'configs/experiment_v2.json').read_text())
    if args.fetch:fetch_v2(c)
    frames,data_manifest=load_v2(c)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_v2_papers'
    out=ROOT/'reports/runs'/run_id
    out.mkdir(parents=True,exist_ok=False)
    for d in ('paths','trades','monthly'):(out/d).mkdir()
    manifest={'run_id':run_id,'config':c,'config_sha256':sha256(ROOT/'configs/experiment_v2.json'),
              'sources':{str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'cash_cow').glob('*.py'))},
              'data':data_manifest,'python':platform.python_version(),'status':'running','live_approved':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows,cache,base_paths,base_months,regime_rows=[],{},{},{},[]
    timer=time.monotonic()
    specs=c['strategies']+c['benchmarks']
    for scenario in c['scenarios']:
        settings=dict(c['base'],capital=c['capital'])
        settings.update({k:v for k,v in scenario.items() if k!='name'})
        settings['taxable_symbols']=[s for s in c['symbols'] if s!='BIL']
        for spec in specs:
            name=spec['id']; settings['cadence']=spec['cadence']
            key=(name,settings['exposure_cap'])
            if key not in cache:cache[key]=make_signals_v2(frames,spec,c['sectors'],settings['exposure_cap'])
            sim=simulate(frames,cache[key],name,settings,c['validation_start'],c['validation_end'])
            m=extended_metrics(sim,settings['capital'],c['target_monthly_return'])
            rows.append({'scenario':scenario['name'],'strategy':name,'window':'retrospective_2016_2024',**m})
            tag=scenario['name']+'__'+name
            sim.path.to_csv(out/'paths'/f'{tag}.csv')
            sim.trades.to_csv(out/'trades'/f'{tag}.csv',index=False)
            month=monthly_returns(sim.path,settings['capital'])
            month.rename('return').to_csv(out/'monthly'/f'{tag}.csv')
            if scenario['name']=='01_base':
                base_paths[name]=sim.path; base_months[name]=month
                # Earlier disjoint window; still retrospective because rules were chosen in 2026.
                earlier=simulate(frames,cache[key],name,settings,c['development_start'],c['development_end'])
                earlier.path.to_csv(out/'paths'/f'earlier__{name}.csv')
                earlier.trades.to_csv(out/'trades'/f'earlier__{name}.csv',index=False)
                monthly_returns(earlier.path,settings['capital']).rename('return').to_csv(out/'monthly'/f'earlier__{name}.csv')
                rows.append({'scenario':scenario['name'],'strategy':name,'window':'earlier_2011_2015',**extended_metrics(earlier,settings['capital'],c['target_monthly_return'])})
                for first,last in [('2016','2018'),('2019','2021'),('2022','2024')]:
                    r=month.loc[first:last]
                    regime_rows.append({'strategy':name,'period':first+'-'+last,'geometric_month':float(np.expm1(np.log1p(r).mean())),
                                        'worst_month':float(r.min()),'target_hits':int((r>=c['target_monthly_return']).sum())})
        print('Completed v2',scenario['name'],flush=True)
    results=pd.DataFrame(rows); results.to_csv(out/'summary.csv',index=False)
    pd.DataFrame(base_months).to_csv(out/'base_monthly.csv')
    pd.DataFrame(regime_rows).to_csv(out/'subperiods.csv',index=False)
    inference=[]; st=c['statistics']; correction=2*(st['prior_candidate_count']+st['new_candidate_count'])
    for spec in c['strategies']:
        name=spec['id']; matched=benchmark_for(spec); r=base_months[name]
        excess=block_inference(r-base_months[matched],st['bootstrap_samples'],st['block_months'],st['seed'])
        target=block_inference(np.log1p(r)-np.log1p(c['target_monthly_return']),st['bootstrap_samples'],st['block_months'],st['seed'])
        inference.append({'strategy':name,'matched_benchmark':matched,
            **{'excess_'+k:v for k,v in excess.items()},**{'target_log_'+k:v for k,v in target.items()},
            'excess_p_adjusted':min(1,excess['one_sided_p']*correction),'target_p_adjusted':min(1,target['one_sided_p']*correction)})
    pd.DataFrame(inference).to_csv(out/'inference.csv',index=False)
    base=results[(results.scenario=='01_base')&(results.window=='retrospective_2016_2024')].sort_values('geometric_month',ascending=False)
    table=['| Strategy | Geometric month | Average month | Months ≥10% | Worst month | Max drawdown |',
           '|---|---:|---:|---:|---:|---:|']
    for _,r in base.iterrows():
        table.append(f'| {r.strategy} | {r.geometric_month:.2%} | {r.mean_month:.2%} | {r.target_hit_months}/108 | {r.worst_month:.2%} | {r.max_drawdown:.2%} |')
    table='\n'.join(table)
    report=f'''# V2: higher-risk paper-based strategy adaptations

Research date: {c['research_date']}. Run `{run_id}`. **Historical research only. No live approval.**

Completed {len(c['strategies'])*len(c['scenarios'])} candidate/scenario simulations, {len(c['benchmarks'])*len(c['scenarios'])} benchmark simulations and {len(specs)} earlier-period diagnostics. Each run starts with its own $2,000 account, except the $1,000 sensitivity. Ten scenarios are overlapping sensitivities, not independent market histories.

The user authorized higher-risk research. Candidate allocation increased from 25% to 95% at scheduled rebalances; actual leveraged ETFs can add approximately 3× daily underlying exposure. This does not authorize a funded allocation. No borrowing or short sale is simulated; leverage is embedded in the ETF.

## Monthly target check

10% compounded monthly is {(1.1**12-1):.1%} a year. A $2,000 account compounding at that rate for this 108-month sample would reach ${2000*1.1**108:,.0f}. Geometric monthly return measures compounded growth; arithmetic mean can be substantially inflated by volatile outcomes. Target-hit counts distinguish occasional big months from sustained growth.

{table}

Base includes assumed slippage and per-order fees, 30% withholding on non-BIL cash distributions, and zero idle-cash interest. It excludes recurring overhead and FX; those limits still matter. The $10/month sensitivity is separate. Benchmark holdings start at 95%, then drift and retain distributions as cash.

## What was actually tested

Twelve **ETF adaptations** grounded in nine named paper sources: relative/industry/intermediate momentum, 52-week-high proximity, short/long reversal, time-series momentum, tactical trend and volatility management. Several variants share exposure. These are not exact reproductions of stock-level long-short or futures portfolios. The paper-to-code mapping, changes and data-dependent deferrals are in `docs/PAPERS_V2.md`.

Actual QLD/TQQQ/UPRO histories are used; no annual/monthly return is simply multiplied by leverage. Fund expenses and embedded financing effects are already reflected in those histories. Corporate cash distributions are accounted separately. Known 2025 split facts restore nominal historical units without fetching post-2024 price bars.

XLF's 2016 spin-off is represented by a documented $4.443564 cash-equivalent receivable per original share, conservatively taxed, rather than the vendor's fictitious 1.231 parent-share split. This is an approximation to disposing of the XLRE distribution; actual XLRE prices, payment dates and sale costs are not reconstructed. Sector results remain provisional for this reason.

## Interpretation and controls

- 2016–2024 is a **reused retrospective sample** already examined in v1. It is not a fresh out-of-sample test. 2011–2015 is separately reported; neither window is prospective.
- No parameter optimization or post-result strategy removal. All twelve candidates and seven benchmarks are retained. The trial registry records the scope change.
- `inference.csv` reports a paired 3-month block-bootstrap excess comparison versus a relevant passive benchmark, and a log-growth test against 10% monthly. A Bonferroni factor of {correction} accounts for two hypothesis families across 22 declared v1/v2 candidate slots. It does not eliminate adaptive research, unrecorded choices or regime uncertainty. P-values are exploratory.
- Securities-sector composition changes, selection of surviving fund families, one-vendor revisions, share-split assumptions, and simplified fills/settlement/payable dates remain limitations.
- TQQQ history begins in 2010. This study does not establish survival through the dot-com crash or 2008 using that instrument. Earlier synthetic backfills would be separate modeled experiments.
- Higher risk is not evidence of higher alpha. Compare leveraged timing against leveraged buy-and-hold as well as unleveraged benchmarks.
- Every monthly return includes unrealized P&L; losers cannot be hidden by leaving trades open. No scheduled withdrawal or monthly income guarantee is modeled.

See `summary.csv` for all scenarios, `base_monthly.csv` for the complete monthly record, `subperiods.csv` for three calendar blocks, and `manifest.json` for exact code/config/data hashes. No broker API or forward-paper session has been connected.
'''
    (out/'RESULTS.md').write_text(report)
    plot_v2(base,base_paths,c,out)
    manifest.update(status='complete',completed_simulations=len(rows),elapsed_seconds=time.monotonic()-timer)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'reports/LATEST_V2.txt').write_text(str(out.relative_to(ROOT))+'\n')
    print(table)
    print('Report:',out/'RESULTS.md')

def plot_v2(base,paths,c,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    candidates=base[base.strategy.isin([s['id'] for s in c['strategies']])].copy()
    fig,(ax,dd)=plt.subplots(1,2,figsize=(12,7),sharey=True,gridspec_kw={'width_ratios':[1.3,1]})
    names=candidates.strategy.to_list(); pos=np.arange(len(names))
    growth=candidates.geometric_month.to_numpy()*100
    drawdown=candidates.max_drawdown.abs().to_numpy()*100
    ax.barh(pos,growth,color='#1756a9'); dd.barh(pos,drawdown,color='#bd4b4b')
    ax.set_yticks(pos,labels=names);ax.invert_yaxis()
    for y,g,d in zip(pos,growth,drawdown):
        ax.text(g+.08,y,f'{g:.2f}%',va='center',fontsize=9)
        dd.text(d+.5,y,f'{d:.1f}%',va='center',fontsize=9)
    ax.axvline(10,color='#b5262b',linestyle='--',label='10% monthly target')
    ax.set(xlim=(min(-.5,float(growth.min())-.5),11),xlabel='Compounded monthly growth (%)')
    dd.set(xlim=(0,max(10,float(drawdown.max())*1.2)),xlabel='Maximum peak-to-trough loss (%)')
    fig.suptitle('Higher-risk paper adaptations · 2016–2024\nHistorical simulations with assumed costs; no live track record')
    for a in (ax,dd):a.grid(axis='x',alpha=.2);a.set_axisbelow(True)
    ax.legend(loc='lower right',fontsize=8);fig.tight_layout()
    fig.savefig(out/'risk_return.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
