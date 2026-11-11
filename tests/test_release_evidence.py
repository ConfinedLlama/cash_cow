"""Synthetic source captures and manually asserted values, never actual releases."""
from copy import deepcopy
import hashlib
import json

import pytest

from cash_cow.packet_research.history import digest
from cash_cow.packet_research.release_evidence import verify_release_evidence


def fixture(folder):
    raw = b'Synthetic source evidence, not a genuine BLS document'
    (folder/'capture.txt').write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    record = {'release_id': 'fixture_cpi', 'metric': 'cpi_mom', 'period': '2026-10',
              'unit': 'percent', 'value': 0.4, 'source_sha256': sha,
              'source_url': 'https://www.bls.gov/news.release/archives/cpi_11102026.htm',
              'published_at': '2026-11-10T13:30:00Z', 'vintage_at': '2026-11-10T13:30:00Z',
              'first_observed_at': '2026-11-11T08:00:02Z'}
    manifest = {'schema': 'release_evidence_v1', 'sources': [
        {'sha256': sha, 'url': record['source_url'], 'file': 'capture.txt',
         'method': 'web_tool_rendering', 'received_at': '2026-11-11T08:00:00Z'}],
        'reviews': [{'record_sha256': digest(record), 'reviewed_at': '2026-11-11T08:00:01Z'}]}
    return [record], manifest


def test_read_only_verification_does_not_backdate_today_into_yesterday(tmp_path):
    records, manifest = fixture(tmp_path);before = deepcopy((records, manifest))
    raw = (tmp_path/'capture.txt').read_bytes()
    old = verify_release_evidence(records, manifest, tmp_path, '2026-11-10T20:00:00Z')
    assert old['eligible_values'] == 0 and old['excluded_not_yet_observed'] == 1
    current = verify_release_evidence(records, manifest, tmp_path, '2026-11-11T08:00:02Z')
    assert current['eligible_values'] == 1
    assert current['capture_methods'] == {'web_tool_rendering': 1}
    assert (records, manifest) == before and (tmp_path/'capture.txt').read_bytes() == raw


@pytest.mark.parametrize('change', ['bytes', 'value', 'url', 'unreviewed', 'unreferenced',
                                  'before_capture', 'before_publication', 'backdated',
                                  'duplicate_source', 'duplicate_review', 'method', 'traversal'])
def test_unreliable_provenance_fails_closed(tmp_path, change):
    records, manifest = fixture(tmp_path)
    source = manifest['sources'][0];review = manifest['reviews'][0]
    if change == 'bytes':(tmp_path/'capture.txt').write_text('modified')
    elif change == 'value':records[0]['value'] = 99
    elif change == 'url':source['url'] = 'https://example.invalid'
    elif change == 'unreviewed':manifest['reviews'] = []
    elif change == 'unreferenced':records = []
    elif change == 'before_capture':review['reviewed_at'] = '2026-11-11T07:59:59Z'
    elif change == 'before_publication':source['received_at'] = '2026-11-10T13:00:00Z'
    elif change == 'backdated':
        records[0]['first_observed_at'] = '2026-11-10T14:00:00Z'
        review['record_sha256'] = digest(records[0])
    elif change == 'duplicate_source':manifest['sources'].append(dict(source))
    elif change == 'duplicate_review':manifest['reviews'].append(dict(review))
    elif change == 'method':source['method'] = 'imagined_raw_http'
    elif change == 'traversal':source['file'] = '../capture.txt'
    with pytest.raises(ValueError):verify_release_evidence(records, manifest, tmp_path, '2026-11-11T09:00:00Z')


def test_symlink_cannot_read_outside_capture_directory(tmp_path):
    records, manifest = fixture(tmp_path)
    path = tmp_path/'capture.txt';path.rename(tmp_path/'other.txt');path.symlink_to(tmp_path/'other.txt')
    with pytest.raises(ValueError, match='symlink'):
        verify_release_evidence(records, manifest, tmp_path, '2026-11-11T09:00:00Z')


def test_stale_values_stay_excluded_even_with_valid_source(tmp_path):
    records, manifest = fixture(tmp_path)
    result = verify_release_evidence(records, manifest, tmp_path, '2026-11-18T09:00:00Z')
    assert result['eligible_values'] == 0 and result['excluded_stale'] == 1


def test_concurrent_source_edit_is_detected(tmp_path, monkeypatch):
    import cash_cow.packet_research.release_evidence as module
    records, manifest = fixture(tmp_path)
    original = module.digest
    def change_after_source_read(record):
        result = original(record)
        (tmp_path/'capture.txt').write_text('modified during review')
        return result
    monkeypatch.setattr(module, 'digest', change_after_source_read)
    with pytest.raises(ValueError, match='changed_during_audit'):
        verify_release_evidence(records, manifest, tmp_path, '2026-11-11T09:00:00Z')
