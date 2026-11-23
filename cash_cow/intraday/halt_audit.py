"""Describe historical gap overlap with sourced halts; never exempt gaps."""
import json

import pandas as pd

from cash_cow.data import ROOT, sha256
from .input_audit import audit_cache


def _intervals(rows, minute_grid=False):
    intervals = []
    for row in rows:
        start, end = pd.Timestamp(row['start']), pd.Timestamp(row['end_exclusive'])
        if (pd.isna(start) or pd.isna(end) or start.tz is None or end.tz is None
                or start >= end):
            raise ValueError('Invalid interval')
        start, end = start.tz_convert('UTC'), end.tz_convert('UTC')
        if intervals and start < intervals[-1][1]:
            raise ValueError('Intervals must be ordered and nonoverlapping')
        if minute_grid and (start != start.floor('min') or end != end.floor('min')
                            or type(row['minutes']) is not int
                            or row['minutes'] != (end-start)/pd.Timedelta(minutes=1)):
            raise ValueError('Invalid missing-minute interval')
        intervals.append((start, end))
    return intervals


def classify_gaps(gaps, halts):
    """Classify each missing minute using half-open UTC intervals.

    Full containment is temporal correspondence, not evidence of causation or
    permission to invent executable prices. Partial trigger/reopen minutes
    remain separate from full minutes inside a halt.
    """
    gap_intervals = _intervals(gaps, minute_grid=True)
    halt_intervals = _intervals(halts)
    totals = {'fully_contained': 0, 'partially_overlapping': 0, 'outside_known_halts': 0}
    rows = []
    for original, (start, end) in zip(gaps, gap_intervals):
        counts = dict.fromkeys(totals, 0)
        for minute in pd.date_range(start, end, freq='min', inclusive='left'):
            minute_end = minute+pd.Timedelta(minutes=1)
            overlap = sum((max(pd.Timedelta(0), min(minute_end, stop)-max(minute, begin))
                           for begin, stop in halt_intervals), pd.Timedelta(0))
            label = ('fully_contained' if overlap == pd.Timedelta(minutes=1)
                     else 'partially_overlapping' if overlap > pd.Timedelta(0)
                     else 'outside_known_halts')
            counts[label] += 1
            totals[label] += 1
        rows.append({**original, **counts})
    return {'missing_minutes': sum(totals.values()), 'counts': totals, 'intervals': rows}


def audit_halts(root=ROOT):
    diagnostic = audit_cache(root)
    reference_path = root/'configs/historical_mwcb_2020.json'
    reference = json.loads(reference_path.read_text())
    result = classify_gaps(diagnostic['missing_intervals'], reference['halts'])
    result.update({
        'status': diagnostic['status'],
        'unchanged_input_issues': diagnostic['issues'],
        'input_source_sha256': diagnostic['source_sha256'],
        'halt_reference_sha256': sha256(reference_path),
        'halt_source': reference['source'],
        'halt_source_published': reference['published'],
        'limits': 'Retrospective temporal overlap only. Known halts are not exhaustive or '
                  'symbol-specific reopening times. No validation exemption, price repair, '
                  'strategy evaluation or causal model input. All original issues are retained.',
    })
    return result


def main():
    result = audit_halts()
    print(json.dumps(result, indent=2, allow_nan=False))
    return 2 if result['unchanged_input_issues'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
