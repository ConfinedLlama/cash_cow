"""Fixed, causal rules. These are research candidates, not proven profitable strategies."""
import numpy as np
import pandas as pd

CADENCE = {'sma200': 'monthly', 'ma_cross': 'weekly', 'absolute_momentum': 'monthly',
           'donchian': 'change', 'rsi2': 'change', 'bollinger': 'change',
           'relative_momentum': 'monthly', 'dual_momentum': 'monthly',
           'inverse_vol_trend': 'monthly', 'vol_target': 'monthly',
           'cash': 'once', 'spy_25': 'monthly', 'bills_100': 'once'}

def make_signals(frames, name, cap=0.25):
    px = pd.DataFrame({s: f['Signal'] for s, f in frames.items()})
    out = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    p = px['SPY']
    trend = p > p.rolling(200, min_periods=200).mean()
    if name == 'cash':
        return out
    if name == 'spy_25':
        out['SPY'] = 0.25
    elif name == 'bills_100':
        out['BIL'] = 0.99  # explicit fee/cash buffer; do not assume deposit insurance
    elif name == 'sma200':
        out['SPY'] = trend.astype(float) * cap
    elif name == 'ma_cross':
        out['SPY'] = (p.rolling(50).mean() > p.rolling(200).mean()).astype(float) * cap
    elif name == 'absolute_momentum':
        out['SPY'] = (p.pct_change(252, fill_method=None) > 0).astype(float) * cap
    elif name in ('donchian', 'rsi2', 'bollinger'):
        upper = p.rolling(55).max().shift(1)
        lower = p.rolling(20).min().shift(1)
        mean = p.rolling(20).mean()
        sd = p.rolling(20).std()
        change = p.diff()
        up = change.clip(lower=0).ewm(alpha=0.5, adjust=False, min_periods=2).mean()
        down = (-change.clip(upper=0)).ewm(alpha=0.5, adjust=False, min_periods=2).mean()
        rsi = 100 - 100 / (1 + up / down.replace(0, np.nan))
        rsi = rsi.mask((down == 0) & (up > 0), 100).mask((down == 0) & (up == 0), 50)
        active, age = False, 0
        for i in range(len(px)):
            if active:
                age += 1
                exit_now = ((p.iloc[i] < lower.iloc[i]) if name == 'donchian' else
                            ((rsi.iloc[i] > 70 or age >= 5 or not trend.iloc[i]) if name == 'rsi2' else
                             (p.iloc[i] >= mean.iloc[i] or age >= 10 or not trend.iloc[i])))
                if exit_now:
                    active = False
            else:
                enter = ((p.iloc[i] > upper.iloc[i]) if name == 'donchian' else
                         ((rsi.iloc[i] < 10 and trend.iloc[i]) if name == 'rsi2' else
                          (p.iloc[i] < mean.iloc[i] - 2 * sd.iloc[i] and trend.iloc[i])))
                if enter:
                    active, age = True, 0
            out.iloc[i, out.columns.get_loc('SPY')] = float(active) * cap
    elif name == 'relative_momentum':
        universe = ['SPY', 'QQQ', 'IWM', 'EFA', 'IEF', 'TLT', 'GLD']
        momentum = px[universe].pct_change(126, fill_method=None)
        for date, row in momentum.iterrows():
            top = row.dropna().nlargest(2)
            top = top[top > 0]
            # Fixed 1/2 sleeves: an unqualified second slot stays in cash.
            out.loc[date, top.index] = cap / 2
    elif name == 'dual_momentum':
        momentum = px[['SPY', 'EFA', 'SHY']].pct_change(252, fill_method=None)
        for date, row in momentum.dropna().iterrows():
            best = row[['SPY', 'EFA']].idxmax()
            if row[best] > max(0, row['SHY']):
                out.loc[date, best] = cap
    elif name == 'inverse_vol_trend':
        universe = ['SPY', 'IEF', 'GLD']
        vol = px[universe].pct_change(fill_method=None).rolling(63).std() * np.sqrt(252)
        inv = 1 / vol.replace(0, np.nan)
        weights = inv.div(inv.sum(axis=1), axis=0)
        allowed = px[universe] > px[universe].rolling(200).mean()
        out[universe] = (weights * allowed * cap).fillna(0)
    elif name == 'vol_target':
        vol = p.pct_change(fill_method=None).rolling(63).std() * np.sqrt(252)
        out['SPY'] = (0.05 / vol.replace(0, np.nan)).clip(0, cap).fillna(0)
    else:
        raise ValueError(f'Unknown strategy: {name}')
    if not np.isfinite(out.to_numpy()).all() or (out < 0).any().any() or (out.sum(axis=1) > 1 + 1e-9).any():
        raise ValueError('Invalid strategy allocation')
    return out
