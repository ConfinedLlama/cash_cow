"""V2 data preparation. Preserve v1 cache; no 2025+ price bars are fetched."""
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd
from .data import ROOT, sha256

def restore_nominal(frame, post_window_factor=1.0, cash_proxies=None):
    f = frame.copy()
    capital_gains = f.get('Capital Gains', pd.Series(0., index=f.index))
    # Tax all cash distributions conservatively using the engine's configured rate.
    distribution = f['Dividends'] + capital_gains
    f['SplitClose'] = f['Close']
    ret = (f['Close'] + distribution) / f['Close'].shift(1) - 1
    f['Signal'] = (1 + ret.fillna(0)).cumprod() * 100
    f['Dividends'] = distribution
    split = f['Stock Splits'].replace(0, 1)
    factor = split.iloc[::-1].cumprod().iloc[::-1] / split * post_window_factor
    cols = ['Open', 'High', 'Low', 'Close', 'Dividends']
    f[cols] = f[cols].mul(factor, axis=0)
    # Vendor encodes some spin-offs as splits. Restore the original price units
    # first, then replace phantom parent shares with a documented cash proxy.
    for date, amount in (cash_proxies or {}).items():
        date = pd.Timestamp(date)
        if date not in f.index or f.loc[date, 'Stock Splits'] == 0:
            raise ValueError('Expected vendor spin-off adjustment missing')
        f.loc[date, 'Stock Splits'] = 0.
        f.loc[date, 'Dividends'] += amount
    if cash_proxies:
        ratio = f['Stock Splits'].replace(0, 1)
        total_return = (f['Close'] + f['Dividends']) * ratio / f['Close'].shift(1)
        f['Signal'] = total_return.fillna(1).cumprod() * 100
    return f

def fetch_v2(c):
    import yfinance as yf
    raw = ROOT / 'data/raw'
    raw.mkdir(exist_ok=True, parents=True)
    for symbol in c['symbols']:
        path = raw / f'{symbol}.csv'
        if path.exists():
            continue
        frame = yf.Ticker(symbol).history(start=c['download_start'], end=c['download_end_exclusive'],
                    auto_adjust=False, actions=True, raise_errors=True, timeout=25)
        if frame.empty:
            raise ValueError(f'Empty data: {symbol}')
        frame.index = frame.index.tz_localize(None)
        frame.index.name = 'Date'
        frame.to_csv(path)
        print(f'Cached {symbol}: {len(frame)} sessions, ending {frame.index[-1].date()}', flush=True)

def load_v2(c):
    frames, files = {}, {}
    for symbol in c['symbols']:
        path = ROOT / f'data/raw/{symbol}.csv'
        f = pd.read_csv(path, index_col=0, parse_dates=True)
        cols = ['Open', 'High', 'Low', 'Close', 'Dividends', 'Stock Splits']
        if f.empty or f.index.has_duplicates or not f.index.is_monotonic_increasing:
            raise ValueError(f'{symbol}: empty or invalid index')
        if f[cols].isna().any().any() or not np.isfinite(f[cols].to_numpy()).all():
            raise ValueError(f'{symbol}: invalid numerical data')
        if (f[['Open','High','Low','Close']] <= 0).any().any():
            raise ValueError(f'{symbol}: nonpositive price')
        if (f.High + 1e-6 < f[['Open','Close','Low']].max(axis=1)).any() or (f.Low - 1e-6 > f[['Open','Close']].min(axis=1)).any():
            raise ValueError(f'{symbol}: invalid OHLC')
        if f.index.max() >= pd.Timestamp(c['download_end_exclusive']):
            raise ValueError(f'{symbol}: reserved history included')
        if 'Capital Gains' in f and (f['Capital Gains'].isna().any() or (f['Capital Gains'] < 0).any()):
            raise ValueError(f'{symbol}: invalid cash distribution')
        post = c['post_window_split_factors'].get(symbol, 1.0)
        proxies = c.get('spin_off_cash_proxies', {}).get(symbol, {})
        frames[symbol] = restore_nominal(f, post, proxies)
        files[symbol] = {'sha256':sha256(path), 'rows':len(f), 'start':str(f.index.min().date()), 'end':str(f.index.max().date()),
                         'post_window_split_factor':post, 'splits':{str(k.date()):float(v) for k,v in f.loc[f['Stock Splits']!=0,'Stock Splits'].items()},
                         'capital_gains_events':int((f.get('Capital Gains',pd.Series(0,index=f.index))!=0).sum()),
                         'spin_off_cash_proxies':proxies}
    required = frames['SPY'].loc[c['development_start']:c['validation_end']].index
    for symbol,f in frames.items():
        if len(required.difference(f.index)):
            raise ValueError(f'{symbol}: missing trading dates in required window')
    manifest = {'research_date':c['research_date'], 'prepared_utc':datetime.now(timezone.utc).isoformat(),
                'provider':'Yahoo Finance via yfinance; unofficial personal research data',
                'config_sha256':sha256(ROOT/'configs/experiment_v2.json'), 'files':files,
                'post_window_sources':c['post_window_split_sources'],
                'limitations':'Known issuer-reported post-window splits restored; not an exhaustive independent corporate-action audit. No post-2024 price bars used.'}
    return frames, manifest

if __name__ == '__main__':
    c=json.loads((ROOT/'configs/experiment_v2.json').read_text())
    fetch_v2(c)
    frames, m=load_v2(c)
    (ROOT/'data/manifest_v2.json').write_text(json.dumps(m,indent=2)+'\n')
    print('Validated',len(frames),'instruments')
