"""Read-only data preparation and registered long-history intraday evaluation."""
import argparse
from datetime import datetime,timezone
import json
import numpy as np
import pandas as pd
from cash_cow.data import ROOT,sha256
from .data import RAW,NY,download_alpaca,validate_bars
from .signals import features,decisions
from .followup import rest_of_day_decisions
from .engine import simulate,metrics,monthly
from .run import reconcile,plot

def load_alpaca():
    frames={};files={}
    for timeframe in ['1Min','1Day']:
        p=RAW/f'alpaca_SPY_{timeframe}_2016-01-01_2025-01-01.csv.gz'
        if not p.exists():raise FileNotFoundError('Multi-year SIP history missing; run with --fetch after saving local keys')
        m=json.loads(p.with_suffix('.manifest.json').read_text())
        if sha256(p)!=m['sha256']:raise ValueError('Alpaca cached file hash mismatch')
        f=pd.read_csv(p)
        f.index=pd.DatetimeIndex(pd.to_datetime(f.pop('timestamp'),utc=True)).tz_convert(NY)
        frames[timeframe]=f;files[str(p.relative_to(ROOT))]=m
    daily=frames['1Day'];daily.index=daily.index.tz_localize(None).normalize()
    other=pd.read_csv(ROOT/'data/raw/SPY.csv',index_col=0,parse_dates=True).reindex(daily.index)
    if other.Dividends.isna().any():raise ValueError('Missing independent dividend observations')
    discrepancy=(other.Close/daily.close-1).abs()*10000
    if discrepancy.max()>10:raise ValueError('API/Yahoo daily prices differ by more than 10 bp; investigate before running')
    daily['dividend']=other.Dividends
    if (other['Stock Splits']!=0).any():raise ValueError('Unexpected SPY split requires explicit treatment')
    bars,audit=validate_bars(frames['1Min'],daily)
    if bars.index[0].date()!=pd.Timestamp('2016-01-04').date() or bars.index[-1].date()!=pd.Timestamp('2024-12-31').date():
        raise ValueError('Incomplete requested multi-year boundary coverage')
    audit['daily_cross_provider_max_difference_bps']=float(discrepancy.max())
    manifest={'provider':'Alpaca SIP','files':files,'validation':audit,
              'dividend_source':'Existing Yahoo SPY action cache','dividend_file_sha256':sha256(ROOT/'data/raw/SPY.csv'),
              'vwap':'HLC3 volume proxy retained for comparability; not trade-exact VWAP'}
    return bars,daily,manifest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fetch',action='store_true');parser.add_argument('--full',action='store_true')
    parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
    if args.fetch:download_alpaca('2016-01-01','2025-01-01')
    bars,daily,provenance=load_alpaca()
    (ROOT/'data/manifest_v4.json').write_text(json.dumps(provenance,indent=2)+'\n')
    if args.validate_only:print(json.dumps(provenance['validation'],indent=2));return
    c=json.loads((ROOT/'configs/experiment_v4.json').read_text());f=features(bars,daily,c)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_v4_intraday_'+('full' if args.full else 'base')
    out=ROOT/'reports/runs'/run_id;out.mkdir(parents=True)
    for d in ['paths','trades','monthly']:(out/d).mkdir()
    manifest={'run_id':run_id,'status':'running','config':c,'config_sha256':sha256(ROOT/'configs/experiment_v4.json'),
              'data':provenance,'full_sensitivity_matrix':args.full,
              'sources':{str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'cash_cow').rglob('*.py'))}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    specs=c['rules']+c['benchmarks'];signals={s['id']:(rest_of_day_decisions(f) if s['family']=='rest_of_day' else decisions(f,s)) for s in specs}
    rows=[];errors=[];months={}
    scenarios=c['scenarios'] if args.full else c['scenarios'][:1]
    for window,(start,end) in c['windows'].items():
        selected=f[(f.day>=pd.Timestamp(start))&(f.day<=pd.Timestamp(end))]
        for account in c['account_models']:
            for scenario in scenarios:
                s=dict(c['base'],capital=c['capital']);s.update({k:v for k,v in scenario.items() if k!='id'})
                for spec in specs:
                    tag=window+'__'+account+'__'+scenario['id']+'__'+spec['id']
                    r=simulate(selected,signals[spec['id']],spec,s,c,account)
                    errors.append(reconcile(r,selected,s,account))
                    rows.append({'window':window,'account':account,'scenario':scenario['id'],'strategy':spec['id'],**metrics(r,s['capital'],c['target_monthly'])})
                    r.path.to_csv(out/'paths'/f'{tag}.csv.gz',compression='gzip');r.trades.to_csv(out/'trades'/f'{tag}.csv',index=False)
                    months[tag]=monthly(r.path,s['capital']);months[tag].rename('return').to_csv(out/'monthly'/f'{tag}.csv')
                    print('Completed',tag,flush=True)
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False);pd.DataFrame(months).to_csv(out/'monthly_returns.csv')
    manifest.update(status='complete',completed_simulations=len(rows));(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'VERIFICATION.json').write_text(json.dumps({'status':'passed','runs':len(rows),'maximum_nav_error':max(errors)},indent=2)+'\n')
    (ROOT/'reports/LATEST_V4.txt').write_text(str(out.relative_to(ROOT))+'\n')
    print('Completed registered historical evaluation:',out)

if __name__=='__main__':main()
