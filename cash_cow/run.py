"""Run the frozen experiment and export auditable local results."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .data import ROOT, fetch, load, sha256
from .engine import simulate, metrics, monthly_returns
from .strategies import make_signals

def paired_bootstrap(candidate, benchmark, samples, block, seed):
    x = (candidate - benchmark).dropna().to_numpy()
    rng = np.random.default_rng(seed)
    n = len(x)
    starts = rng.integers(0, n, size=(samples, int(np.ceil(n / block))))
    indices = ((starts[:, :, None] + np.arange(block)) % n).reshape(samples, -1)[:, :n]
    means = x[indices].mean(axis=1)
    observed = x.mean()
    # Centered block-bootstrap null, not a claim of distribution-free validity.
    p = (1 + ((means - observed) >= observed).sum()) / (samples + 1)
    return {'mean_monthly_excess_vs_bills': observed,
            'excess_ci95_low': np.quantile(means, 0.025), 'excess_ci95_high': np.quantile(means, 0.975),
            'one_sided_bootstrap_p': p}

def holm(pvalues):
    values = np.asarray(pvalues)
    order = np.argsort(values)
    adjusted = np.empty(len(values))
    adjusted[order] = np.minimum(1, np.maximum.accumulate(values[order] * np.arange(len(values), 0, -1)))
    return adjusted

def markdown_table(df, columns):
    lines = ['| ' + ' | '.join(columns) + ' |', '|' + '|'.join(['---'] * len(columns)) + '|']
    for _, row in df.iterrows():
        vals = []
        for c in columns:
            x = row[c]
            if c in ['mean_month', 'positive_month_fraction', 'worst_month', 'max_drawdown', 'cagr']:
                vals.append(f'{x:.2%}')
            elif isinstance(x, (float, np.floating)):
                vals.append(f'{x:.2f}')
            else:
                vals.append(str(x))
        lines.append('| ' + ' | '.join(vals) + ' |')
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--label', default='initial')
    args = parser.parse_args()
    config_path = ROOT / 'configs/experiment_v1.json'
    c = json.loads(config_path.read_text())
    if args.fetch:
        fetch(c)
    frames = load(c)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + args.label
    out = ROOT / 'reports/runs' / run_id
    out.mkdir(parents=True, exist_ok=False)
    for directory in ['paths', 'trades', 'monthly']:
        (out / directory).mkdir()
    source_paths = sorted((ROOT / 'cash_cow').glob('*.py'))
    manifest = {'run_id': run_id, 'research_date': c['research_date'], 'config': c,
                'config_sha256': sha256(config_path), 'sources': {str(p.relative_to(ROOT)): sha256(p) for p in source_paths},
                'data_files': {s: sha256(ROOT / f'data/raw/{s}.csv') for s in c['symbols']},
                'python': platform.python_version(), 'live_approved': False,
                'classification': 'Retrospective historical screen; no forward-paper track record'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    start_time = time.monotonic()
    summaries, base_months, paths, regimes = [], {}, {}, []
    signal_cache = {}
    for scenario in c['scenarios']:
        settings = dict(c['base'], capital=c['capital'])
        settings.update({k: v for k, v in scenario.items() if k != 'name'})
        for name in c['strategies'] + c['benchmarks']:
            key = (name, settings['exposure_cap'])
            if key not in signal_cache:
                signal_cache[key] = make_signals(frames, name, settings['exposure_cap'])
            sim = simulate(frames, signal_cache[key], name, settings, c['validation_start'], c['validation_end'])
            tag = f'{scenario["name"]}__{name}'
            row = {'scenario': scenario['name'], 'strategy': name, 'window': 'validation', **metrics(sim, settings['capital'])}
            summaries.append(row)
            sim.path.to_csv(out / 'paths' / f'{tag}.csv')
            sim.trades.to_csv(out / 'trades' / f'{tag}.csv', index=False)
            monthly = monthly_returns(sim.path, settings['capital'])
            monthly.rename('return').to_csv(out / 'monthly' / f'{tag}.csv')
            if scenario['name'] == '01_base':
                base_months[name] = monthly
                paths[name] = sim.path
                # Full-history diagnostic, kept separate from the validation comparison.
                history = simulate(frames, signal_cache[key], name, settings, c['development_start'], c['validation_end'])
                summaries.append({'scenario': scenario['name'], 'strategy': name, 'window': 'full_history_diagnostic', **metrics(history, settings['capital'])})
                for year in [2008, 2011, 2018, 2020, 2022]:
                    y = history.path.loc[str(year), 'equity']
                    prev = history.path.loc[history.path.index < y.index[0], 'equity']
                    initial = prev.iloc[-1] if len(prev) else settings['capital']
                    dd = y / y.cummax().clip(lower=initial) - 1
                    regimes.append({'strategy': name, 'year': year, 'return': y.iloc[-1] / initial - 1, 'max_drawdown_within_year': dd.min()})
        print('Completed', scenario['name'], flush=True)
    results = pd.DataFrame(summaries)
    results.to_csv(out / 'summary.csv', index=False)
    pd.DataFrame(regimes).to_csv(out / 'regimes.csv', index=False)
    stats = []
    for name in c['strategies']:
        stats.append({'strategy': name, **paired_bootstrap(base_months[name], base_months['bills_100'],
                     c['selection']['bootstrap_samples'], c['selection']['bootstrap_block_months'], c['selection']['seed'])})
    inference = pd.DataFrame(stats)
    inference['holm_p'] = holm(inference['one_sided_bootstrap_p'])
    inference.to_csv(out / 'inference.csv', index=False)
    pd.DataFrame(base_months).to_csv(out / 'base_monthly.csv')
    base = results[(results.scenario == '01_base') & (results.window == 'validation')].copy()
    base['mean_month_usd_at_2000'] = base['mean_month'] * 2000
    base = base.sort_values('mean_month', ascending=False)
    plot(paths, out)
    table = markdown_table(base, ['strategy', 'mean_month', 'mean_month_usd_at_2000', 'positive_month_fraction', 'worst_month', 'max_drawdown', 'orders'])
    riskpass = base[(base.strategy.isin(c['strategies'])) & (base.max_drawdown >= -c['selection']['provisional_max_drawdown']) & (base.worst_month >= c['selection']['provisional_worst_month'])].strategy.tolist()
    statpass = inference.loc[inference.holm_p < c['selection']['holm_alpha'], 'strategy'].tolist()
    report = f'''# Initial historical screening results

Research date: {c['research_date']}. Run: `{run_id}`. **No strategy is approved for live trading.**

Executed 10 candidate strategies × 10 scenarios = 100 validation simulations, plus 30 matched benchmark simulations and 13 full-history diagnostics. The scenarios overlap and are **not independent replications**. All trials are retained, including losing ones.

Validation: {c['validation_start']} through {c['validation_end']}; 108 calendar months. Full-history diagnostics begin in 2008. 2025 onward was not fetched. These are historical rules chosen today, so the validation interval is a retrospective screen, not genuinely future evidence. No parameter optimization was performed.

Each candidate has its own USD 2,000 research account. Base target risky allocation is at most 25% at rebalances; prices can push realized exposure above the target between rebalances. This is not a 25% maximum-loss guarantee. `spy_25` is a matched-exposure equity benchmark; `bills_100` buys 99% BIL once with a fee buffer and holds cash distributions. Idle cash earns zero.

{table}

`mean_month_usd_at_2000` multiplies historical average monthly percentage by $2,000 for scale. It is **not** a forecast, withdrawal income, or actual average monthly P&L in the compounding simulation. Flat months are not counted as profitable. NAV includes unrealized gains/losses and dividend/sale receivables. Final positions are marked, not liquidated.

## Screening checks

Within provisional historical risk limits (drawdown ≤5%, worst month ≥−2%): {', '.join(riskpass) or 'none'}.

Positive monthly excess over the bill benchmark passing the approximate one-sided block-bootstrap test after Holm correction across ten candidates: {', '.join(statpass) or 'none'}.

This bootstrap uses paired monthly excess returns, 3-month circular blocks, {c['selection']['bootstrap_samples']:,} samples and a fixed seed. It is an exploratory estimate conditional on this history, not a guarantee. It does not cure data revisions, universe selection, prior knowledge of history, or future regime change. Changing blocks or adding strategies counts as further research trials.

## Important limits

- Research data from one unofficial vendor; not yet cross-checked against broker/issuer data.
- Next-session open with assumed slippage, no quote/queue/partial-fill/auction reconstruction. Delays are session-scale robustness tests, not measured network latency.
- $0.40 flat charge per order in the base case is a screening assumption, not an exact IBKR invoice. Higher fees and $10/month operating costs have separate scenarios.
- Three exchange-session sale settlement buffer throughout history; not an exact historical or current broker settlement calendar. Dividend cash is delayed 30 sessions; actual payable dates are not available. NAV recognizes entitlement on ex-date.
- Equity distributions are haircut 30%; Treasury ETF distributions assume zero withholding in base, with 30% on all distributions in tax stress. Fund-specific classifications and broker implementation are unverified.
- Fractional shares assumed in base; whole-share stress included. Reverse-split fractional entitlements are retained rather than broker-specific cash-in-lieu processing.
- No FX changes, conversion/remittance charges, Singapore personal income tax determination, or full infrastructure budget in base. USD results can differ substantially in SGD.
- ETF universe was selected today; it is not a survivorship-free whole-US-stock-market study. Several candidates share the same trend/equity exposure and are not independent sources of profit.

Read `docs/RESEARCH.md` and `docs/METHODOLOGY.md` before interpreting the CSVs. Forward paper trading has not started.
'''
    (out / 'RESULTS.md').write_text(report)
    (ROOT / 'reports/LATEST.txt').write_text(str(out.relative_to(ROOT)) + '\n')
    manifest['elapsed_seconds'] = time.monotonic() - start_time
    manifest['completed_simulations'] = len(summaries)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(table)
    print(f'Report: {out / "RESULTS.md"}')

def plot(paths, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    for name, p in paths.items():
        eq = p.equity
        style = '--' if name in ('cash', 'spy_25', 'bills_100') else '-'
        axes[0].plot(eq.index, eq, style, label=name, linewidth=1.3)
        axes[1].plot(eq.index, (eq / eq.cummax().clip(lower=2000) - 1) * 100, style, linewidth=1)
    axes[0].set_title('Cash Cow · Historical screening only · 2016–2024\nUSD 2,000 each; candidate allocation capped at 25% at rebalances')
    axes[0].set_ylabel('Account equity (USD)')
    axes[0].legend(ncol=3, fontsize=8, loc='upper left')
    axes[1].set_ylabel('Drawdown (%)')
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.text(0.5, 0.01, 'Historical simulations with assumed costs. No future performance or live-trading approval implied.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(out / 'equity_drawdown.png', dpi=160)
    plt.close(fig)

if __name__ == '__main__':
    main()
