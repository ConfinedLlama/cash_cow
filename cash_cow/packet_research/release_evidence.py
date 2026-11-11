"""Read-only checks joining manual release records to saved evidence bytes.

This verifies consistency, not the truth of an extraction or source authorship.
No network, model or trading integration is provided.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from cash_cow.paper.client import timestamp
from .history import digest
from .releases import select_releases

METHODS = {'http_response_body', 'web_tool_rendering'}


def verify_release_evidence(records, manifest, directory, as_of):
    selected = select_releases(records, as_of)
    if (not isinstance(manifest, dict) or set(manifest) != {'schema', 'sources', 'reviews'}
            or manifest['schema'] != 'release_evidence_v1'
            or not isinstance(manifest['sources'], list) or not isinstance(manifest['reviews'], list)):
        raise ValueError('invalid_evidence_manifest')
    directory = Path(directory)
    sources, reviews, file_hashes = {}, {}, {}
    for source in manifest['sources']:
        if not isinstance(source, dict) or set(source) != {'sha256', 'url', 'file', 'method', 'received_at'}:
            raise ValueError('invalid_evidence_source')
        sha, name = source['sha256'], source['file']
        if (not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha)
                or not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', name)
                or not isinstance(source['method'], str) or source['method'] not in METHODS or sha in sources):
            raise ValueError('invalid_or_duplicate_evidence_source')
        timestamp(source['received_at'])
        path = directory/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('source_file_missing_or_symlink')
        with path.open('rb') as stream:
            raw = stream.read(5_000_001)
        if not raw or len(raw) > 5_000_000 or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('source_bytes_mismatch_or_size')
        sources[sha] = source
        file_hashes[path] = sha
    for review in manifest['reviews']:
        if not isinstance(review, dict) or set(review) != {'record_sha256', 'reviewed_at'}:
            raise ValueError('invalid_review')
        sha = review['record_sha256']
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha) or sha in reviews:
            raise ValueError('invalid_or_duplicate_review')
        reviews[sha] = timestamp(review['reviewed_at'])
    used_sources, used_reviews = set(), set()
    for record in records:
        sha, record_hash = record['source_sha256'], digest(record)
        source, reviewed = sources.get(sha), reviews.get(record_hash)
        if source is None or reviewed is None or source['url'] != record['source_url']:
            raise ValueError('missing_or_mismatched_source_or_review')
        if not timestamp(record['published_at']) <= timestamp(source['received_at']) <= reviewed <= timestamp(record['first_observed_at']):
            raise ValueError('backdated_source_review_or_observation')
        used_sources.add(sha);used_reviews.add(record_hash)
    if used_sources != set(sources) or used_reviews != set(reviews):
        raise ValueError('unreferenced_source_or_review')
    for path, sha in file_hashes.items():
        with path.open('rb') as stream:
            raw = stream.read(5_000_001)
        if path.is_symlink() or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('source_changed_during_audit')
    return {'status': 'provenance_checks_passed', 'as_of': as_of,
            'records': len(records), 'sources': len(sources),
            'capture_methods': dict(Counter(s['method'] for s in sources.values())),
            'eligible_values': len(selected['values']),
            'excluded_not_yet_observed': selected['excluded_not_yet_observed'],
            'excluded_stale': selected['excluded_stale'],
            'manifest_sha256': digest(manifest), 'records_sha256': digest(records),
            'limits': 'Hashes, URLs and review times are local provenance assertions, not authenticated authorship or verified numeric extraction. Web rendering is not original HTTP bytes. No retroactive model input, signal or performance claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--as-of', required=True)
    args = parser.parse_args()
    try:
        result = verify_release_evidence(json.loads(args.records.read_bytes()),
                                        json.loads(args.manifest.read_bytes()),
                                        args.manifest.parent, args.as_of)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print(json.dumps({'status': 'review_required', 'issues': ['invalid_release_evidence']}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
