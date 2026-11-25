import json

import pytest

from cash_cow.data import sha256
from cash_cow.intraday.trade_audit import audit_snapshot, summarize_response

START, END = '2023-06-05T13:51:00Z', '2023-06-05T13:52:00Z'


def response():
    return {'trades': {'SPY': [{'t': '2023-06-05T13:51:00.000000001Z', 'p': 100., 's': 10}]},
            'next_page_token': None}


def test_empty_success_is_not_proof_of_no_trading_and_partial_is_not_complete():
    assert summarize_response({'trades': None, 'next_page_token': None}, START, END)['status'] == 'no_records_returned'
    body = response()
    body['next_page_token'] = 'another-page'
    assert summarize_response(body, START, END) == {
        'returned_records': 1, 'pagination_complete': False, 'status': 'partial_response'}
    del body['next_page_token']
    with pytest.raises(KeyError):
        summarize_response(body, START, END)


@pytest.mark.parametrize('at', [END, '2023-06-05T13:50:59.999999999Z', '2023-06-05T13:51:00', 'NaT'])
def test_timestamp_bounds_preserve_nanosecond_and_exclusive_end(at):
    body = response(); body['trades']['SPY'][0]['t'] = at
    with pytest.raises(ValueError):
        summarize_response(body, START, END)


def test_rejects_holdout_oversized_interval_invalid_numbers_and_wrong_symbol():
    for start, end in [('2025-01-01T00:00Z', '2025-01-01T00:01Z'), (START, '2023-06-05T16:00Z')]:
        with pytest.raises(ValueError):
            summarize_response(response(), start, end)
    for value in (True, float('nan'), 0, -1):
        body = response(); body['trades']['SPY'][0]['p'] = value
        with pytest.raises(ValueError):
            summarize_response(body, START, END)
    with pytest.raises(ValueError):
        summarize_response({'trades': {'OTHER': []}, 'next_page_token': None}, START, END)


def test_snapshot_rejects_corruption_missing_provenance_and_duplicate_files(tmp_path):
    path = tmp_path/'response.json'; path.write_text(json.dumps(response()))
    probe = {'start': START, 'end_exclusive': END, 'response_file': path.name,
             'response_sha256': sha256(path), 'http_status': 200, 'observed_at': '2026-11-24T10:00:00Z'}
    manifest = {'endpoint': 'https://data.alpaca.markets/v2/stocks/trades',
                'symbol': 'SPY', 'feed': 'sip', 'probes': [probe]}
    meta = tmp_path/'manifest.json'; meta.write_text(json.dumps(manifest))
    before = path.read_bytes()
    assert audit_snapshot(meta)['probes'][0]['returned_records'] == 1
    assert path.read_bytes() == before
    manifest['probes'].append(probe); meta.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='duplicate'):
        audit_snapshot(meta)
    manifest['probes'].pop(); manifest['feed'] = 'iex'; meta.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='source'):
        audit_snapshot(meta)
    manifest['feed'] = 'sip'; meta.write_text(json.dumps(manifest)); path.write_text('{}')
    with pytest.raises(ValueError, match='hash'):
        audit_snapshot(meta)


@pytest.mark.parametrize('failure', ['future', 'private_timestamp', 'malformed_body', 'missing_file'])
def test_cli_rejects_invalid_evidence_without_echoing_private_payload(tmp_path, failure):
    import subprocess
    import sys

    marker = 'PRIVATE_SYNTHETIC_TIMESTAMP_MARKER'
    path = tmp_path/'response.json'
    body = response() if failure != 'malformed_body' else {'trades': {'SPY': [None]}, 'next_page_token': None}
    path.write_text(json.dumps(body))
    probe = {'start': START, 'end_exclusive': END, 'response_file': path.name,
             'response_sha256': sha256(path), 'http_status': 200,
             'observed_at': '2099-01-01T00:00:00Z' if failure == 'future' else
                            marker if failure == 'private_timestamp' else '2023-06-06T00:00:00Z'}
    meta = tmp_path/'manifest.json'
    meta.write_text(json.dumps({'endpoint': 'https://data.alpaca.markets/v2/stocks/trades',
                               'symbol': 'SPY', 'feed': 'sip', 'probes': [probe]}))
    if failure == 'missing_file':
        path.unlink()
    before = meta.read_bytes()
    result = subprocess.run([sys.executable, '-m', 'cash_cow.intraday.trade_audit', str(meta)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert json.loads(result.stdout) == {'status': 'review_required',
                                         'issues': ['invalid_or_unreadable_probe_evidence']}
    assert result.stderr == ''
    assert marker not in result.stdout and str(tmp_path) not in result.stdout
    assert meta.read_bytes() == before
