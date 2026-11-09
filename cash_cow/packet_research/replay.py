"""Audit offline packet construction on existing archives; never call a model.

Print aggregate counts and hashes only. No raw news, prices, rationale, account
fields or generated packets are printed or written. No historical data fetch.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from cash_cow.paper.client import timestamp
from .history import digest
from .packet import ARMS, build_packet, load_spec


def audit_packets(directory, release_path=None):
    directory = Path(directory)
    inputs, errors, snapshots = {}, Counter(), []
    releases = []

    def read(path):
        raw = path.read_bytes()
        inputs[path] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    if release_path is not None:
        try:
            releases = read(Path(release_path))
        except (OSError, ValueError):
            errors['unreadable_release_archive'] += 1
            releases = None
    for path in sorted((directory/'bars').glob('*.json')):
        try:
            value = read(path)
            snapshots.append((timestamp(value['observed_at']), digest(value), value))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            errors['invalid_snapshot'] += 1
    if not snapshots:
        errors['missing_snapshots'] += 1
    snapshots.sort(key=lambda row: (row[0], row[1]))
    arms = {arm: {'assembled': 0, 'rejected': 0, 'packet_bytes_max': 0} for arm in ARMS}
    observations, statuses, packet_hashes = Counter(), Counter(), []
    paths = sorted((directory/'ai_decisions').glob('*.json'))
    if not paths:
        errors['missing_decisions'] += 1
    for path in paths:
        try:
            record = read(path)
            if record['status'] not in {'pending','failed','completed'}:
                raise ValueError('invalid_status')
            statuses[record['status']] += 1
            context = record['context']
            cutoff = timestamp(context['as_of'])
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            errors['invalid_decision_record'] += 1
            for arm in ARMS: arms[arm]['rejected'] += 1
            continue
        eligible = [row for row in snapshots if row[0] <= cutoff]
        snapshot = eligible[-1][2] if eligible else None
        ambiguous = bool(eligible and len({row[1] for row in eligible if row[0] == eligible[-1][0]}) > 1)
        for arm in ARMS:
            try:
                if arm != 'baseline' and (snapshot is None or ambiguous):
                    raise ValueError('missing_or_ambiguous_snapshot')
                result = build_packet(context, snapshot, releases, arm)
                arms[arm]['assembled'] += 1
                arms[arm]['packet_bytes_max'] = max(arms[arm]['packet_bytes_max'], result['packet_bytes'])
                packet_hashes.append((path.name, arm, result['packet_sha256']))
                if arm == 'history_and_releases':
                    release_data = result['packet']['official_releases']
                    observations[release_data['availability']] += 1
                    observations['excluded_future_values'] += release_data['excluded_not_yet_observed']
            except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
                # Do not echo exceptions that could contain private input strings.
                arms[arm]['rejected'] += 1
    for path, original in inputs.items():
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != original:
                errors['source_changed_during_audit'] += 1
        except OSError:
            errors['source_disappeared_during_audit'] += 1
    sources = [(str(p.relative_to(directory)) if p.is_relative_to(directory) else 'release_archive', h)
               for p,h in inputs.items()]
    code = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(__file__).parent.glob('*.py')}
    return {'as_of': datetime.now(timezone.utc).isoformat(),
            'status': 'review_required' if errors or any(a['rejected'] for a in arms.values()) else 'construction_checks_passed',
            'records': len(paths), 'baseline_record_statuses': dict(statuses), 'arms': arms,
            'release_availability': dict(observations), 'archive_errors': dict(errors),
            'input_manifest_sha256': digest(sorted(sources)),
            'packet_manifest_sha256': digest(sorted(packet_hashes)),
            'code_sha256': code, 'specification_sha256': digest(load_spec()),
            'limits': 'Legacy tick-start timestamps are not verified receipt times. Previously inspected development data, not an out-of-sample trial. No model calls, counterfactual actions, fills, returns or source authenticity claims. Source hashes cover files read, not an atomic directory snapshot.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True, help='Existing private paper telemetry directory')
    parser.add_argument('--releases', type=Path, help='Manually verified official-release archive; omitted means unavailable')
    args = parser.parse_args()
    result = audit_packets(args.directory.resolve(), args.releases.resolve() if args.releases else None)
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result['status'] == 'review_required' else 0)


if __name__ == '__main__':
    main()
