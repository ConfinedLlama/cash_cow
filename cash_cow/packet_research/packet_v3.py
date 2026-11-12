"""Frozen offline packet_context_v3: response receipts and release evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .history import digest
from .packet import ARMS
from .receipts import receipt_history
from .release_evidence import verify_release_evidence
from .releases import select_releases

VERSION = 'packet_context_v3'
SPEC = {
    'version': VERSION, 'status': 'offline_only', 'execution_enabled': False,
    'baseline': 'paper_ai_v1', 'symbol': 'SPY', 'feed': 'iex',
    'return_lags_minutes': [5, 15, 30], 'history_bars': 6, 'bar_minutes': 5,
    'max_snapshot_age_seconds': 120, 'max_release_age_days': 7,
    'max_packet_bytes': 20000, 'arms': list(ARMS),
    'capital_usd': 2000, 'allocation': 0.95,
    'cost_stress': {'minimum_per_order_usd': 0.40, 'per_share_usd': 0.0035, 'per_order_bps': 2},
    'prospective_sessions': 20, 'capture_schema': 'receipt_capture_v1',
    'release_evidence_schema': 'release_evidence_v1',
    'max_request_seconds': 60, 'max_capture_seconds': 120,
    'max_clock_difference_seconds': 10, 'max_wall_monotonic_difference_seconds': 1,
}


def load_spec():
    path = Path(__file__).resolve().parents[2]/'configs/packet_context_v3.json'
    spec = json.loads(path.read_bytes())
    if digest(spec) != digest(SPEC):
        raise ValueError('unsupported_candidate_specification')
    return spec


def build_packet(context, capture, releases, arm, *, evidence=None, evidence_directory=None):
    spec = load_spec()
    if arm not in ARMS:
        raise ValueError('unsupported_candidate_arm')
    if not isinstance(context, dict) or any(k in context for k in ('price_history', 'official_releases')):
        raise ValueError('invalid_or_enriched_baseline')
    if context.get('symbol') != 'SPY' or context.get('feed') != 'iex':
        raise ValueError('symbol_or_feed_mismatch')
    packet = deepcopy(context)
    sources = {'baseline': digest(context), 'specification': digest(spec)}
    if arm != 'baseline':
        packet['price_history'] = receipt_history(capture, context)
        packet['price_history']['version'] = VERSION
        sources['capture'] = digest(capture)
    if arm == 'history_and_releases':
        if not isinstance(releases, list):
            raise ValueError('invalid_release_archive')
        if releases:
            if evidence is None or evidence_directory is None:
                raise ValueError('release_evidence_required')
            verified = verify_release_evidence(releases, evidence, evidence_directory, context['as_of'])
            sources['release_evidence'] = verified['manifest_sha256']
        elif evidence is not None:
            # An explicit empty manifest is checked too; unused evidence fails.
            if evidence_directory is None:
                raise ValueError('release_evidence_directory_required')
            verified = verify_release_evidence(releases, evidence, evidence_directory, context['as_of'])
            sources['release_evidence'] = verified['manifest_sha256']
        packet['official_releases'] = select_releases(releases, context['as_of'])
        sources['release_archive'] = digest(releases)
    raw = json.dumps(packet, sort_keys=True, allow_nan=False, ensure_ascii=False).encode('utf-8')
    if len(raw) > spec['max_packet_bytes']:
        raise ValueError('packet_byte_limit_exceeded')
    return {'version': VERSION, 'arm': arm, 'execution_enabled': False, 'packet': packet,
            'packet_bytes': len(raw), 'packet_sha256': hashlib.sha256(raw).hexdigest(),
            'source_sha256': sources,
            'limits': 'Offline construction only. Local receipt and manual source consistency, not authenticated source identity, clock synchronization, model performance or executions.'}
