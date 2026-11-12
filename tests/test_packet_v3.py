from copy import deepcopy
import json

import pytest

from cash_cow.packet_research import packet_v3
from cash_cow.packet_research.packet_v3 import build_packet, load_spec
from test_receipt_history import fixture


def test_three_arms_are_deterministic_and_baseline_preserved():
    capture, context = fixture(); original = deepcopy(context)
    results = [build_packet(context, capture, [], arm) for arm in packet_v3.ARMS]
    assert results[0]['packet'] == context == original
    assert 'price_history' not in results[0]['packet']
    assert results[1]['packet']['price_history']['version'] == 'packet_context_v3'
    assert results[2]['packet']['official_releases']['values'] == []
    assert results[2] == build_packet(context, capture, [], 'history_and_releases')
    assert all(not r['execution_enabled'] for r in results)
    assert len({r['packet_sha256'] for r in results}) == 3


def test_nonempty_release_cannot_bypass_saved_evidence():
    capture, context = fixture()
    with pytest.raises(ValueError, match='evidence_required'):
        build_packet(context, capture, [{'unverified': True}], 'history_and_releases')


def test_receipt_after_cutoff_rejects_history_but_not_baseline():
    capture, context = fixture(); context['as_of'] = '2026-11-12T15:04:59Z'
    assert build_packet(context, capture, [], 'baseline')['packet'] == context
    with pytest.raises(ValueError):build_packet(context, capture, [], 'history')


def test_packet_limit_counts_utf8_bytes_without_truncation():
    capture, context = fixture();context['news'] = '界'*7000
    with pytest.raises(ValueError, match='byte_limit'):build_packet(context, capture, [], 'baseline')


def test_specification_rejects_cost_or_extra_field_changes(monkeypatch):
    original = load_spec()
    for changed in (dict(original, allocation=1), dict(original, surprise=True)):
        monkeypatch.setattr(packet_v3.Path, 'read_bytes', lambda _: json.dumps(changed).encode())
        with pytest.raises(ValueError, match='specification'):load_spec()


def test_verified_release_selected_but_later_observation_excluded(tmp_path):
    from test_release_evidence import fixture as releases_fixture
    from cash_cow.packet_research.history import digest
    capture, context = fixture();records, manifest = releases_fixture(tmp_path)
    result = build_packet(context, capture, records, 'history_and_releases',
                          evidence=manifest, evidence_directory=tmp_path)
    assert len(result['packet']['official_releases']['values']) == 1
    records[0]['first_observed_at'] = '2026-11-12T15:06:00Z'
    manifest['reviews'][0]['record_sha256'] = digest(records[0])
    result = build_packet(context, capture, records, 'history_and_releases',
                          evidence=manifest, evidence_directory=tmp_path)
    assert result['packet']['official_releases']['excluded_not_yet_observed'] == 1
    assert result['packet']['official_releases']['values'] == []
    (tmp_path/'capture.txt').write_text('tampered')
    with pytest.raises(ValueError):
        build_packet(context, capture, records, 'history_and_releases',
                     evidence=manifest, evidence_directory=tmp_path)
