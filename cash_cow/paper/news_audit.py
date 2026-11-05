"""Audit the private news revision archive without exposing text or changing it.

Use --as-of with an explicit timezone to inspect only revisions observed by that
instant. Excluding later observations does not reconstruct missed news coverage.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .client import timestamp


def audit_news(directory, as_of=None):
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise ValueError("As-of time must include timezone")
    errors = Counter()
    revisions = Counter()
    days = Counter()
    observed_times, delays, manifest = [], [], []
    excluded, inspected = 0, 0
    directory = Path(directory)
    if not directory.is_dir():
        errors['missing_archive'] += 1
    for path in sorted(directory.glob('*.json')):
        if path.name == 'status.json':
            continue
        inspected += 1
        try:
            raw = path.read_bytes()
            manifest.append((path.name, hashlib.sha256(raw).hexdigest()))
            record = json.loads(raw)
            observed = timestamp(record['first_observed_at'])
            if observed > as_of:
                excluded += 1
                continue
            metadata = record['metadata']
            digest = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
            if record['sha256'] != digest or path.stem != digest:
                errors['revision_hash_mismatch'] += 1
                continue
            published = timestamp(metadata['created_at'])
            updated = timestamp(metadata['updated_at'])
            if published > observed or updated > observed or updated < published:
                errors['invalid_causal_timestamps'] += 1
                continue
            if metadata.get('id') is None:
                errors['missing_article_id'] += 1
                continue
            revisions[str(metadata['id'])] += 1
            days[observed.astimezone(timezone.utc).date().isoformat()] += 1
            observed_times.append(observed)
            delays.append((observed-updated).total_seconds())
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            errors['unreadable_or_invalid_record'] += 1
    if not observed_times:
        errors['no_valid_observations_at_cutoff'] += 1
    return {
        'as_of': as_of.isoformat(),
        'status': 'review_required' if errors else 'integrity_checks_passed',
        'files_inspected': inspected, 'valid_revisions': len(observed_times),
        'unique_articles': len(revisions), 'articles_with_multiple_revisions': sum(n>1 for n in revisions.values()),
        'excluded_observed_after_cutoff': excluded, 'errors': dict(errors),
        'first_observed_utc': min(observed_times).astimezone(timezone.utc).isoformat() if observed_times else None,
        'last_observed_utc': max(observed_times).astimezone(timezone.utc).isoformat() if observed_times else None,
        'observed_revisions_by_utc_day': dict(sorted(days.items())),
        'max_revision_observation_delay_seconds': max(delays, default=None),
        'manifest_sha256': hashlib.sha256(json.dumps(manifest).encode()).hexdigest(),
        'limits': 'Integrity of stored revisions only, not completeness, truth, relevance or current collector health. Metadata timestamps are supplied by the vendor. No headlines, URLs or article IDs are emitted. Files may be added during the audit.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', choices=('paper_v1','paper_ai_v1'), default='paper_ai_v1')
    parser.add_argument('--as-of', type=timestamp)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = audit_news(root/'data/telemetry'/args.config/'news', args.as_of)
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result['errors'] else 0)


if __name__ == '__main__':
    main()
