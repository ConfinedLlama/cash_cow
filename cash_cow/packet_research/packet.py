"""Assemble registered offline comparison arms without calling a model."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .history import digest, history_features, VERSION
from .releases import select_releases

ARMS = ('baseline', 'history', 'history_and_releases')


def load_spec():
    path = Path(__file__).resolve().parents[2]/'configs/packet_context_v2.json'
    spec = json.loads(path.read_text())
    expected = {'version': VERSION, 'status': 'offline_only', 'execution_enabled': False,
                'baseline': 'paper_ai_v1', 'symbol': 'SPY', 'feed': 'iex',
                'return_lags_minutes': [5,15,30], 'history_bars': 6, 'bar_minutes': 5,
                'max_snapshot_age_seconds': 120, 'max_release_age_days': 7,
                'max_packet_bytes': 20000, 'arms': list(ARMS)}
    if any(spec.get(key) != value for key, value in expected.items()):
        raise ValueError('unsupported_candidate_specification')
    return spec


def build_packet(context, snapshot, releases, arm):
    spec = load_spec()
    if arm not in ARMS:
        raise ValueError('unsupported_candidate_arm')
    if not isinstance(context, dict) or any(key in context for key in ('price_history','official_releases')):
        raise ValueError('baseline_already_enriched_or_invalid')
    if context.get('symbol') != spec['symbol'] or context.get('feed') != spec['feed']:
        raise ValueError('symbol_or_feed_mismatch')
    packet = deepcopy(context)
    sources = {'baseline': digest(context), 'specification': digest(spec)}
    if arm != 'baseline':
        packet['price_history'] = history_features(snapshot, context)
        sources['snapshot'] = digest(snapshot)
    if arm == 'history_and_releases':
        packet['official_releases'] = select_releases(releases, context['as_of'])
        sources['release_archive'] = digest(releases)
    encoded = json.dumps(packet,sort_keys=True,allow_nan=False,ensure_ascii=False).encode('utf-8')
    if len(encoded) > spec['max_packet_bytes']:
        raise ValueError('packet_byte_limit_exceeded')
    return {'version': VERSION, 'arm': arm, 'execution_enabled': False,
            'packet': packet, 'packet_bytes': len(encoded),
            'packet_sha256': hashlib.sha256(encoded).hexdigest(), 'source_sha256': sources,
            'limits': 'Offline construction only. No model decision, execution, return or verified receipt-time claim. Preserve baseline and prior failures.'}
