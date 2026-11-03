"""Paper mechanisms expressed as causal observations, never same-bar fills."""
import numpy as np
import pandas as pd

def features(bars,daily,c):
    f=bars[['open','high','low','close','volume']].copy()
    day=pd.DatetimeIndex(f.index.date);f['day']=day
    f['minute']=f.index.hour*60+f.index.minute-(9*60+30)
    g=f.groupby('day');f['day_open']=g.open.transform('first')
    f['move']=(f.close/f.day_open-1).abs()
    f['sigma']=f.groupby('minute')['move'].transform(lambda x:x.shift(1).rolling(c['noise_lookback'],min_periods=c['noise_lookback']).mean())
    typical=(f.high+f.low+f.close)/3
    f['vwap_proxy']=(typical*f.volume).groupby(day).cumsum()/f.volume.groupby(day).cumsum()
    dividends=daily.dividend.fillna(0)
    previous=daily.close.shift(1)-dividends
    daily_return=(daily.close+dividends)/daily.close.shift(1)-1
    volatility=daily_return.shift(1).rolling(c['daily_vol_lookback']).std()
    f['previous_close']=day.map(previous)
    f['daily_vol']=day.map(volatility)
    f['upper']=np.maximum(f.day_open,f.previous_close)*(1+f.sigma)
    f['lower']=np.minimum(f.day_open,f.previous_close)*(1-f.sigma)
    first=f[f.minute==29].set_index('day').close
    first_return=first/previous-1
    v30=f[f.minute<30].groupby('day').volume.sum()
    median_volume=v30.shift(1).rolling(20,min_periods=20).median()
    f['first_return']=day.map(first_return)
    f['high_volume']=day.map(v30>median_volume)
    # First-half information is unavailable until 10:00, even though mapped by day.
    f.loc[f.minute<29,['first_return','high_volume']]=[np.nan,False]
    f['session_minutes']=g.close.transform('size')
    return f

def decisions(frame,spec):
    """NaN=keep position; -1/0/+1=target side, observed at this bar's end."""
    family=spec['family']; out=pd.Series(np.nan,index=frame.index,name='side')
    if family=='cash':return out
    for _,f in frame.groupby('day'):
        full=int(f.session_minutes.iloc[0])==390
        if not full:continue  # predeclared: no trading shortened sessions
        if family=='always_long':out.loc[f.index[0]]=1;continue
        if family in ('gao','last_half_long'):
            at=f.index[359]  # bar 15:29, complete 15:30
            if family=='last_half_long':side=1.
            else:
                side=float(np.sign(f.first_return.iloc[359]))
                if not np.isfinite(side):side=0.
                if spec['filter']=='agreement':
                    late=float(np.sign(f.close.iloc[359]/f.close.iloc[329]-1))
                    if late!=side:side=0.
                elif spec['filter']=='volume' and not bool(f.high_volume.iloc[359]):side=0.
            out.loc[at]=side;continue
        if family!='noise':raise ValueError(f'Unknown family {family}')
        side=0
        for n in range(29,389,30):
            r=f.iloc[n]
            if not np.isfinite(r.sigma) or not np.isfinite(r.daily_vol):continue
            if spec['stop']=='opposite':
                if r.close>r.upper:side=1
                elif r.close<r.lower:side=-1
            else:
                if r.close>max(r.upper,r.vwap_proxy):side=1
                elif r.close<min(r.lower,r.vwap_proxy):side=-1
                else:side=0
            out.loc[f.index[n]]=float(side)
    return out
