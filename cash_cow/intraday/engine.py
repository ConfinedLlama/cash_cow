"""Single-instrument, next-minute execution with cash settlement and explicit fills."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
from pandas.tseries.holiday import USFederalHolidayCalendar

@dataclass
class Result:
    path: pd.DataFrame
    trades: pd.DataFrame
    stats: dict

def settlement_dates(start,end,override=None):
    schedule=mcal.get_calendar('NYSE').schedule(start,pd.Timestamp(end)+pd.Timedelta(days=15))
    holidays=USFederalHolidayCalendar().holidays(start,pd.Timestamp(end)+pd.Timedelta(days=15))
    eligible=schedule.index.difference(holidays)
    out={}
    for d in schedule.index:
        lag=override if override is not None else (1 if d>=pd.Timestamp('2024-05-28') else 2 if d>=pd.Timestamp('2017-09-05') else 3)
        future=eligible[eligible>d]
        if len(future)>=lag:out[d]=future[lag-1]
    return out

def commission(quantity,s):
    return max(s['minimum_commission'],abs(quantity)*s['commission_per_share']) if quantity else 0.

def simulate(frame,decision,spec,settings,config,account):
    s=settings;capital=s['capital'];cash=float(capital);position=0.;pending=[]
    reference=account=='hypothetical_margin_long_short'
    if account not in ('cash_long_only','hypothetical_margin_long_short'):raise ValueError('Unknown account model')
    lot=1. if s['whole_shares'] else .000001
    settlements=settlement_dates(frame.day.iloc[0],frame.day.iloc[-1],s.get('settlement_override'))
    records=[];fills=[];fees=slippage=borrow=overhead=0.;blocked=liquidations=0;last_month=None;ruined=False
    for day,f in frame.groupby('day'):
        cash+=sum(v for d,v in pending if d<=day);pending=[(d,v) for d,v in pending if d>day]
        if position:raise AssertionError('Overnight position')
        opening_equity=cash+sum(v for _,v in pending)
        if day.to_period('M')!=last_month:
            expense=min(max(0.,cash),s['monthly_overhead']);cash-=expense;overhead+=expense
            if expense<s['monthly_overhead']:raise ValueError('Insufficient settled cash for overhead; model extension required')
            last_month=day.to_period('M')
        opening_equity=cash+sum(v for _,v in pending)
        vol=f.daily_vol.iloc[0]
        multiplier=min(config['max_reference_leverage'],config['target_daily_vol']/vol) if spec['sizing']=='vol_target' and np.isfinite(vol) and vol>0 else 1.
        if spec['sizing']=='vol_target' and (not np.isfinite(vol) or vol<=0):multiplier=0.
        if not reference:multiplier=min(1.,multiplier)
        unit_qty=np.floor(opening_equity*s['allocation']*multiplier/f.open.iloc[0]/lot)*lot
        opens=f.open.to_numpy();closes=f.close.to_numpy();volumes=f.volume.to_numpy();times=f.index
        actions={};obs=decision.reindex(times).to_numpy();force_next=False;day_locked=False
        for n,v in enumerate(obs):
            if np.isfinite(v):
                fill=n+1+int(s['latency_minutes'])
                if fill<len(f)-1:actions[fill]=(int(v),times[n]+pd.Timedelta(minutes=1))
        for n,t in enumerate(times):
            order_reason=None;signal_time=pd.NaT;target=None
            if force_next:
                target=0.;order_reason='maintenance_liquidation';signal_time=times[n-1]+pd.Timedelta(minutes=1)
                force_next=False;day_locked=True;liquidations+=1
            elif n==len(f)-1:
                target=0.;order_reason='scheduled_flatten';signal_time=times[0]
            elif n in actions and not day_locked and not ruined:
                side,signal_time=actions[n]
                if not reference and side<0:side=0
                if np.sign(position)!=side:
                    target=side*unit_qty;order_reason='signal'
            if target is not None:
                # A reversal is two orders. Sales in cash accounts cannot fund immediate repurchase.
                orders=[]
                if position and (target==0 or np.sign(target)!=np.sign(position)):orders.append(-position)
                if target and np.sign(target)!=np.sign(position):orders.append(target)
                for delta in orders:
                    closing=position!=0 and np.sign(delta)!=np.sign(position)
                    price=opens[n]*(1+np.sign(delta)*s['slippage_bps']/10000)+np.sign(delta)*s['slippage_dollars']
                    if not closing:
                        # Liquidity uses the PREVIOUS completed bar, never the future fill bar's volume.
                        capacity=np.floor(volumes[max(0,n-1)]*s['participation_cap']/lot)*lot
                        delta=np.sign(delta)*min(abs(delta),capacity)
                        if not reference:
                            affordable=np.floor(max(0,cash-s['minimum_commission'])/(price+s['commission_per_share'])/lot)*lot
                            delta=min(delta,affordable)
                        if abs(delta)<lot*.9 or abs(delta)*price<25:
                            blocked+=1;continue
                    cost=commission(delta,s)
                    if not reference and delta>0 and delta*price+cost>cash+1e-7:raise AssertionError('Unsettled cash used')
                    if not reference and delta<0:pending.append((settlements[day],-delta*price-cost))
                    else:cash-=delta*price+cost
                    position+=delta
                    if abs(position)<lot*.1:position=0.
                    fees+=cost;slippage+=abs(delta)*abs(price-opens[n])
                    fills.append((t,signal_time,delta,price,cost,order_reason,cash,position))
            # Intraday funding proxy; no overnight borrowing survives scheduled flatten.
            funding=(abs(min(position,0))*closes[n]+max(0,-cash))*s['borrow_annual_rate']/(365*24*60) if reference else 0.
            cash-=funding;borrow+=funding
            receivable=sum(v for _,v in pending)
            equity=cash+receivable+position*closes[n]
            if not reference and (cash< -1e-6 or position< -1e-6):raise AssertionError('Cash/long-only invariant')
            if reference and position and equity<.25*abs(position)*closes[n]:force_next=True
            if equity<=0:ruined=True;force_next=bool(position)
            records.append((t,equity,cash,receivable,position,fees,slippage,borrow,overhead))
        if position:raise AssertionError('Position not flattened')
    path=pd.DataFrame(records,columns=['timestamp','equity','cash','receivables','position','fees','slippage','borrow','overhead']).set_index('timestamp')
    trades=pd.DataFrame(fills,columns=['timestamp','signal_available','quantity','price','fee','reason','cash_after','position_after'])
    return Result(path,trades,{'blocked_entries':blocked,'maintenance_liquidations':liquidations,'ruined':ruined})

def monthly(path,capital):
    # Convert local dates without timezone warnings; retain all zero-trade days.
    eq=path.equity.copy();eq.index=eq.index.tz_localize(None)
    level=eq.resample('ME').last();prior=level.shift(1);prior.iloc[0]=capital
    return level/prior-1

def metrics(result,capital,target=.10):
    p=result.path;r=monthly(p,capital);eq=p.equity
    geometric=float(np.expm1(np.log1p(r).mean())) if (r>-1).all() else -1.
    return {'ending_equity':float(eq.iloc[-1]),'net_profit':float(eq.iloc[-1]-capital),'months':len(r),
            'geometric_month':geometric,'mean_month':float(r.mean()),'worst_month':float(r.min()),'best_month':float(r.max()),
            'target_hit_months':int((r>=target).sum()),'max_drawdown':float((eq/eq.cummax().clip(lower=capital)-1).min()),
            'negative_months':int((r<0).sum()),'orders':len(result.trades),'fees':float(p.fees.iloc[-1]),
            'slippage':float(p.slippage.iloc[-1]),'borrow':float(p.borrow.iloc[-1]),'overhead':float(p.overhead.iloc[-1]),**result.stats}
