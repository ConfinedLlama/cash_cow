"""Download research bars with provenance; reject incomplete/unhandled data."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fetch(config: dict) -> dict:
    import yfinance as yf
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    manifest = {'provider': 'Yahoo Finance via yfinance; unofficial personal research access',
                'research_date': config['research_date'], 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                'start': config['download_start'], 'end_exclusive': config['download_end_exclusive'],
                'config_sha256': sha256(ROOT / 'configs/experiment_v1.json'), 'files': {}}
    for symbol in config['symbols']:
        path = raw / f'{symbol}.csv'
        if not path.exists():
            frame = yf.Ticker(symbol).history(start=config['download_start'], end=config['download_end_exclusive'],
                                             auto_adjust=False, actions=True, raise_errors=True, timeout=25)
            if frame.empty:
                raise ValueError(f'No data returned for {symbol}')
            frame.index = frame.index.tz_localize(None)
            frame.index.name = 'Date'
            frame.to_csv(path)
            print(f'Downloaded {symbol}: {len(frame)} sessions', flush=True)
        frame = pd.read_csv(path, index_col=0, parse_dates=True)
        manifest['files'][symbol] = {'sha256': sha256(path), 'rows': len(frame),
                                      'first': str(frame.index.min().date()), 'last': str(frame.index.max().date()),
                                      'file_modified_utc': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
    (ROOT / 'data/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest

def load(config: dict) -> dict[str, pd.DataFrame]:
    frames = {}
    for symbol in config['symbols']:
        path = ROOT / f'data/raw/{symbol}.csv'
        f = pd.read_csv(path, index_col=0, parse_dates=True)
        if f.index.has_duplicates or not f.index.is_monotonic_increasing:
            raise ValueError(f'{symbol}: invalid date index')
        cols = ['Open', 'High', 'Low', 'Close', 'Dividends', 'Stock Splits']
        if f[cols].isna().any().any() or not np.isfinite(f[cols].to_numpy()).all():
            raise ValueError(f'{symbol}: missing/nonfinite data; no forward filling allowed')
        if (f[['Open', 'High', 'Low', 'Close']] <= 0).any().any():
            raise ValueError(f'{symbol}: nonpositive price')
        if (f['High'] + 1e-6 < f[['Open', 'Close', 'Low']].max(axis=1)).any() or (f['Low'] - 1e-6 > f[['Open', 'Close']].min(axis=1)).any():
            raise ValueError(f'{symbol}: inconsistent OHLC')
        if 'Capital Gains' in f and (f['Capital Gains'] != 0).any():
            raise ValueError(f'{symbol}: capital-gain distributions need explicit accounting')
        if f.index.max() >= pd.Timestamp(config['download_end_exclusive']):
            raise ValueError('Reserved history was included')
        # Causal total-return index: no vendor Adj Close or future adjustment factors.
        ret = (f['Close'] + f['Dividends']) / f['Close'].shift(1) - 1
        f['Signal'] = (1 + ret.fillna(0)).cumprod() * 100
        # Yahoo OHLC and distributions are split-adjusted. Restore nominal units
        # for position sizing; the signal remains on a split-consistent basis.
        split = f['Stock Splits'].replace(0, 1)
        future_split = split.iloc[::-1].cumprod().iloc[::-1] / split
        f[['Open', 'High', 'Low', 'Close', 'Dividends']] = f[['Open', 'High', 'Low', 'Close', 'Dividends']].mul(future_split, axis=0)
        frames[symbol] = f
    master = frames['SPY'].index
    required = master[master >= config['development_start']]
    for symbol, f in frames.items():
        if len(required.difference(f.index)):
            raise ValueError(f'{symbol}: missing required trading sessions')
    return frames
