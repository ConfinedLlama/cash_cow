"""Sample download, exchange-calendar validation and read-only Alpaca importer."""
import argparse
from datetime import datetime,timezone
import hashlib
import io
import json
import os
from pathlib import Path
import time
import zipfile
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import requests
from cash_cow.data import ROOT,sha256

NY='America/New_York'
RAW=ROOT/'data/raw/intraday'
URL='https://historicaldata.net/file/stocks_sample_2022H2.zip'

def validate_bars(bars,daily):
    if bars.empty or bars.index.tz is None or bars.index.has_duplicates or not bars.index.is_monotonic_increasing:
        raise ValueError('Empty, duplicate, unordered or timezone-naive bars')
    cols=['open','high','low','close','volume']
    if not np.isfinite(bars[cols].to_numpy()).all() or (bars[cols[:4]]<=0).any().any() or (bars.volume<=0).any():
        raise ValueError('Invalid price/volume')
    if (bars.high+1e-8<bars[['open','close','low']].max(axis=1)).any() or (bars.low-1e-8>bars[['open','close']].min(axis=1)).any():
        raise ValueError('Invalid OHLC bounds')
    if bars.index.max().year>=2025: raise ValueError('Reserved prices must remain unfetched')
    schedule=mcal.get_calendar('NYSE').schedule(bars.index[0].date(),bars.index[-1].date())
    regular=[]; audit=[]
    for day,s in schedule.iterrows():
        expected=pd.date_range(s.market_open,s.market_close,freq='min',inclusive='left').tz_convert(NY)
        actual=bars.loc[(bars.index>=expected[0])&(bars.index<=expected[-1])]
        missing=expected.difference(actual.index)
        if len(missing) or len(actual)!=len(expected):
            raise ValueError(f'{day.date()}: incomplete session ({len(missing)} missing minutes)')
        if 'session' in actual and not actual.session.eq('reg').all():raise ValueError('Vendor/session-calendar mismatch')
        regular.append(actual)
        audit.append({'date':str(day.date()),'minutes':len(actual),'early_close':len(actual)<390})
    reg=pd.concat(regular)
    if set(reg.index.date)!=set(daily.index.date):raise ValueError('Daily/minute date mismatch')
    # Vendor daily close includes auction conventions; preserve differences as diagnostics.
    last=reg.groupby(reg.index.date).close.last()
    close_error=np.abs(last.to_numpy()/daily.close.to_numpy()-1)
    audit_summary={'regular_bars':len(reg),'sessions':len(schedule),'missing_minutes':0,
                   'early_close_sessions':[a['date'] for a in audit if a['early_close']],
                   'max_daily_vs_last_minute_close_bps':float(close_error.max()*10000)}
    return reg,audit_summary

def load_sample(fetch=False):
    RAW.mkdir(parents=True,exist_ok=True); path=RAW/'stocks_sample_2022H2.zip'
    if fetch and not path.exists():
        r=requests.get(URL,timeout=60);r.raise_for_status();path.write_bytes(r.content)
    if not path.exists():raise FileNotFoundError('Run python -m cash_cow.intraday.data --sample')
    with zipfile.ZipFile(path) as z:
        vendor=json.loads(z.read('manifest.json'))
        selected=['minute_by_symbol/SPY_minute.csv','day_by_symbol/SPY_day.csv']
        for name in selected:
            entry=next(a for a in vendor['files'] if a['name']==name)
            if hashlib.sha256(z.read(name)).hexdigest()!=entry['sha256']:raise ValueError('Vendor manifest hash mismatch')
        bars=pd.read_csv(io.BytesIO(z.read(selected[0])),low_memory=False)
        bars.index=pd.DatetimeIndex(pd.to_datetime(bars.pop('timestamp'))).tz_localize(NY)
        daily=pd.read_csv(io.BytesIO(z.read(selected[1])),index_col='date',parse_dates=True)
        daily['dividend']=daily.dividend.fillna(0.)
        if daily['split'].notna().any():raise ValueError('SPY sample unexpectedly contains split')
        for name in ['README.md','LICENSE.txt','manifest.json']:
            (RAW/('vendor_'+name)).write_bytes(z.read(name))
    reg,audit=validate_bars(bars,daily)
    # Independently sourced existing Yahoo daily prices: sanity check, not a tick audit.
    other=pd.read_csv(ROOT/'data/raw/SPY.csv',index_col=0,parse_dates=True).reindex(daily.index)
    error=((other.Close/daily.close-1).abs()*10000)
    audit['yahoo_daily_close_max_difference_bps']=float(error.max())
    if other.Close.isna().any() or error.max()>10:raise ValueError('Cross-provider close discrepancy exceeds 10 bp')
    provenance={'provider':'HistoricalData.net','source':URL,'retrieved_or_verified_utc':datetime.now(timezone.utc).isoformat(),
                'archive_sha256':sha256(path),'file_hashes':{a['name']:a['sha256'] for a in vendor['files'] if a['name'] in selected},
                'validation':audit,'price_basis':'raw nominal OHLC, not future-adjusted adj_* columns',
                'vwap':'minute vwap unavailable; cumulative HLC3 times volume proxy, disclosed adaptation',
                'license':'Free sample evaluation allowed; raw data excluded from Git and redistribution'}
    return reg,daily,provenance

