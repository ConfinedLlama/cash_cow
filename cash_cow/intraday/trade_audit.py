"""Offline audit of bounded historical SPY trade probes, not gap exemptions."""
import argparse
import json
import math
from pathlib import Path

import pandas as pd

from cash_cow.data import sha256


def summarize_response(body, start, end):
    """Empty successful responses mean no returned records, not no trading."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if (pd.isna(start) or pd.isna(end) or start.tz is None or end.tz is None
            or not pd.Timestamp('2016-01-01', tz='UTC') <= start < end
            or end > pd.Timestamp('2025-01-01', tz='UTC')
            or end-start > pd.Timedelta(hours=1)):
        raise ValueError('Outside bounded historical probe interval')
    token = body['next_page_token']
    if token is not None and (not isinstance(token, str) or not token):
        raise ValueError('Invalid pagination evidence')
    trades = body['trades']
    if trades is None:
        trades = {}
    if not isinstance(trades, dict) or not trades.keys() <= {'SPY'}:
        raise ValueError('Unexpected trade symbols')
    rows = trades.get('SPY', [])
    if not isinstance(rows, list):
        raise ValueError('Invalid trade records')
    previous = None
    for row in rows:
        at = pd.Timestamp(row['t'])
        if (pd.isna(at) or at.tz is None or not start <= at < end
                or (previous is not None and at < previous)):
            raise ValueError('Trade timestamp outside interval or unordered')
        for field in ('p', 's'):
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('Invalid trade price or size')
        previous = at
    return {'returned_records': len(rows), 'pagination_complete': token is None,
            'status': 'partial_response' if token is not None else
                      'records_returned' if rows else 'no_records_returned'}


def audit_snapshot(manifest_path):
    """Verify private response hashes and request metadata without networking."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if (manifest['endpoint'] != 'https://data.alpaca.markets/v2/stocks/trades'
            or manifest['symbol'] != 'SPY' or manifest['feed'] != 'sip'):
        raise ValueError('Unrecognized historical probe source')
    results, seen = [], set()
    for probe in manifest['probes']:
        name = probe['response_file']
        if not isinstance(name, str) or Path(name).name != name or name in seen:
            raise ValueError('Invalid or duplicate response file')
        seen.add(name)
        path = manifest_path.parent/name
        if sha256(path) != probe['response_sha256']:
            raise ValueError('Probe response hash mismatch')
        if probe['http_status'] != 200:
            raise ValueError('Probe response was not successful')
        observed = pd.Timestamp(probe['observed_at'])
        if pd.isna(observed) or observed.tz is None or observed < pd.Timestamp(probe['end_exclusive']):
            raise ValueError('Invalid observation timestamp')
        summary = summarize_response(json.loads(path.read_text()), probe['start'], probe['end_exclusive'])
        results.append({'start': probe['start'], 'end_exclusive': probe['end_exclusive'],
                        'response_sha256': probe['response_sha256'], **summary})
    if not results:
        raise ValueError('No probe evidence')
    return {'manifest_sha256': sha256(manifest_path), 'probes': results,
            'limits': 'Returned records from one provider only. Empty responses do not prove a halt '
                      'or absence of trading. Partial responses are lower bounds. No OHLC reconstruction, '
                      'bar eligibility classification, source repair or permission to run a strategy.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    result = audit_snapshot(args.manifest)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 2 if any(not row['pagination_complete'] for row in result['probes']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
