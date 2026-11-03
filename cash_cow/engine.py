"""Daily-bar cash-account screen with explicit receivables and next-open execution.

Fills, settlement and dividend payable dates are approximations; see methodology.
No network access and no broker order API exist in this module.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .strategies import CADENCE

@dataclass
class Simulation:
    path: pd.DataFrame
    trades: pd.DataFrame

def simulate(frames, signals, name, settings, start, end):
    dates = frames['SPY'].index
    symbols = list(signals.columns)
    opens = pd.DataFrame({s: frames[s]['Open'] for s in symbols}).reindex(dates).to_numpy()
    closes = pd.DataFrame({s: frames[s]['Close'] for s in symbols}).reindex(dates).to_numpy()
    dividends = pd.DataFrame({s: frames[s]['Dividends'] for s in symbols}).reindex(dates).fillna(0).to_numpy()
    splits = pd.DataFrame({s: frames[s]['Stock Splits'] for s in symbols}).reindex(dates).fillna(0).replace(0, 1).to_numpy()
    weights = signals.reindex(dates).to_numpy()
    indices = np.flatnonzero((dates >= start) & (dates <= end))
    if len(indices) == 0:
        raise ValueError('Empty simulation window')
    capital = settings['capital']
    cash, previous_equity = float(capital), float(capital)
    holdings = np.zeros(len(symbols))
    desired = np.zeros(len(symbols))
    previous_weights = None
    receivables = []  # (release_index, cash_amount): valued now, not spendable yet
    records, trades = [], []
    slip = settings['one_way_slippage_bps'] / 10000
    fee = settings['commission_per_order']
    lot = 1 if settings['whole_shares'] else 0.000001
    equity_funds = set(settings.get('taxable_symbols', ['SPY', 'QQQ', 'IWM', 'EFA']))
    tax = np.array([0.30 if settings['all_dividends_withholding'] or s in equity_funds else 0.0 for s in symbols])
    total_fees = total_slippage = total_overhead = withheld = 0.0
    overhead_payable = 0.0
    cadence = settings.get('cadence', CADENCE.get(name))
    if cadence not in ('monthly', 'weekly', 'change', 'once'):
        raise ValueError(f'Unsupported decision cadence for {name}')
    for k, i in enumerate(indices):
        d = dates[i]
        cash += sum(amount for release, amount in receivables if release <= i)
        receivables = [(release, amount) for release, amount in receivables if release > i]
        holdings *= splits[i]
        desired *= splits[i]
        # Entitlement belongs to holders before the ex-date open.
        gross_div = holdings * dividends[i]
        net_div = float((gross_div * (1 - tax)).sum())
        withheld += float((gross_div * tax).sum())
        if net_div:
            receivables.append((i + settings['dividend_cash_delay_sessions'], net_div))
        new_month = k == 0 or d.to_period('M') != dates[indices[k-1]].to_period('M')
        if new_month:
            overhead = settings['monthly_overhead']
            overhead_payable += overhead
            total_overhead += overhead
        payment = min(cash, overhead_payable)
        cash -= payment
        overhead_payable -= payment
        j = i - 1 - settings['extra_signal_delay_sessions']
        if j < 0:
            raise ValueError('Insufficient lagged observations')
        w = weights[j]
        changed = previous_weights is None or not np.allclose(w, previous_weights, atol=1e-12)
        new_week = k == 0 or d.to_period('W-FRI') != dates[indices[k-1]].to_period('W-FRI')
        rebalance = k == 0 or (cadence == 'monthly' and new_month) or (cadence == 'weekly' and new_week) or (cadence == 'change' and changed)
        if rebalance:
            # Lagged NAV prevents sizing with that day's closing price.
            budget_equity = max(0, previous_equity - (settings['monthly_overhead'] if new_month else 0))
            desired = np.floor((budget_equity * w / (opens[i] * (1 + slip))) / lot) * lot
            # Fixed $25 rebalance threshold; always permit complete exits.
            small = (np.abs(desired - holdings) * opens[i] < 25) & (desired > 0)
            desired[small] = holdings[small]
        previous_weights = w.copy()
        if overhead_payable > 1e-8:
            # Recognize an operating-expense liability immediately. Reduce positions
            # to fund it, wait for settlement, and block buys while unpaid.
            desired = np.minimum(desired, holdings)
            needed = max(0, overhead_payable - sum(amount for _, amount in receivables))
            for a in np.argsort(-(holdings * opens[i])):
                if needed <= 0:
                    break
                qty = min(holdings[a], np.ceil((needed + fee) / (opens[i, a] * (1 - slip)) / lot) * lot)
                desired[a] = min(desired[a], holdings[a] - qty)
                needed -= qty * opens[i, a] * (1 - slip) - fee
        for a in range(len(symbols)):
            quantity = max(0, holdings[a] - desired[a])
            if quantity < lot * 0.9:
                continue
            execution = opens[i, a] * (1 - slip)
            proceeds = quantity * execution - fee
            if proceeds <= 0:
                continue
            holdings[a] -= quantity
            receivables.append((i + settings['settlement_sessions'], proceeds))
            total_fees += fee
            total_slippage += quantity * opens[i, a] * slip
            trades.append((d, dates[j], symbols[a], 'SELL', quantity, execution, fee, cash))
        for a in range(len(symbols)):
            if overhead_payable > 1e-8:
                break
            wanted = max(0, desired[a] - holdings[a])
            execution = opens[i, a] * (1 + slip)
            quantity = min(wanted, np.floor(max(0, cash - fee) / execution / lot) * lot)
            if quantity < lot * 0.9 or quantity * execution < 25:
                continue
            cash -= quantity * execution + fee
            holdings[a] += quantity
            total_fees += fee
            total_slippage += quantity * opens[i, a] * slip
            trades.append((d, dates[j], symbols[a], 'BUY', quantity, execution, fee, cash))
        invested = float(holdings @ closes[i])
        unsettled = sum(amount for _, amount in receivables)
        equity = cash + unsettled + invested - overhead_payable
        if cash < -1e-7 or (holdings < -1e-7).any() or not np.isfinite(equity) or equity <= 0:
            raise AssertionError('Cash/no-short/accounting invariant violated')
        records.append((d, equity, cash, unsettled, invested / equity, total_fees, total_slippage, total_overhead, withheld, overhead_payable))
        previous_equity = equity
    path = pd.DataFrame(records, columns=['date', 'equity', 'settled_cash', 'receivables', 'exposure', 'fees', 'slippage_cost', 'overhead', 'withheld_dividends', 'overhead_payable']).set_index('date')
    trades = pd.DataFrame(trades, columns=['date', 'signal_date', 'symbol', 'side', 'quantity', 'price', 'fee', 'settled_cash_after'])
    return Simulation(path, trades)

def monthly_returns(path, capital):
    levels = path['equity'].resample('ME').last()
    prior = levels.shift(1)
    prior.iloc[0] = capital
    return levels / prior - 1

def metrics(sim, capital):
    eq = sim.path['equity']
    month = monthly_returns(sim.path, capital)
    peak = eq.cummax().clip(lower=capital)
    day = eq.pct_change().fillna(eq.iloc[0] / capital - 1)
    duration = (eq.index[-1] - eq.index[0]).days + 1
    dd = eq / peak - 1
    return {'start': str(eq.index[0].date()), 'end': str(eq.index[-1].date()), 'months': len(month),
            'capital': capital, 'ending_equity': eq.iloc[-1], 'net_profit': eq.iloc[-1] - capital,
            'cagr': (eq.iloc[-1] / capital)**(365.25 / duration) - 1,
            'mean_month': month.mean(), 'median_month': month.median(),
            'positive_month_fraction': (month > 0).mean(), 'negative_months': int((month < 0).sum()),
            'worst_month': month.min(), 'best_month': month.max(), 'max_drawdown': dd.min(),
            'worst_day': day.min(), 'annual_vol': day.std(ddof=1) * np.sqrt(252),
            'sharpe_zero_cash': day.mean() / day.std(ddof=1) * np.sqrt(252) if day.std(ddof=1) > 1e-12 else 0,
            'orders': len(sim.trades), 'fees': sim.path['fees'].iloc[-1],
            'slippage_cost': sim.path['slippage_cost'].iloc[-1], 'overhead': sim.path['overhead'].iloc[-1],
            'withheld_dividends': sim.path['withheld_dividends'].iloc[-1],
            'mean_exposure': sim.path['exposure'].mean()}
