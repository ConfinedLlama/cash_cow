"""Read-only AI evidence audit; no broker/model calls or telemetry mutations.

Count unique saved decisions separately from repeated polling events. Cross-check
the subscription ledger and causal packet times without emitting private text.
"""
import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .ai import validate_proposal
from .client import timestamp


def audit(directory, config, now=None):
    directory = Path(directory)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Audit time must include timezone")
    errors, manifest = Counter(), {}

    def read(path):
        raw = path.read_bytes()
        manifest[str(path.relative_to(directory))] = hashlib.sha256(raw).hexdigest()
        return raw

    try:
        usage = json.loads(read(directory / 'ai_subscription_usage.json'))
        if not isinstance(usage, dict):
            raise ValueError()
    except (OSError, ValueError):
        usage = {}
        errors['unreadable_usage'] += 1

    counts, actions, sessions, records = Counter(), Counter(), {}, {}
    latencies, quote_ages = [], []
    news_packets = cited_packets = 0
    folder = directory / 'ai_decisions'
    if not folder.is_dir():
        errors['missing_decision_directory'] += 1
    for path in sorted(folder.glob('*.json')):
        try:
            record = json.loads(read(path))
            context = record['context']
            observed = timestamp(context['as_of'])
            day = context['session_date']
            if day != observed.astimezone(ZoneInfo('America/New_York')).date().isoformat() or observed > now:
                raise ValueError()
            slot = hashlib.sha256(f"{config['version']}:{context['features']['bar']}:{context['position_qty']}".encode()).hexdigest()[:24]
            if path.stem != slot:
                raise ValueError()
            status = record['status']
            if status not in {'pending', 'failed', 'completed'}:
                raise ValueError()
            counts[status] += 1
            sessions.setdefault(day, Counter())[status] += 1
            # Keep failed/pending records in the denominator; never repair them.
            records[slot] = record
            attempt = usage.get(day, {}).get(slot)
            if not isinstance(attempt, dict) or attempt.get('status') != status:
                errors['decision_usage_mismatch'] += 1
            if status == 'pending' and (now-observed).total_seconds() > config['ai']['proposal_ttl_seconds']:
                errors['expired_pending_decision'] += 1
            if status != 'completed':
                continue
            proposal = validate_proposal(record['proposal'], context)
            received = timestamp(record['received_at'])
            latency = (received-observed).total_seconds()
            if received > now or latency < 0:
                raise ValueError()
            latencies.append(latency)
            if latency > config['ai']['proposal_ttl_seconds']:
                errors['late_completed_decision'] += 1
            for item in context['news']:
                first = timestamp(item['first_observed_at'])
                if not timestamp(item['published_at']) <= timestamp(item['updated_at']) <= first <= observed:
                    errors['noncausal_packet_news'] += 1
            news_packets += bool(context['news'])
            cited_packets += bool(proposal['news_ids'])
            quote_age = (observed-timestamp(context['quote']['t'])).total_seconds()
            quote_ages.append(quote_age)
            if not -5 <= quote_age <= config['max_quote_age_seconds']:
                errors['invalid_packet_quote_age'] += 1
            actions[proposal['action']] += 1
            sessions[day][proposal['action']] += 1
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
            errors['invalid_decision_record'] += 1

    usage_counts, tokens = {}, Counter()
    preflight_attempts = diagnostic_attempts = 0
    for day, attempts in usage.items():
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError()
        except (ValueError, TypeError):
            errors['invalid_usage_date'] += 1
            continue
        if not isinstance(attempts, dict):
            errors['invalid_usage_day'] += 1
            continue
        daily = Counter()
        for slot, attempt in attempts.items():
            if not isinstance(attempt, dict) or attempt.get('status') not in {'pending', 'failed', 'completed'}:
                errors['invalid_usage_attempt'] += 1
                continue
            daily[attempt['status']] += 1
            if slot.startswith('preflight-'):
                preflight_attempts += 1
            elif slot.startswith('diagnostic-'):
                diagnostic_attempts += 1
            elif slot not in records:
                errors['market_usage_without_decision'] += 1
            values = attempt.get('usage', {})
            if not isinstance(values, dict):
                errors['invalid_token_usage'] += 1
                continue
            for field in ('input_tokens', 'output_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'reasoning_output_tokens'):
                value = values.get(field, 0)
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    errors['invalid_token_usage'] += 1
                else:
                    tokens[field] += value
        usage_counts[day] = dict(daily)

    event_count, consumed = 0, set()
    try:
        lines = read(directory / 'events.jsonl').splitlines()
    except OSError:
        lines = []
        errors['unreadable_events'] += 1
    for line in lines:
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError()
            if event.get('kind') != 'ai_proposal':
                continue
            event_count += 1
            slot = event['decision_id']
            consumed.add(slot)
            record = records.get(slot)
            if not record or record.get('status') != 'completed':
                errors['event_without_completed_decision'] += 1
                continue
            at = timestamp(event['at'])
            observed = timestamp(record['context']['as_of'])
            if at > now or at < timestamp(record['received_at']) or not 0 <= (at-observed).total_seconds() <= config['ai']['proposal_ttl_seconds']:
                errors['invalid_consumption_time'] += 1
            if event['action'] != record['proposal']['action'] or timestamp(event['as_of']) != observed:
                errors['event_decision_mismatch'] += 1
        except (ValueError, KeyError, TypeError, AttributeError):
            errors['invalid_event'] += 1

    return {
        'as_of': now.isoformat(), 'status': 'review_required' if errors else 'integrity_checks_passed',
        'unique_records': len(records), 'decision_statuses': dict(counts), 'completed_actions': dict(actions),
        'by_session': {day: dict(count) for day, count in sorted(sessions.items())},
        'proposal_events': event_count, 'unique_decisions_referenced': len(consumed),
        'repeated_proposal_events': event_count-len(consumed),
        'response_latency_seconds': {'min': min(latencies, default=None), 'max': max(latencies, default=None)},
        'packet_quote_age_seconds': {'min': min(quote_ages, default=None), 'max': max(quote_ages, default=None)},
        'completed_packets_with_news': news_packets, 'completed_proposals_citing_news': cited_packets,
        'subscription_attempts': usage_counts, 'preflight_attempts': preflight_attempts,
        'diagnostic_attempts': diagnostic_attempts,
        'reported_tokens_all_attempts': dict(tokens), 'errors': dict(errors),
        'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        'limits': 'Private files read separately, not an atomic snapshot. Retry audit if concurrently written. Counts are not fills, profitability, confidence calibration, news completeness, or evidence that a citation caused a decision. Token fields may overlap and are not dollar costs. No raw packet text, identifiers, or credentials emitted.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', choices=('paper_ai_v1',), default='paper_ai_v1')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / 'configs' / (args.config+'.json')).read_text())
    result = audit(root / 'data/telemetry' / args.config, config)
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result['errors'] else 0)


if __name__ == '__main__':
    main()
