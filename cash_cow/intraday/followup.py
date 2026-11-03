"""Separately registered rest-of-day signal; preserves original v3 code and results."""
from datetime import datetime,timezone
import json
import numpy as np
import pandas as pd
from cash_cow.data import ROOT,sha256
from .data import load_sample
from .signals import features
from .engine import simulate,metrics,monthly
from .run import reconcile,plot

def rest_of_day_decisions(frame):
    out=pd.Series(np.nan,index=frame.index,name='side')
    for _,f in frame.groupby('day'):
        if len(f)!=390:continue
        price=f.close.iloc[359];prior=f.previous_close.iloc[359]
        out.loc[f.index[359]]=float(np.sign(price/prior-1)) if np.isfinite(prior) else 0.
    return out

def main():
    c=json.loads((ROOT/'configs/experiment_v3b.json').read_text())
    bars,daily,provenance=load_sample();f=features(bars,daily,c);signal=rest_of_day_decisions(f)
    f=f[(f.day>=pd.Timestamp(c['evaluation_start']))&(f.day<=pd.Timestamp(c['evaluation_end']))]
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_v3b_rest_of_day'
    out=ROOT/'reports/runs'/run_id;out.mkdir(parents=True)
    for name in ['paths','trades','monthly']:(out/name).mkdir()
    manifest={'run_id':run_id,'status':'running','config':c,'data':provenance,
              'config_sha256':sha256(ROOT/'configs/experiment_v3b.json'),
              'sources':{str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'cash_cow').rglob('*.py'))}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows=[];months={};errors=[]
    for account in c['account_models']:
        scenarios=list(c['scenarios'])+([dict(id='paper_cost_diagnostic',**c['paper_cost_diagnostic'])] if account.startswith('hypothetical') else [dict(id='modern_T1_counterfactual',**c['modern_cash_diagnostic'])])
        for scenario in scenarios:
            s=dict(c['base'],capital=c['capital']);s.update({k:v for k,v in scenario.items() if k!='id'})
            for spec in c['rules']:
                r=simulate(f,signal,spec,s,c,account);errors.append(reconcile(r,f,s,account))
                tag=account+'__'+scenario['id']+'__'+spec['id']
                rows.append({'account':account,'scenario':scenario['id'],'strategy':spec['id'],'capital':s['capital'],**metrics(r,s['capital'],c['target_monthly'])})
                r.path.to_csv(out/'paths'/f'{tag}.csv.gz',compression='gzip');r.trades.to_csv(out/'trades'/f'{tag}.csv',index=False)
                months[tag]=monthly(r.path,s['capital']);months[tag].rename('return').to_csv(out/'monthly'/f'{tag}.csv')
        print('Completed follow-up',account,flush=True)
    summary=pd.DataFrame(rows);summary.to_csv(out/'summary.csv',index=False);pd.DataFrame(months).to_csv(out/'monthly_returns.csv')
    base=summary[summary.scenario=='01_base'];plot(base,c,out)
    table=['| Account / strategy | Compounded month | Worst month | Drawdown |','|---|---:|---:|---:|']
    for _,r in base.iterrows():table.append(f'| {r.account} / {r.strategy} | {r.geometric_month:.2%} | {r.worst_month:.2%} | {r.max_drawdown:.2%} |')
    report='# Rest-of-day follow-up\n\n44 additional simulations. Same August–December 2022 sample; hypothesis added after v3 results, so this is adaptive reuse, not a fresh validation.\n\n'+'\n'.join(table)+'\n\nSignal: direction of previous daily close (ex-dividend adjusted) to the completed 15:29 bar. Trade final half-hour with the same delayed next-minute fills. Fixed sizing and a separately labelled 2%-daily-volatility hybrid. The source paper studies futures across asset classes; this SPY adaptation does not reproduce that universe or its published returns.\n\nSource: https://academicweb.nd.edu/~zda/intramom.pdf\n\nAll v3 account, cost, data, short-availability, eligibility and short-sample limitations apply. No live approval.\n'
    (out/'RESULTS.md').write_text(report)
    audit={'status':'passed','runs':len(rows),'orders':int(summary.orders.sum()),'maximum_nav_reconciliation_error':max(errors)}
    (out/'VERIFICATION.json').write_text(json.dumps(audit,indent=2)+'\n')
    manifest.update(status='complete',completed_simulations=len(rows));(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'reports/LATEST_V3B.txt').write_text(str(out.relative_to(ROOT))+'\n');print(report);print('Report:',out/'RESULTS.md')

if __name__=='__main__':main()
