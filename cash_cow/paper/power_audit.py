"""Sanitize a saved macOS pmset power log; never change power or service state.

Recognized transitions are observations, not measured runner availability.
DarkWake is a partial wake and is not proof that network/trading work succeeded.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .client import timestamp

TRANSITION = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d{4})\s+(Sleep|DarkWake|Wake)\s{2,}(.*)$')
REASONS = {'Clamshell Sleep': 'clamshell', 'Maintenance Sleep': 'maintenance',
           'Idle Sleep': 'idle', 'Sleep Service Back to Sleep': 'sleep_service'}


def audit(raw, start, end, now=None):
    now = now or datetime.now(timezone.utc)
    if any(t.tzinfo is None for t in (start, end, now)) or not start < end <= now:
        raise ValueError('Require an elapsed timezone-aware interval')
    if (end-start).total_seconds() > 172800:
        raise ValueError('Power review window exceeds two days')
    issues, rows, previous = [], [], None
    try:
        lines = raw.decode('utf-8').splitlines()
    except UnicodeError:
        lines=[];issues.append('invalid_log_encoding')
    for line in lines:
        match = TRANSITION.match(line)
        if not match:
            continue  # In particular, Wake Requests and Assertions are not wakes.
        stamp, kind, detail = match.groups()
        try:
            at = datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S %z').astimezone(timezone.utc)
        except ValueError:
            issues.append('invalid_transition_timestamp');continue
        if previous is not None and at < previous:
            issues.append('nonmonotonic_transitions')
        previous = at
        if at > now:
            issues.append('future_transition');continue
        reason = None
        if kind == 'Sleep':
            found = re.search(r"Entering Sleep state due to '([^']+)'", detail)
            reason = REASONS.get(found[1], 'other') if found else 'unknown'
        power = 'battery' if re.search(r'\bUsing BATT?\b', detail, re.I) else (
            'ac' if re.search(r'\bUsing AC\b', detail, re.I) else 'unknown')
        rows.append({'at':at.isoformat(), 'kind':kind, 'reason':reason, 'power_source':power})
    # Do not infer continuity or asleep duration from missing/rotated records.
    before = [r for r in rows if timestamp(r['at']) < start]
    selected = [r for r in rows if start <= timestamp(r['at']) < end]
    if not selected:
        issues.append('no_transitions_in_window')
    return {'as_of':now.isoformat(), 'window_start':start.isoformat(), 'window_end':end.isoformat(),
            'status':'review_required' if issues else 'observations_available',
            'issues':sorted(set(issues)), 'source_sha256':hashlib.sha256(raw).hexdigest(),
            'last_transition_before_window':before[-1] if before else None,
            'transition_counts':dict(Counter(r['kind'] for r in selected)),
            'sleep_reason_counts':dict(Counter(r['reason'] for r in selected if r['kind']=='Sleep')),
            'transitions':selected,
            'limits':'Saved-log observations only; log retention/completeness unverified. '
                     'DarkWake is not full wake or proof of working network/model access. '
                     'No transitions does not establish uninterrupted uptime. '
                     'No sleep duration, strategy performance or causal attribution inferred.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--start', type=timestamp, required=True)
    parser.add_argument('--end', type=timestamp, required=True)
    args=parser.parse_args()
    try:
        result=audit(args.log.read_bytes(),args.start,args.end)
    except (OSError, ValueError):
        result={'status':'review_required','issues':['power_evidence_unavailable']}
    print(json.dumps(result,indent=2))
    return 2 if result['status']=='review_required' else 0


if __name__=='__main__':
    raise SystemExit(main())
