"""Read-only v3 archive audit; aggregate output, no models or market requests."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from cash_cow.paper.client import timestamp
from .history import digest
from .packet import ARMS
from .packet_v3 import VERSION, build_packet, load_spec

BAD_INPUT = (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError)
CAPTURE_STATUSES = {'captured', 'incomplete_bars', 'market_closed', 'no_completed_minute'}


def audit_packets(directory, captures_directory, release_path=None, evidence_path=None):
    directory, captures_directory = Path(directory), Path(captures_directory)
    inputs, errors, captures, capture_statuses = {}, Counter(), [], Counter()
    decision_paths = sorted((directory/'ai_decisions').glob('*.json'))
    capture_paths = sorted(captures_directory.glob('*.json'))

    def read(path):
        if path.is_symlink():raise ValueError('symlink')
        with path.open('rb') as stream:raw = stream.read(1_000_001)
        if len(raw) > 1_000_000:raise ValueError('oversize')
        inputs[path] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    releases, evidence = [], None
    if release_path is not None or evidence_path is not None:
        try:
            if release_path is None or evidence_path is None:raise ValueError('missing_pair')
            releases, evidence = read(Path(release_path)), read(Path(evidence_path))
        except BAD_INPUT:
            errors['invalid_release_evidence_inputs'] += 1
            releases = None
    for path in capture_paths:
        try:
            record = read(path)
            if path.stem != inputs[path] or record['schema'] != 'receipt_capture_v1':
                raise ValueError('capture_identity')
            status = record['status']
            if status not in CAPTURE_STATUSES:raise ValueError('capture_status')
            # Incomplete/closed observations are retained, not skipped in favor
            # of an older usable capture. Full consistency is checked per arm.
            receipt = record['bars'] if record.get('bars') is not None else record['clock']
            at = timestamp(receipt['received_at'])
            captures.append((at, path.stem, record));capture_statuses[status] += 1
        except BAD_INPUT:
            errors['invalid_capture'] += 1
    if not capture_paths:errors['missing_captures'] += 1
    if not decision_paths:errors['missing_decisions'] += 1
    captures.sort(key=lambda row: (row[0], row[1]))
    arms = {arm: {'assembled': 0, 'rejected': 0, 'packet_bytes_max': 0, 'reasons': Counter()} for arm in ARMS}
    statuses, availability, packets = Counter(), Counter(), []
    for path in decision_paths:
        try:
            record = read(path)
            if record['status'] not in {'completed', 'pending', 'failed'}:raise ValueError('status')
            statuses[record['status']] += 1
            context = record['context'];cutoff = timestamp(context['as_of'])
        except BAD_INPUT:
            errors['invalid_decision'] += 1
            for arm in arms.values():
                arm['rejected'] += 1;arm['reasons']['invalid_decision'] += 1
            continue
        eligible = [row for row in captures if row[0] <= cutoff]
        selected = eligible[-1][2] if eligible else None
        ambiguous = bool(eligible and len({r[1] for r in eligible if r[0] == eligible[-1][0]}) > 1)
        for arm, counts in arms.items():
            reason = None
            if arm != 'baseline':
                if errors['invalid_capture']:reason = 'invalid_capture_archive'
                elif selected is None:reason = 'no_capture_before_cutoff'
                elif ambiguous:reason = 'ambiguous_latest_capture'
            if arm == 'history_and_releases' and releases is None:reason = 'invalid_release_evidence_inputs'
            if reason is None:
                try:
                    result = build_packet(context, selected, releases, arm, evidence=evidence,
                                          evidence_directory=Path(evidence_path).parent if evidence_path else None)
                    counts['assembled'] += 1
                    counts['packet_bytes_max'] = max(counts['packet_bytes_max'], result['packet_bytes'])
                    packets.append((inputs[path], arm, result['packet_sha256']))
                    if arm == 'history_and_releases':
                        values = result['packet']['official_releases']
                        availability[values['availability']] += 1
                        availability['excluded_not_yet_observed'] += values['excluded_not_yet_observed']
                except BAD_INPUT:
                    # Fixed error category: never echo raw source values.
                    reason = 'packet_validation_failed'
            if reason:
                counts['rejected'] += 1;counts['reasons'][reason] += 1
    for path, sha in inputs.items():
        try:
            with path.open('rb') as stream:raw = stream.read(1_000_001)
            if path.is_symlink() or hashlib.sha256(raw).hexdigest() != sha:
                errors['source_changed_during_audit'] += 1
        except OSError:errors['source_disappeared_during_audit'] += 1
    if (decision_paths != sorted((directory/'ai_decisions').glob('*.json'))
            or capture_paths != sorted(captures_directory.glob('*.json'))):
        errors['archive_membership_changed'] += 1
    return {'version': VERSION, 'as_of': datetime.now(timezone.utc).isoformat(),
            'status': 'review_required' if any(errors.values()) or any(a['rejected'] for a in arms.values()) else 'construction_checks_passed',
            'decision_records': len(decision_paths), 'decision_statuses': dict(statuses),
            'capture_records': len(capture_paths), 'capture_statuses': dict(capture_statuses),
            'arms': arms, 'release_availability': dict(availability),
            'archive_errors': {k: v for k, v in errors.items() if v},
            'input_hashes_sha256': digest(sorted(inputs.values())),
            'packet_manifest_sha256': digest(sorted(packets)), 'specification_sha256': digest(load_spec()),
            'code_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
            'limits': 'Previously inspected development data; no model calls, executions or returns. Missing/failed observations retained. Local hashes/times are not authenticated source identity. Read-only checks are not an atomic filesystem snapshot.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--captures', type=Path, required=True)
    parser.add_argument('--releases', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    try:
        result = audit_packets(args.directory, args.captures, args.releases, args.evidence)
    except BAD_INPUT:
        result = {'status': 'review_required', 'issues': ['invalid_archive_or_specification']}
    print(json.dumps(result, indent=2))
    return 2 if result['status'] == 'review_required' else 0


if __name__ == '__main__':
    raise SystemExit(main())
