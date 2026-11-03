"""Parameter-driven ETF adaptations of named papers, not exact paper replications."""
import numpy as np
import pandas as pd

def select_top(scores, columns, cap, n=3, smallest=False):
    out = pd.DataFrame(0., index=scores.index, columns=columns)
    for date,row in scores.iterrows():
        row=row.dropna()
        if len(row)<n:
            continue
        chosen=row.nsmallest(n).index if smallest else row.nlargest(n).index
        out.loc[date,chosen]=cap/n
    return out

def make_signals_v2(frames, spec, sectors, cap=0.95):
    px=pd.DataFrame({s:f['Signal'] for s,f in frames.items()})
    out=pd.DataFrame(0.,index=px.index,columns=px.columns)
    name=spec['id']
    if 'family' not in spec:
        if 'instrument' in spec:
            out[spec['instrument']]=0.95  # fixed benchmark definition, independent of candidate cap
        return out
    family=spec['family']
    if family in ('industry_momentum','relative_momentum','intermediate_momentum','industry_momentum_volatility_management') and name!='relative_mom_3x':
        scores=px[sectors].shift(spec['skip'])/px[sectors].shift(spec['lookback'])-1
        out=select_top(scores,px.columns,cap,spec['top_n'])
        if family=='industry_momentum_volatility_management':
            ret=px[sectors].pct_change(fill_method=None)
            for i in range(spec['vol_window'],len(out)):
                w=out.iloc[i][sectors].to_numpy()/cap
                if w.sum()==0:
                    continue
                covariance=ret.iloc[i-spec['vol_window']+1:i+1].cov().to_numpy()*252
                vol=np.sqrt(max(0.,w@covariance@w))
                scale=min(1.,spec['annual_vol_target']/vol) if vol>0 else 0.
                out.iloc[i]*=scale
            out.iloc[:spec['vol_window']]=0.
    elif family=='52_week_high':
        # Price-nearness signal, not total-return nearness. All observations use consistent split units.
        close=pd.DataFrame({s:frames[s]['SplitClose'] for s in sectors})
        scores=close/close.rolling(spec['lookback'],min_periods=spec['lookback']).max()
        out=select_top(scores,px.columns,cap,spec['top_n'])
    elif family in ('short_reversal','long_reversal'):
        scores=px[sectors].pct_change(spec['lookback'],fill_method=None)
        out=select_top(scores,px.columns,cap,spec['top_n'],smallest=True)
    elif family=='time_series_momentum':
        u=spec['underlying']; k=spec['lookback']
        excess=px[u].pct_change(k,fill_method=None)-px.BIL.pct_change(k,fill_method=None)
        out[spec['instrument']]=(excess>0).astype(float)*cap
    elif family=='tactical_trend':
        u=spec['underlying']
        out[spec['instrument']]=(px[u]>px[u].rolling(spec['lookback']).mean()).astype(float)*cap
    elif family=='volatility_management':
        # Prior completed observations; monthly rebalance is implemented by the engine.
        variance=px[spec['underlying']].pct_change(fill_method=None).rolling(spec['vol_window']).var()*252
        underlying_exposure=spec['reference_annual_vol']**2/variance.replace(0,np.nan)
        out[spec['instrument']]=(underlying_exposure/spec['daily_leverage']).clip(0,cap).fillna(0)
    elif name=='relative_mom_3x':
        scores=px[['SPY','QQQ']].shift(spec['skip'])/px[['SPY','QQQ']].shift(spec['lookback'])-1
        for date,row in scores.dropna().iterrows():
            best=row.idxmax()
            out.loc[date,{'SPY':'UPRO','QQQ':'TQQQ'}[best]]=cap
    else:
        raise ValueError(f'Unknown strategy {name}')
    if not np.isfinite(out.to_numpy()).all() or (out<0).any().any() or (out.sum(axis=1)>cap+1e-9).any():
        raise ValueError('Invalid candidate allocation')
    return out