def read_keys():
    values={}
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line:continue
            key,value=line.split('=',1);values[key.strip()]=value.strip().strip('"').strip("'")
    key=os.getenv('APCA_API_KEY_ID') or values.get('APCA_API_KEY_ID')
    secret=os.getenv('APCA_API_SECRET_KEY') or values.get('APCA_API_SECRET_KEY')
    if not key or not secret:raise ValueError('Missing local APCA_API_KEY_ID / APCA_API_SECRET_KEY; never paste credentials into chat.')
    return {'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret}

def download_alpaca(start,end):
    if pd.Timestamp(end)>pd.Timestamp('2025-01-01'):raise ValueError('2025+ is reserved')
    if pd.Timestamp(start)>=pd.Timestamp(end):raise ValueError('Invalid date interval')
    headers=read_keys(); RAW.mkdir(parents=True,exist_ok=True)
    # Only market-data GET requests; no account, order or trading endpoint exists.
    for timeframe in ['1Min','1Day']:
        dest=RAW/f'alpaca_SPY_{timeframe}_{start}_{end}.csv.gz'
        if dest.exists():
            saved=dest.with_suffix('.manifest.json')
            if not saved.exists() or json.loads(saved.read_text()).get('sha256')!=sha256(dest):
                raise FileExistsError(f'Existing {dest.name} is unverified; refusing to overwrite')
            print(f'Using verified cache {dest.name}',flush=True)
            continue
        params={'symbols':'SPY','timeframe':timeframe,'start':start+'T00:00:00Z',
                'end':(pd.Timestamp(end,tz='UTC')-pd.Timedelta(seconds=1)).isoformat(),
                'feed':'sip','adjustment':'raw','limit':10000,'sort':'asc'}
        records=[];pages=0;tokens=set()
        while True:
            for attempt in range(5):
                try:
                    response=requests.get('https://data.alpaca.markets/v2/stocks/bars',headers=headers,params=params,timeout=45)
                except requests.RequestException:
                    if attempt==4:raise RuntimeError('Alpaca network request failed after five attempts') from None
                    time.sleep(2**attempt);continue
                if response.status_code not in (429,500,502,503,504):break
                if attempt==4:raise RuntimeError('Alpaca temporarily unavailable after five attempts')
                time.sleep(2**attempt)
            if response.status_code!=200:raise RuntimeError(f'Alpaca data request failed HTTP {response.status_code}; verify keys and SIP history entitlement locally.')
            payload=response.json();records.extend(payload.get('bars',{}).get('SPY',[]));pages+=1
            token=payload.get('next_page_token')
            if not token:break
            if token in tokens:raise RuntimeError('Repeated pagination token')
            tokens.add(token);params['page_token']=token
            if pages%20==0:print(f'{timeframe}: {len(records)} rows downloaded',flush=True)
            time.sleep(.32)
        if not records:raise ValueError('No bars returned')
        f=pd.DataFrame(records).rename(columns={'t':'timestamp','o':'open','h':'high','l':'low','c':'close','v':'volume','vw':'vwap','n':'transactions'})
        stamp=pd.to_datetime(f.timestamp,utc=True)
        if stamp.duplicated().any() or not stamp.is_monotonic_increasing:raise ValueError('Invalid API bar order')
        f.to_csv(dest,index=False,compression='gzip')
        manifest={'provider':'Alpaca SIP','timeframe':timeframe,'start':start,'end_exclusive':end,'rows':len(f),
                  'sha256':sha256(dest),'pages':pages,'adjustment':'raw','retrieved_utc':datetime.now(timezone.utc).isoformat()}
        dest.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(f'Saved {dest.name}: {len(f)} rows',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sample',action='store_true');p.add_argument('--alpaca',action='store_true')
    p.add_argument('--start',default='2016-01-01');p.add_argument('--end',default='2025-01-01');a=p.parse_args()
    if a.alpaca:download_alpaca(a.start,a.end)
    else:
        _,_,m=load_sample(fetch=a.sample)
        (ROOT/'data/manifest_v3.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
